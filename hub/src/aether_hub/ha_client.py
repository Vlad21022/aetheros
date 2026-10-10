"""A thin client for Home Assistant's WebSocket API.

Keeps one connection open: authenticates, subscribes to state changes, fetches all
states, and calls services. Reconnects with a growing delay. Knows nothing about
screens or the AetherOS protocol. See docs/decisions.md, 017.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

log = logging.getLogger("aether_hub.ha")

# websockets logs raw frames at DEBUG, and the auth frame carries the token.
# Its logger never goes below INFO, whatever the hub's log level is.
_wire_log = logging.getLogger("aether_hub.ha.wire")
_wire_log.setLevel(logging.INFO)

RETRY_DELAYS: tuple[float, ...] = (1, 2, 5, 10, 30)
COMMAND_TIMEOUT = 10.0

JsonObject = dict[str, Any]


class HaError(Exception):
    """Home Assistant refused or failed a command."""


class HaUnavailable(HaError):
    """There is no working connection to Home Assistant right now."""


class HaAuthError(HaError):
    """Home Assistant rejected the access token."""


def websocket_url(url: str) -> str:
    """http://ha.local:8123 → ws://ha.local:8123/api/websocket"""
    parts = urlsplit(url)
    scheme = {"http": "ws", "https": "wss"}.get(parts.scheme, parts.scheme)
    path = parts.path if parts.path not in ("", "/") else "/api/websocket"
    return urlunsplit((scheme, parts.netloc, path, "", ""))


class HaClient:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        on_connected: Callable[[list[JsonObject]], None],
        on_state_changed: Callable[[JsonObject], None],
        on_disconnected: Callable[[], None],
        retry_delays: Sequence[float] = RETRY_DELAYS,
    ) -> None:
        """`on_connected` gets every state after each (re)connect; `on_state_changed`
        gets the `data` of each state_changed event."""
        self._url = websocket_url(url)
        self._token = token
        self._on_connected = on_connected
        self._on_state_changed = on_state_changed
        self._on_disconnected = on_disconnected
        self._retry_delays = retry_delays
        self._ws: ClientConnection | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self.connected = False

    async def run(self) -> None:
        """Stays connected until cancelled. Returns only if the token is rejected."""
        attempt = 0
        while True:
            try:
                async with connect(self._url, logger=_wire_log) as ws:
                    await self._authenticate(ws)
                    attempt = 0
                    await self._session(ws)
                log.warning("Home Assistant closed the connection")
            except HaAuthError as exc:
                # Retrying a bad token only gets the hub banned by Home Assistant.
                log.error("Home Assistant rejected the token (%s). Fix AETHER_HA_TOKEN and restart the hub.", exc)
                return
            except (OSError, ConnectionClosed, HaError, TimeoutError, ValueError) as exc:
                log.warning("Home Assistant is not reachable: %s", exc)
            delay = self._retry_delays[min(attempt, len(self._retry_delays) - 1)]
            attempt += 1
            await asyncio.sleep(delay)

    async def call_service(self, domain: str, service: str, entity_id: str) -> None:
        await self._command(
            {"type": "call_service", "domain": domain, "service": service, "target": {"entity_id": entity_id}}
        )

    async def _authenticate(self, ws: ClientConnection) -> None:
        async with asyncio.timeout(COMMAND_TIMEOUT):
            hello = json.loads(await ws.recv())
            if hello.get("type") != "auth_required":
                raise HaError(f"expected auth_required, got {hello.get('type')}")
            await ws.send(json.dumps({"type": "auth", "access_token": self._token}))
            reply = json.loads(await ws.recv())
        if reply.get("type") == "auth_invalid":
            raise HaAuthError(str(reply.get("message", "invalid token")))
        if reply.get("type") != "auth_ok":
            raise HaError(f"expected auth_ok, got {reply.get('type')}")

    async def _session(self, ws: ClientConnection) -> None:
        self._ws = ws
        reader = asyncio.create_task(self._read(ws))
        try:
            # Subscribe first, so no change is lost between the two commands.
            await self._command({"type": "subscribe_events", "event_type": "state_changed"})
            states = await self._command({"type": "get_states"})
            self.connected = True
            log.info("connected to Home Assistant, %d entities", len(states))
            self._on_connected(states)
            await reader
        finally:
            reader.cancel()
            self._ws = None
            self.connected = False
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(HaUnavailable("connection lost"))
            self._pending.clear()
            self._on_disconnected()

    async def _read(self, ws: ClientConnection) -> None:
        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "event":
                event = msg.get("event") or {}
                if event.get("event_type") == "state_changed":
                    self._on_state_changed(event.get("data") or {})
            elif msg.get("type") == "result":
                future = self._pending.pop(msg.get("id"), None)
                if future is None or future.done():
                    continue
                if msg.get("success"):
                    future.set_result(msg.get("result"))
                else:
                    error = msg.get("error") or {}
                    future.set_exception(HaError(str(error.get("message") or error.get("code") or "command failed")))

    async def _command(self, command: JsonObject) -> Any:
        ws = self._ws
        if ws is None:
            raise HaUnavailable("not connected")
        command_id, self._next_id = self._next_id, self._next_id + 1
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[command_id] = future
        try:
            await ws.send(json.dumps({"id": command_id, **command}))
            async with asyncio.timeout(COMMAND_TIMEOUT):
                return await future
        except ConnectionClosed:
            raise HaUnavailable("connection lost") from None
        except TimeoutError:
            raise HaUnavailable("Home Assistant did not answer in time") from None
        finally:
            self._pending.pop(command_id, None)
