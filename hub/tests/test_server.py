"""Talk to a real hub over a real WebSocket, the way a screen will."""

import asyncio
import contextlib
import json

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from test_contract import SCHEMA
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aether_hub.config import Entities
from aether_hub.ha_state import HomeAssistantState
from aether_hub.server import Hub
from aether_hub.state import DemoState

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


@contextlib.asynccontextmanager
async def serving(hub: Hub):
    """The hub on a free port, broadcasting, the way `run` starts it."""
    async with serve(hub.handle, "127.0.0.1", 0) as server:
        broadcast = asyncio.create_task(hub.broadcast())
        try:
            yield f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/v1"
        finally:
            broadcast.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await broadcast


async def receive(ws):
    async with asyncio.timeout(2):
        msg = json.loads(await ws.recv())
    VALIDATOR.validate(msg)
    return msg


async def join(url: str, screen_id: str = "test-screen"):
    """Connects a screen and reads its welcome and snapshot."""
    ws = await connect(url)
    await ws.send(json.dumps({**HELLO, "payload": {**HELLO["payload"], "screenId": screen_id}}))
    assert (await receive(ws))["type"] == "welcome"
    return ws, await receive(ws)


@pytest.fixture
async def url():
    async with serving(Hub(DemoState())) as url:
        yield url


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


HA_ENTITIES = Entities.model_validate(
    {"home": {"tiles": [{"entity": "light.office", "title": "Birou"}]}, "sections": {"weather": "weather.home"}}
)
HA_STATES = [
    {"entity_id": "light.office", "state": "off", "attributes": {}},
    {"entity_id": "weather.home", "state": "cloudy", "attributes": {"temperature": 14}},
]


async def test_state_changes_reach_every_screen():
    source = HomeAssistantState(HA_ENTITIES)
    source.connected(HA_STATES)
    async with serving(Hub(source)) as url:
        kitchen, snapshot = await join(url, "kitchen")
        office, _ = await join(url, "office")
        async with kitchen, office:
            # The snapshot queued by connected() is broadcast too; skip up to the update.
            assert snapshot["payload"]["home"]["tiles"][0]["state"] == "Stinsă"
            source.state_changed(
                {"entity_id": "light.office", "new_state": {"entity_id": "light.office", "state": "on"}}
            )
            for ws in (kitchen, office):
                update = await receive(ws)
                while update["type"] != "state.update":
                    update = await receive(ws)
                assert update["payload"]["section"] == "home"
                assert update["payload"]["value"]["tiles"][0]["state"] == "Aprinsă"


async def test_losing_home_assistant_sends_a_new_snapshot():
    source = HomeAssistantState(HA_ENTITIES)
    source.connected(HA_STATES)
    async with serving(Hub(source)) as url:
        ws, _ = await join(url)
        async with ws:
            source.disconnected()
            snapshot = await receive(ws)
            while snapshot["payload"]["home"]["summary"] != "Home Assistant nu răspunde":
                snapshot = await receive(ws)
            assert snapshot["type"] == "state.snapshot"
            assert snapshot["payload"]["home"]["tiles"][0]["state"] == "Indisponibil"
            assert "weather" not in snapshot["payload"] or snapshot["payload"]["weather"] is None


async def test_a_screen_that_left_does_not_stop_the_broadcast():
    source = HomeAssistantState(HA_ENTITIES)
    source.connected(HA_STATES)
    async with serving(Hub(source)) as url:
        gone, _ = await join(url, "gone")
        stays, _ = await join(url, "stays")
        await gone.close()
        async with stays:
            source.state_changed(
                {"entity_id": "light.office", "new_state": {"entity_id": "light.office", "state": "on"}}
            )
            update = await receive(stays)
            while update["type"] != "state.update":
                update = await receive(stays)
            assert update["payload"]["value"]["tiles"][0]["active"] is True
