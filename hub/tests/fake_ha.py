"""A small stand-in for Home Assistant's WebSocket API, enough for the hub's client."""

from __future__ import annotations

import json
from typing import Any

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

TOKEN = "test-token"


class FakeHa:
    def __init__(self) -> None:
        self.states: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, str, str]] = []
        self.fail_services = False
        self.auth_attempts = 0
        self._subscribers: dict[ServerConnection, int] = {}
        self._connections: set[ServerConnection] = set()
        self._server: Server | None = None
        self.url = ""

    async def start(self, port: int = 0) -> None:
        self._server = await serve(self._handle, "127.0.0.1", port)
        self.port = self._server.sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def drop_connections(self) -> None:
        for ws in list(self._connections):
            await ws.close()

    async def set_state(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> None:
        old = self.states.get(entity_id)
        new = {"entity_id": entity_id, "state": state, "attributes": attributes or (old or {}).get("attributes", {})}
        self.states[entity_id] = new
        data = {"entity_id": entity_id, "old_state": old, "new_state": new}
        for ws, subscription in list(self._subscribers.items()):
            event = {"event_type": "state_changed", "data": data}
            await ws.send(json.dumps({"id": subscription, "type": "event", "event": event}))

    async def _handle(self, ws: ServerConnection) -> None:
        self._connections.add(ws)
        try:
            await ws.send(json.dumps({"type": "auth_required", "ha_version": "fake"}))
            auth = json.loads(await ws.recv())
            self.auth_attempts += 1
            if auth.get("access_token") != TOKEN:
                await ws.send(json.dumps({"type": "auth_invalid", "message": "Invalid access token"}))
                return
            await ws.send(json.dumps({"type": "auth_ok", "ha_version": "fake"}))
            async for raw in ws:
                await self._command(ws, json.loads(raw))
        except ConnectionClosed:
            pass
        finally:
            self._connections.discard(ws)
            self._subscribers.pop(ws, None)

    async def _command(self, ws: ServerConnection, msg: dict[str, Any]) -> None:
        async def result(value: Any = None) -> None:
            await ws.send(json.dumps({"id": msg["id"], "type": "result", "success": True, "result": value}))

        match msg["type"]:
            case "subscribe_events":
                self._subscribers[ws] = msg["id"]
                await result()
            case "get_states":
                await result(list(self.states.values()))
            case "call_service":
                entity_id = msg["target"]["entity_id"]
                if self.fail_services:
                    error = {"code": "home_assistant_error", "message": "Service failed"}
                    await ws.send(json.dumps({"id": msg["id"], "type": "result", "success": False, "error": error}))
                    return
                self.calls.append((msg["domain"], msg["service"], entity_id))
                await result({"context": {}})
                await self._apply(msg["service"], entity_id)
            case _:
                error = {"code": "unknown_command", "message": "Unknown command."}
                await ws.send(json.dumps({"id": msg["id"], "type": "result", "success": False, "error": error}))

    async def _apply(self, service: str, entity_id: str) -> None:
        """What the real devices would do, so state_changed follows a service call."""
        current = self.states.get(entity_id, {}).get("state")
        new = {
            "turn_on": "on",
            "turn_off": "off",
            "toggle": "off" if current == "on" else "on",
            "lock": "locked",
            "media_play_pause": "paused" if current == "playing" else "playing",
        }.get(service)
        if new is not None and new != current:
            await self.set_state(entity_id, new)
