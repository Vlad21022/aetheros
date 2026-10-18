"""The schema, the examples and the Python models must agree."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from aether_hub import protocol as p

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
SCHEMA = json.loads((CONTRACTS / "aether-protocol.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
EXAMPLES = sorted((CONTRACTS / "examples").glob("*.json"))


def test_schema_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_every_message_type_has_an_example():
    types = {ref["$ref"].removeprefix("#/$defs/msg.") for ref in SCHEMA["oneOf"]}
    assert types == {path.stem for path in EXAMPLES}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_matches_schema(path):
    VALIDATOR.validate(json.loads(path.read_text()))


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda path: path.stem)
def test_example_round_trips_through_models(path):
    raw = path.read_text()
    msg = p.parse(raw)
    assert msg.type == path.stem
    assert json.loads(p.dump(msg)) == json.loads(raw)


def test_messages_built_by_the_hub_match_schema():
    msg = p.new(p.AgentStatus, p.AgentStatusPayload(state="idle"), reply_to="s1")
    VALIDATOR.validate(json.loads(p.dump(msg)))


def test_schema_rejects_unknown_type():
    bad = {"v": 1, "type": "launch_missiles", "id": "x", "ts": "2026-10-10T13:25:00Z", "payload": {}}
    assert not VALIDATOR.is_valid(bad)


def test_home_cannot_be_cleared():
    bad = {
        "v": 1,
        "type": "state.update",
        "id": "x",
        "ts": "2026-10-10T13:25:00Z",
        "payload": {"section": "home", "value": None},
    }
    assert not VALIDATOR.is_valid(bad)
    with pytest.raises(ValueError):
        p.parse(json.dumps(bad))


def _message(kind: str, payload: dict) -> dict:
    return {"v": 1, "type": kind, "id": "x", "ts": "2026-10-10T13:25:00Z", "payload": payload}


@pytest.mark.parametrize("action", ["next", "previous"])
def test_control_can_skip_tracks(action):
    msg = _message("control", {"entityId": "media_player.living_room", "action": action})
    VALIDATOR.validate(msg)
    assert p.parse(json.dumps(msg)).payload.action == action


def test_snapshot_without_the_tap_fields_stays_valid():
    """What a hub from before tap, entityId and controls sends."""
    tile = {"entityId": "light.office", "kind": "light", "title": "Birou", "state": "Aprinsă", "active": True}
    playing = {"source": "TV", "title": "Film", "playing": True}
    msg = _message("state.snapshot", {"home": {"summary": "", "tiles": [tile]}, "nowPlaying": playing})
    VALIDATOR.validate(msg)
    parsed = p.parse(json.dumps(msg))
    assert parsed.payload.home.tiles[0].tap is None
    assert parsed.payload.nowPlaying.controls is None
    assert json.loads(p.dump(parsed)) == msg


@pytest.mark.parametrize(
    "change",
    [
        {"home": {"summary": "", "tiles": [{"tap": "set"}]}},
        {"nowPlaying": {"controls": ["toggle", "rewind"]}},
        {"nowPlaying": {"controls": ["next", "next"]}},
    ],
)
def test_schema_rejects_taps_it_does_not_know(change):
    tile = {"entityId": "light.office", "kind": "light", "title": "Birou", "state": "Aprinsă", "active": True}
    payload = {
        "home": {"summary": "", "tiles": [tile]},
        "nowPlaying": {"source": "TV", "title": "Film", "playing": True},
    }
    if "home" in change:
        payload["home"]["tiles"][0].update(change["home"]["tiles"][0])
    else:
        payload["nowPlaying"].update(change["nowPlaying"])
    assert not VALIDATOR.is_valid(_message("state.snapshot", payload))


def test_glance_travels_in_snapshot_and_update():
    payload = {"home": {"summary": "", "tiles": []}, "glance": "Sala la 18:30 · ploaie de la 19:00"}
    VALIDATOR.validate(_message("state.snapshot", payload))
    assert p.parse(json.dumps(_message("state.snapshot", payload))).payload.glance == payload["glance"]
    for value in ("Sala până la 19:30", None):
        update = _message("state.update", {"section": "glance", "value": value})
        VALIDATOR.validate(update)
        parsed = p.parse(json.dumps(update))
        assert parsed.payload.value == value
        assert json.loads(p.dump(parsed)) == update


@pytest.mark.parametrize(
    "payload",
    [
        {"section": "glance", "value": ""},
        {"section": "glance", "value": "x" * 121},
        {"section": "glance", "value": {"temperatureC": 1, "condition": "x"}},
        {"section": "weather", "value": "Sala la 18:30"},
    ],
)
def test_glance_is_a_short_string_and_only_glance_is_a_string(payload):
    msg = _message("state.update", payload)
    assert not VALIDATOR.is_valid(msg)
    with pytest.raises(ValueError):
        p.parse(json.dumps(msg))
