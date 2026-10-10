"""WebSocket endpoint that screens connect to (ws://<hub>:8765/v1).

Phase 0: the handshake, the snapshot and the error rules from contracts/README.md.
Home Assistant (phase 1) and the agent (phase 3) plug in behind `Hub`.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import ValidationError
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from . import protocol as p
from .state import StateSource, demo_state

log = logging.getLogger("aether_hub")

PATH = "/v1"


class Hub:
    def __init__(self, state: StateSource, name: str = "AetherOS Hub") -> None:
        self.state = state
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
                        await self._send(
                            ws,
                            p.new(
                                p.Error,
                                p.ErrorPayload(code="unavailable", message="Home control arrives in phase 1."),
                                reply_to=msg.id,
                            ),
                        )
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


async def run(host: str = "0.0.0.0", port: int = 8765) -> None:
    hub = Hub(demo_state())
    async with serve(hub.handle, host, port) as server:
        log.info("listening on ws://%s:%d%s", host, port, PATH)
        await server.serve_forever()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
