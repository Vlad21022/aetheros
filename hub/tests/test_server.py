"""Talk to a real hub over a real WebSocket, the way a screen will."""

import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from test_contract import SCHEMA
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aether_hub.server import Hub
from aether_hub.state import demo_state

VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

HELLO = {
    "v": 1,
    "type": "hello",
    "id": "s1",
    "ts": "2026-10-10T13:25:00Z",
    "payload": {
        "screenId": "test-screen",
        "name": "Test",
        "protocol": 1,
        "capabilities": {"touch": True, "microphone": False, "speaker": False, "presence": False},
        "size": {"width": 1280, "height": 800},
    },
}


@pytest.fixture
async def url():
    async with serve(Hub(demo_state()).handle, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        yield f"ws://127.0.0.1:{port}/v1"


async def receive(ws):
    msg = json.loads(await ws.recv())
    VALIDATOR.validate(msg)
    return msg


async def test_hello_gets_welcome_then_snapshot(url):
    async with connect(url) as ws:
        await ws.send(json.dumps(HELLO))
        welcome = await receive(ws)
        assert welcome["type"] == "welcome" and welcome["replyTo"] == "s1"
        snapshot = await receive(ws)
        assert snapshot["type"] == "state.snapshot"
        assert snapshot["payload"]["home"]["tiles"]


async def test_must_say_hello_first(url):
    async with connect(url) as ws:
        await ws.send(json.dumps({**HELLO, "type": "presence", "payload": {"present": True}}))
        error = await receive(ws)
        assert error["payload"]["code"] == "bad_message"


async def test_garbage_gets_an_error_and_the_connection_stays_open(url):
    async with connect(url) as ws:
        await ws.send("not json")
        assert (await receive(ws))["payload"]["code"] == "bad_message"
        await ws.send(json.dumps(HELLO))
        assert (await receive(ws))["type"] == "welcome"


async def test_utterance_gets_status_reply_status(url):
    async with connect(url) as ws:
        await ws.send(json.dumps(HELLO))
        await receive(ws)
        await receive(ws)
        await ws.send(
            json.dumps(
                {**HELLO, "type": "utterance", "id": "s2", "payload": {"text": "Aprinde lumina", "source": "typed"}}
            )
        )
        kinds = [(await receive(ws))["type"] for _ in range(3)]
        assert kinds == ["agent.status", "agent.reply", "agent.status"]
