"""The owner's commands for a running hub: pair, screens, forget.

They travel over a Unix socket in the hub's data directory (owner-only), never over
the network, so only someone logged in as the owner on the hub's machine can run them.
One JSON request per connection, one JSON reply.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .pairing import PairingError

if TYPE_CHECKING:
    from .server import Hub

SOCKET_FILE = "admin.sock"


async def serve_admin(hub: Hub, path: Path) -> asyncio.Server:
    with contextlib.suppress(FileNotFoundError):
        os.unlink(path)  # left over from a hub that did not shut down cleanly

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = json.loads(await reader.readline())
            reply = await _run(hub, request)
        except (ValueError, KeyError, TypeError):
            reply = {"ok": False, "message": "Comandă necunoscută."}
        writer.write(json.dumps(reply, ensure_ascii=False).encode() + b"\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_unix_server(handle, path=path)
    os.chmod(path, 0o600)
    return server


async def _run(hub: Hub, request: dict[str, Any]) -> dict[str, Any]:
    match request["command"]:
        case "pair":
            try:
                screen = await hub.pairing.approve(str(request["code"]))
            except PairingError as exc:
                return {"ok": False, "message": str(exc)}
            return {"ok": True, "message": f"Ecranul „{screen.name}” e asociat ({screen.screen_id})."}
        case "screens":
            screens = [
                {
                    "screenId": s.screen_id,
                    "name": s.name,
                    "pairedAt": s.paired_at,
                    "connected": s.screen_id in hub.screens,
                }
                for s in hub.pairing.screens()
            ]
            return {"ok": True, "message": f"{len(screens)} ecrane asociate.", "screens": screens}
        case "forget":
            screen = await hub.forget(str(request["screenId"]))
            if screen is None:
                return {"ok": False, "message": f"Niciun ecran asociat cu id-ul {request['screenId']}."}
            return {"ok": True, "message": f"Ecranul „{screen.name}” nu mai e asociat."}
    raise KeyError(request["command"])


def call(path: Path, request: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
    """Sends one command to the running hub. Raises ConnectionError if it is not running."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(str(path))
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise ConnectionError(f"Hub-ul nu rulează (nu găsesc {path}).") from exc
        sock.sendall(json.dumps(request).encode() + b"\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data)
