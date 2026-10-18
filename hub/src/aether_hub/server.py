"""WebSocket endpoint that screens connect to (wss://<hub>:8765/v1).

Pairing, the handshake, the snapshot, live state updates and the error rules from
contracts/README.md. The agent (phase 3) plugs in behind `Hub`.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys
from collections.abc import Callable
from datetime import datetime

from pydantic import ValidationError
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from . import admin, config
from . import protocol as p
from .config import Settings
from .glance import glance, with_glance
from .ha_client import HaClient
from .ha_state import HomeAssistantState
from .pairing import SCREENS_FILE, PairedScreen, Pairing
from .state import DemoState, StateSource
from .tier0 import Tier0Error, Tier0Router
from .tls import display, ensure_certificate

log = logging.getLogger("aether_hub")

PATH = "/v1"


class Hub:
    def __init__(
        self,
        state: StateSource,
        router: Tier0Router,
        pairing: Pairing,
        name: str = "AetherOS Hub",
        now: Callable[[], datetime] = lambda: datetime.now().astimezone(),
    ) -> None:
        self.state = state
        self.router = router
        self.pairing = pairing
        self.now = now
        self._glance: str | None = None
        self.name = name
        self.screens: dict[str, ServerConnection] = {}

    async def handle(self, ws: ServerConnection) -> None:
        if ws.request is None or ws.request.path != PATH:
            await ws.close(code=1008, reason=f"use {PATH}")
            return

        screen_id: str | None = None  # set once the screen has shown a valid token
        asked_to_pair: str | None = None
        try:
            async for raw in ws:
                try:
                    msg = p.parse(raw)
                except ValidationError as exc:
                    await self._send(ws, p.new(p.Error, p.ErrorPayload(code="bad_message", message=_short(exc))))
                    continue

                match msg:
                    case p.Hello():
                        if not self.pairing.verify(msg.payload.screenId, msg.payload.token):
                            screen_id = None
                            await self._error(ws, msg, "unauthorized", "This screen is not paired with the hub.")
                            continue
                        screen_id = msg.payload.screenId
                        self.screens[screen_id] = ws
                        log.info("screen %s connected (%s)", screen_id, msg.payload.name)
                        await self._send(
                            ws, p.new(p.Welcome, p.WelcomePayload(hubName=self.name, protocol=1), reply_to=msg.id)
                        )
                        await self._send(
                            ws, p.new(p.StateSnapshot, with_glance(await self.state.snapshot(), self.now()))
                        )
                    case p.PairRequest() if screen_id is None:
                        asked_to_pair = msg.payload.screenId
                        self.pairing.request(
                            msg.payload.screenId, msg.payload.name, msg.payload.code, self._deliver_token(ws, msg.id)
                        )
                        log.info("screen %r asks to be paired: run aether-hub pair <code it shows>", msg.payload.name)
                    case _ if screen_id is None:
                        await self._error(ws, msg, "unauthorized", "Pair this screen first.")
                    case p.Utterance():
                        await self._on_utterance(ws, msg)
                    case p.Control():
                        await self._on_control(ws, msg)
                    case p.Presence() | p.ConfirmResponse():
                        log.info("%s from %s", msg.type, screen_id)
                    case p.PairRequest():
                        await self._error(ws, msg, "bad_message", "This screen is already paired.")
                    case _:
                        await self._error(ws, msg, "bad_message", f"{msg.type} is sent by the hub, not a screen.")
        except ConnectionClosed:
            pass
        finally:
            if asked_to_pair is not None:
                self.pairing.withdraw(asked_to_pair)
            if screen_id is not None and self.screens.get(screen_id) is ws:
                del self.screens[screen_id]
                log.info("screen %s disconnected", screen_id)

    def _deliver_token(self, ws: ServerConnection, request_id: str):
        async def deliver(token: str) -> None:
            await self._send(
                ws, p.new(p.PairResult, p.PairResultPayload(token=token, hubName=self.name), reply_to=request_id)
            )

        return deliver

    async def forget(self, screen_id: str) -> PairedScreen | None:
        """Unpairs a screen and closes its connection; it falls back to pairing."""
        screen = self.pairing.forget(screen_id)
        ws = self.screens.pop(screen_id, None)
        if ws is not None:
            await ws.close(code=4001, reason="unpaired")
        if screen is not None:
            log.info("screen %s (%s) unpaired", screen_id, screen.name)
        return screen

    async def _error(self, ws: ServerConnection, msg: p.Message, code: p.ErrorCode, message: str) -> None:
        await self._send(ws, p.new(p.Error, p.ErrorPayload(code=code, message=message), reply_to=msg.id))

    async def broadcast(self) -> None:
        """Sends every change of the state source to all connected screens. Runs until cancelled."""
        # What every screen got with its snapshot, so the first change sends no stale glance.
        self._glance = glance(await self.state.snapshot(), self.now())
        async for change in self.state.updates():
            if isinstance(change, p.SnapshotPayload):
                snapshot = with_glance(change, self.now())
                self._glance = snapshot.glance
                await self._to_all(p.new(p.StateSnapshot, snapshot))
            else:
                await self._to_all(p.new(p.StateUpdate, change))
                await self.refresh_glance()

    async def refresh_glance(self) -> None:
        """Sends a glance update if the line changed since the last one sent."""
        text = glance(await self.state.snapshot(), self.now())
        if text != self._glance:
            self._glance = text
            await self._to_all(p.new(p.StateUpdate, p.UpdatePayload(section="glance", value=text)))

    async def tick(self) -> None:
        """Refreshes the glance at the start of every minute: events start and end with the clock."""
        while True:
            await asyncio.sleep(60 - self.now().second)
            await self.refresh_glance()

    async def _to_all(self, msg: p.Message) -> None:
        for ws in list(self.screens.values()):
            with contextlib.suppress(ConnectionClosed):
                await self._send(ws, msg)

    async def _on_control(self, ws: ServerConnection, msg: p.Control) -> None:
        """Tier 0. The new state reaches the screens as a state.update, not in this reply."""
        try:
            result = await self.router.control(msg.payload)
        except Tier0Error as exc:
            await self._send(ws, p.new(p.Error, p.ErrorPayload(code=exc.code, message=str(exc)), reply_to=msg.id))
        else:
            await self._send(ws, p.new(p.ActionResult, result, reply_to=msg.id))

    async def _on_utterance(self, ws: ServerConnection, msg: p.Utterance) -> None:
        await self._send(ws, p.new(p.AgentStatus, p.AgentStatusPayload(state="thinking", tier=0), reply_to=msg.id))
        await self._send(
            ws,
            p.new(
                p.AgentReply,
                p.AgentReplyPayload(text="Încă nu știu să fac asta. Agentul vine în faza 3.", final=True),
                reply_to=msg.id,
            ),
        )
        await self._send(ws, p.new(p.AgentStatus, p.AgentStatusPayload(state="idle")))

    async def _send(self, ws: ServerConnection, msg: p.Message) -> None:
        await ws.send(p.dump(msg))


def _short(exc: ValidationError) -> str:
    first = exc.errors()[0]
    where = ".".join(str(part) for part in first["loc"])
    return f"{where}: {first['msg']}"[:300]


def build(settings: Settings, pairing: Pairing | None = None) -> tuple[Hub, HaClient | None]:
    """Wires the hub to Home Assistant, or to the demo home when none is configured."""
    pairing = pairing or Pairing(settings.data_dir / SCREENS_FILE)
    if settings.home_assistant is None:
        demo = DemoState()
        return Hub(demo, Tier0Router(demo.entities, demo), pairing), None

    entities = settings.entities
    source = HomeAssistantState(entities)
    client = HaClient(
        settings.home_assistant.url,
        settings.home_assistant.token.get_secret_value(),
        on_connected=source.connected,
        on_state_changed=source.state_changed,
        on_disconnected=source.disconnected,
    )
    controllable = [tile.entity for tile in entities.home.tiles]
    if entities.sections.now_playing:
        controllable.append(entities.sections.now_playing)
    return Hub(source, Tier0Router(controllable, client), pairing), client


async def run(settings: Settings, port: int = 8765) -> None:
    hub, client = build(settings)
    certificate = ensure_certificate(settings.data_dir)
    host = settings.host
    admin_server = await admin.serve_admin(hub, settings.data_dir / admin.SOCKET_FILE)
    async with (
        admin_server,
        serve(hub.handle, host, port, ssl=certificate.server_context()),
        asyncio.TaskGroup() as tasks,
    ):
        log.info("listening on wss://%s:%d%s", host, port, PATH)
        log.info("certificate fingerprint %s", display(certificate.fingerprint))
        log.info("%d paired screens", len(hub.pairing.screens()))
        if client is None:
            log.info("no Home Assistant configured: serving demo data")
        else:
            tasks.create_task(client.run())
        tasks.create_task(hub.tick())
        await hub.broadcast()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="aether-hub", description="AetherOS hub. Without a command, runs the hub.")
    commands = parser.add_subparsers(dest="command")
    pair = commands.add_parser("pair", help="pair the screen that shows this code")
    pair.add_argument("code", nargs="+", help="the six digits on the screen")
    commands.add_parser("screens", help="list the paired screens")
    forget = commands.add_parser("forget", help="unpair a screen")
    forget.add_argument("screen_id")
    args = parser.parse_args(argv)

    try:
        settings = config.load()
    except config.ConfigError as exc:
        raise SystemExit(f"aether-hub: {exc}") from None

    if args.command is None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(run(settings))
        return

    request: dict[str, object] = {"command": args.command}
    if args.command == "pair":
        request["code"] = "".join(ch for ch in "".join(args.code) if ch.isdigit())
    elif args.command == "forget":
        request["screenId"] = args.screen_id
    try:
        reply = admin.call(settings.data_dir / admin.SOCKET_FILE, request)
    except ConnectionError as exc:
        raise SystemExit(f"aether-hub: {exc}") from None
    print(reply["message"])
    for screen in reply.get("screens", []):
        state = "conectat" if screen["connected"] else "deconectat"
        print(f"  {screen['screenId']}  {screen['name']}  asociat {screen['pairedAt']}  {state}")
    sys.exit(0 if reply["ok"] else 1)
