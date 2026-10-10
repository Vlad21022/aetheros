"""WebSocket endpoint that screens connect to (ws://<hub>:8765/v1).

The handshake, the snapshot, live state updates and the error rules from
contracts/README.md. The agent (phase 3) plugs in behind `Hub`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from pydantic import ValidationError
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from . import config
from . import protocol as p
from .config import Settings
from .ha_client import HaClient
from .ha_state import HomeAssistantState
from .state import DemoState, StateSource
from .tier0 import Tier0Error, Tier0Router

log = logging.getLogger("aether_hub")

PATH = "/v1"


class Hub:
    def __init__(self, state: StateSource, router: Tier0Router, name: str = "AetherOS Hub") -> None:
        self.state = state
        self.router = router
        self.name = name
        self.screens: dict[str, ServerConnection] = {}

    async def handle(self, ws: ServerConnection) -> None:
        if ws.request is None or ws.request.path != PATH:
            await ws.close(code=1008, reason=f"use {PATH}")
            return

        screen_id: str | None = None
        try:
            async for raw in ws:
                try:
                    msg = p.parse(raw)
                except ValidationError as exc:
                    await self._send(ws, p.new(p.Error, p.ErrorPayload(code="bad_message", message=_short(exc))))
                    continue

                if screen_id is None and not isinstance(msg, p.Hello):
                    await self._send(
                        ws,
                        p.new(
                            p.Error, p.ErrorPayload(code="bad_message", message="Send hello first."), reply_to=msg.id
                        ),
                    )
                    continue

                match msg:
                    case p.Hello():
                        screen_id = msg.payload.screenId
                        self.screens[screen_id] = ws
                        log.info("screen %s connected (%s)", screen_id, msg.payload.name)
                        await self._send(
                            ws, p.new(p.Welcome, p.WelcomePayload(hubName=self.name, protocol=1), reply_to=msg.id)
                        )
                        await self._send(ws, p.new(p.StateSnapshot, await self.state.snapshot()))
                    case p.Utterance():
                        await self._on_utterance(ws, msg)
                    case p.Control():
                        await self._on_control(ws, msg)
                    case p.Presence() | p.ConfirmResponse():
                        log.info("%s from %s", msg.type, screen_id)
                    case _:
                        await self._send(
                            ws,
                            p.new(
                                p.Error,
                                p.ErrorPayload(
                                    code="bad_message", message=f"{msg.type} is sent by the hub, not a screen."
                                ),
                                reply_to=msg.id,
                            ),
                        )
        except ConnectionClosed:
            pass
        finally:
            if screen_id is not None and self.screens.get(screen_id) is ws:
                del self.screens[screen_id]
                log.info("screen %s disconnected", screen_id)

    async def broadcast(self) -> None:
        """Sends every change of the state source to all connected screens. Runs until cancelled."""
        async for change in self.state.updates():
            if isinstance(change, p.SnapshotPayload):
                msg = p.new(p.StateSnapshot, change)
            else:
                msg = p.new(p.StateUpdate, change)
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


def build(settings: Settings) -> tuple[Hub, HaClient | None]:
    """Wires the hub to Home Assistant, or to the demo home when none is configured."""
    if settings.home_assistant is None:
        demo = DemoState()
        return Hub(demo, Tier0Router(demo.entities, demo)), None

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
    return Hub(source, Tier0Router(controllable, client)), client


async def run(settings: Settings, host: str = "0.0.0.0", port: int = 8765) -> None:
    hub, client = build(settings)
    async with serve(hub.handle, host, port), asyncio.TaskGroup() as tasks:
        log.info("listening on ws://%s:%d%s", host, port, PATH)
        if client is None:
            log.info("no Home Assistant configured: serving demo data")
        else:
            tasks.create_task(client.run())
        await hub.broadcast()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        settings = config.load()
    except config.ConfigError as exc:
        raise SystemExit(f"aether-hub: {exc}") from None
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run(settings))
