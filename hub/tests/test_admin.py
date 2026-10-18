"""Pairing a screen end to end: a screen over wss, the owner over the admin socket."""

import asyncio
import contextlib
import json
import logging
import tempfile
from pathlib import Path

import pytest
from test_server import HELLO, receive, serving
from tls_helpers import CLIENT_SSL
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from aether_hub import admin
from aether_hub.config import Settings
from aether_hub.pairing import Pairing
from aether_hub.server import build, main

UNPAIRED = {**HELLO, "payload": {k: v for k, v in HELLO["payload"].items() if k != "token"} | {"screenId": "kitchen"}}


def pair_request(code: str = "482913") -> str:
    return json.dumps(
        {
            **HELLO,
            "type": "pair.request",
            "id": "p1",
            "payload": {"screenId": "kitchen", "name": "Bucătărie", "code": code},
        }
    )


@pytest.fixture
async def hub_and_socket():
    # Unix socket paths are short-lived and must be short: /tmp, not pytest's long tmp_path.
    directory = Path(tempfile.mkdtemp(prefix="aether-", dir="/tmp"))
    hub, _ = build(Settings(data_dir=directory), Pairing(directory / "screens.json"))
    sock = directory / admin.SOCKET_FILE
    server = await admin.serve_admin(hub, sock)
    async with server, serving(hub) as url:
        yield hub, url, sock


async def ask(sock: Path, **request) -> dict:
    return await asyncio.to_thread(admin.call, sock, request)


async def test_an_unpaired_screen_gets_nothing_but_pairing(hub_and_socket):
    hub, url, _ = hub_and_socket
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(json.dumps(UNPAIRED))
        assert (await receive(ws))["payload"]["code"] == "unauthorized"
        control = {
            **HELLO,
            "type": "control",
            "id": "c1",
            "payload": {"entityId": "light.group_on", "action": "toggle"},
        }
        await ws.send(json.dumps(control))
        error = await receive(ws)
        assert (error["replyTo"], error["payload"]["code"]) == ("c1", "unauthorized")
        assert (await hub.state.snapshot()).home.tiles[0].state == "3 aprinse"


async def test_wrong_token_is_unauthorized(hub_and_socket):
    _, url, _ = hub_and_socket
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(json.dumps({**UNPAIRED, "payload": {**UNPAIRED["payload"], "token": "guess"}}))
        assert (await receive(ws))["payload"]["code"] == "unauthorized"


async def test_pairing_from_code_to_welcome(hub_and_socket, caplog):
    hub, url, sock = hub_and_socket
    async with connect(url, ssl=CLIENT_SSL) as ws:
        with caplog.at_level(logging.DEBUG):
            await ws.send(pair_request())
            await asyncio.sleep(0.05)
            reply = await ask(sock, command="pair", code="482913")
            assert reply == {"ok": True, "message": "Ecranul „Bucătărie” e asociat (kitchen)."}
            result = await receive(ws)
        assert (result["type"], result["replyTo"]) == ("pair.result", "p1")
        token = result["payload"]["token"]
        assert token not in caplog.text and "482913" not in caplog.text

        await ws.send(json.dumps({**UNPAIRED, "payload": {**UNPAIRED["payload"], "token": token}}))
        assert (await receive(ws))["type"] == "welcome"
        assert (await receive(ws))["type"] == "state.snapshot"

        listing = await ask(sock, command="screens")
        assert [(s["screenId"], s["connected"]) for s in listing["screens"]] == [("kitchen", True)]


async def test_a_wrong_code_is_said_to_the_owner(hub_and_socket):
    _, url, sock = hub_and_socket
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(pair_request("482913"))
        await asyncio.sleep(0.05)
        reply = await ask(sock, command="pair", code="000000")
        assert not reply["ok"] and "000000" in reply["message"]


async def test_forget_closes_the_screen_and_its_token_stops_working(hub_and_socket):
    hub, url, sock = hub_and_socket
    token = hub.pairing.add("kitchen", "Bucătărie")
    hello = json.dumps({**UNPAIRED, "payload": {**UNPAIRED["payload"], "token": token}})
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(hello)
        await receive(ws)
        await receive(ws)
        assert (await ask(sock, command="forget", screenId="kitchen"))["ok"]
        with pytest.raises(ConnectionClosed) as closed:
            while True:
                await ws.recv()
        assert closed.value.rcvd.code == 4001
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(hello)
        assert (await receive(ws))["payload"]["code"] == "unauthorized"
    assert not (await ask(sock, command="forget", screenId="kitchen"))["ok"]


async def test_a_paired_screen_cannot_ask_again(hub_and_socket):
    hub, url, _ = hub_and_socket
    token = hub.pairing.add("kitchen", "Bucătărie")
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(json.dumps({**UNPAIRED, "payload": {**UNPAIRED["payload"], "token": token}}))
        await receive(ws)
        await receive(ws)
        await ws.send(pair_request())
        assert (await receive(ws))["payload"]["code"] == "bad_message"


async def test_unknown_admin_commands_are_refused(hub_and_socket):
    _, _, sock = hub_and_socket
    assert not (await ask(sock, command="shutdown"))["ok"]


def test_the_command_line_says_when_the_hub_is_not_running(monkeypatch, capsys):
    directory = Path(tempfile.mkdtemp(prefix="aether-", dir="/tmp"))
    monkeypatch.chdir(directory)
    monkeypatch.delenv("AETHER_HA_URL", raising=False)
    monkeypatch.delenv("AETHER_HA_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exit_:
        main(["screens"])
    assert "nu rulează" in str(exit_.value.code)


async def test_the_command_line_pairs(hub_and_socket, monkeypatch, capsys):
    hub, url, sock = hub_and_socket
    monkeypatch.chdir(sock.parent)
    monkeypatch.setenv("AETHER_DATA", str(sock.parent))
    monkeypatch.delenv("AETHER_HA_URL", raising=False)
    monkeypatch.delenv("AETHER_HA_TOKEN", raising=False)
    async with connect(url, ssl=CLIENT_SSL) as ws:
        await ws.send(pair_request())
        await asyncio.sleep(0.05)
        with pytest.raises(SystemExit) as exit_:
            await asyncio.to_thread(main, ["pair", "482", "913"])
        assert exit_.value.code == 0
        assert "e asociat" in capsys.readouterr().out
        assert (await receive(ws))["type"] == "pair.result"
    with contextlib.suppress(SystemExit):
        await asyncio.to_thread(main, ["screens"])
    assert "Bucătărie" in capsys.readouterr().out
