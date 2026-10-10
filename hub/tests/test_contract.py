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
