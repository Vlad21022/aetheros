"""Talk to a real hub over a real WebSocket, the way a screen will."""

import asyncio
import contextlib
import json

import pytest
from fake_ha import TOKEN
from jsonschema import Draft202012Validator, FormatChecker
from test_contract import SCHEMA
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from aether_hub.config import Entities, HomeAssistantConfig, Settings
from aether_hub.ha_state import HomeAssistantState
from aether_hub.server import Hub, build
from aether_hub.tier0 import Tier0Router

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
    async with serving(build(Settings())[0]) as url:
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
    async with serving(Hub(source, Tier0Router([], None))) as url:
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
    async with serving(Hub(source, Tier0Router([], None))) as url:
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
    async with serving(Hub(source, Tier0Router([], None))) as url:
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


def control(entity_id: str, action: str = "toggle", message_id: str = "s9") -> str:
    return json.dumps(
        {**HELLO, "type": "control", "id": message_id, "payload": {"entityId": entity_id, "action": action}}
    )


async def next_of(ws, kind: str):
    msg = await receive(ws)
    while msg["type"] != kind:
        msg = await receive(ws)
    return msg


async def test_demo_home_answers_a_control(url):
    kitchen, snapshot = await join(url, "kitchen")
    office, _ = await join(url, "office")
    async with kitchen, office:
        assert snapshot["payload"]["home"]["tiles"][0]["state"] == "3 aprinse"
        await kitchen.send(control("light.group_on"))
        result = await next_of(kitchen, "action.result")
        assert result["replyTo"] == "s9" and result["payload"]["ok"] is True
        for ws in (kitchen, office):
            update = await next_of(ws, "state.update")
            assert update["payload"]["value"]["tiles"][0] == {
                "entityId": "light.group_on",
                "kind": "light",
                "title": "Lumini",
                "state": "Stinse",
                "active": False,
                "tap": "toggle",
            }


@pytest.mark.parametrize(
    ("entity_id", "action", "code"),
    [
        ("light.nowhere", "toggle", "unknown_entity"),
        ("lock.front_door", "toggle", "not_allowed"),
        ("aether.pc_office", "turn_off", "not_allowed"),
        ("sensor.living_room_temperature", "set", "not_allowed"),
    ],
)
async def test_controls_that_are_refused(url, entity_id, action, code):
    ws, _ = await join(url)
    async with ws:
        await ws.send(control(entity_id, action))
        error = await receive(ws)
        assert (error["type"], error["replyTo"], error["payload"]["code"]) == ("error", "s9", code)


@pytest.fixture
async def ha_hub(fake_ha, tmp_path):
    """A hub wired to the stand-in Home Assistant, the way `run` wires it."""
    await fake_ha.set_state("light.office", "off", {"friendly_name": "Birou"})
    await fake_ha.set_state("lock.front_door", "locked")
    player = {"media_title": "Film", "friendly_name": "TV", "supported_features": 16384 | 1 | 32}
    await fake_ha.set_state("media_player.tv", "playing", player)
    settings = Settings(
        home_assistant=HomeAssistantConfig(url=fake_ha.url, token=TOKEN),
        entities=Entities.model_validate(
            {
                "home": {"tiles": [{"entity": "light.office"}, {"entity": "lock.front_door"}]},
                "sections": {"now_playing": "media_player.tv"},
            }
        ),
    )
    hub, client = build(settings)
    client._retry_delays = (0.01,)
    connected = asyncio.Event()
    on_connected = client._on_connected
    client._on_connected = lambda states: (on_connected(states), connected.set())
    task = asyncio.create_task(client.run())
    async with serving(hub) as url:
        async with asyncio.timeout(2):
            await connected.wait()
        yield url
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_control_reaches_home_assistant_and_comes_back_as_state(ha_hub, fake_ha):
    ws, snapshot = await join(ha_hub)
    async with ws:
        assert snapshot["payload"]["home"]["tiles"][0] == {
            "entityId": "light.office",
            "kind": "light",
            "title": "Birou",
            "state": "Stinsă",
            "active": False,
            "tap": "toggle",
        }
        await ws.send(control("light.office", "turn_on"))
        assert (await next_of(ws, "action.result"))["payload"]["ok"] is True
        assert fake_ha.calls == [("light", "turn_on", "light.office")]
        update = await next_of(ws, "state.update")
        assert update["payload"]["value"]["tiles"][0]["state"] == "Aprinsă"


async def test_play_pause_goes_through_the_now_playing_entity(ha_hub, fake_ha):
    ws, snapshot = await join(ha_hub)
    async with ws:
        assert snapshot["payload"]["nowPlaying"]["playing"] is True
        await ws.send(control("media_player.tv"))
        await next_of(ws, "action.result")
        assert fake_ha.calls == [("media_player", "media_play_pause", "media_player.tv")]
        update = await next_of(ws, "state.update")
        assert (update["payload"]["section"], update["payload"]["value"]["playing"]) == ("nowPlaying", False)


async def test_unlock_is_refused_before_it_reaches_home_assistant(ha_hub, fake_ha):
    ws, _ = await join(ha_hub)
    async with ws:
        await ws.send(control("lock.front_door", "turn_off"))
        assert (await receive(ws))["payload"]["code"] == "not_allowed"
        assert fake_ha.calls == []


async def test_a_change_made_in_home_assistant_reaches_the_screen(ha_hub, fake_ha):
    ws, _ = await join(ha_hub)
    async with ws:
        await fake_ha.set_state("light.office", "on")
        update = await next_of(ws, "state.update")
        assert update["payload"]["value"]["tiles"][0]["active"] is True


async def test_a_service_home_assistant_refuses_is_reported(ha_hub, fake_ha):
    fake_ha.fail_services = True
    ws, _ = await join(ha_hub)
    async with ws:
        await ws.send(control("light.office"))
        result = await next_of(ws, "action.result")
        assert result["payload"] == {"ok": False, "message": "Nu a mers. Home Assistant a refuzat comanda."}


async def test_home_assistant_going_away_is_said_out_loud(ha_hub, fake_ha):
    ws, _ = await join(ha_hub)
    async with ws:
        await fake_ha.stop()
        await fake_ha.drop_connections()
        snapshot = await next_of(ws, "state.snapshot")
        assert snapshot["payload"]["home"]["summary"] == "Home Assistant nu răspunde"
        assert "nowPlaying" not in snapshot["payload"]
        await ws.send(control("light.office"))
        error = await next_of(ws, "error")
        assert error["payload"]["code"] == "unavailable"


async def test_demo_home_skips_tracks(url):
    ws, snapshot = await join(url)
    async with ws:
        playing = snapshot["payload"]["nowPlaying"]
        assert (playing["entityId"], playing["controls"]) == (
            "media_player.living_room",
            ["previous", "toggle", "next"],
        )
        await ws.send(control(playing["entityId"], "next"))
        update = await next_of(ws, "state.update")
        assert update["payload"]["value"]["title"] != playing["title"]
        await ws.send(control(playing["entityId"], "previous"))
        update = await next_of(ws, "state.update")
        assert update["payload"]["value"]["title"] == playing["title"]


async def test_next_track_reaches_home_assistant(ha_hub, fake_ha):
    ws, snapshot = await join(ha_hub)
    async with ws:
        assert snapshot["payload"]["nowPlaying"]["controls"] == ["toggle", "next"]
        await ws.send(control("media_player.tv", "next"))
        assert (await next_of(ws, "action.result"))["payload"]["ok"] is True
        assert fake_ha.calls == [("media_player", "media_next_track", "media_player.tv")]
