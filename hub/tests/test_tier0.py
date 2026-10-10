"""The tier 0 rules: which taps become which Home Assistant services."""

import pytest

from aether_hub import protocol as p
from aether_hub.ha_client import HaError, HaUnavailable
from aether_hub.tier0 import REFUSED, RULES, SENT, Tier0Error, Tier0Router, tap_action

ENTITIES = ["light.office", "switch.plug", "media_player.tv", "lock.front_door", "cover.garage", "climate.living"]


class Home:
    def __init__(self, fails_with: Exception | None = None) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.fails_with = fails_with

    async def call_service(self, domain: str, service: str, entity_id: str) -> None:
        if self.fails_with is not None:
            raise self.fails_with
        self.calls.append((domain, service, entity_id))


def control(entity_id: str, action: str, value=None) -> p.ControlPayload:
    return p.ControlPayload(entityId=entity_id, action=action, value=value)


@pytest.mark.parametrize(
    ("entity_id", "action", "service"),
    [
        ("light.office", "toggle", "toggle"),
        ("light.office", "turn_on", "turn_on"),
        ("light.office", "turn_off", "turn_off"),
        ("switch.plug", "toggle", "toggle"),
        ("switch.plug", "turn_on", "turn_on"),
        ("switch.plug", "turn_off", "turn_off"),
        ("media_player.tv", "toggle", "media_play_pause"),
        ("media_player.tv", "next", "media_next_track"),
        ("media_player.tv", "previous", "media_previous_track"),
        ("lock.front_door", "turn_on", "lock"),
    ],
)
async def test_allowed_controls_call_the_service(entity_id, action, service):
    home = Home()
    result = await Tier0Router(ENTITIES, home).control(control(entity_id, action))
    assert home.calls == [(entity_id.partition(".")[0], service, entity_id)]
    assert (result.ok, result.message) == (True, SENT)


def test_every_rule_is_tested():
    tested = {
        ("light", "toggle"),
        ("light", "turn_on"),
        ("light", "turn_off"),
        ("switch", "toggle"),
        ("switch", "turn_on"),
        ("switch", "turn_off"),
        ("media_player", "toggle"),
        ("media_player", "next"),
        ("media_player", "previous"),
        ("lock", "turn_on"),
    }
    assert set(RULES) == tested, "a new tier 0 rule needs a case in test_allowed_controls_call_the_service"


@pytest.mark.parametrize("action", ["toggle", "turn_off", "set"])
async def test_a_tap_never_unlocks_a_door(action):
    home = Home()
    with pytest.raises(Tier0Error, match="confirmation") as error:
        await Tier0Router(ENTITIES, home).control(control("lock.front_door", action))
    assert error.value.code == "not_allowed"
    assert home.calls == []


@pytest.mark.parametrize(
    ("entity_id", "action"),
    [
        ("cover.garage", "toggle"),
        ("climate.living", "set"),
        ("light.office", "set"),
        ("light.office", "next"),
        ("media_player.tv", "turn_off"),
    ],
)
async def test_everything_else_is_refused(entity_id, action):
    home = Home()
    with pytest.raises(Tier0Error) as error:
        await Tier0Router(ENTITIES, home).control(control(entity_id, action, 21))
    assert error.value.code == "not_allowed"
    assert home.calls == []


async def test_entities_outside_the_config_cannot_be_controlled():
    home = Home()
    with pytest.raises(Tier0Error) as error:
        await Tier0Router(ENTITIES, home).control(control("light.neighbour", "toggle"))
    assert error.value.code == "unknown_entity"
    assert home.calls == []


async def test_home_assistant_away_is_unavailable():
    router = Tier0Router(ENTITIES, Home(fails_with=HaUnavailable("not connected")))
    with pytest.raises(Tier0Error) as error:
        await router.control(control("light.office", "toggle"))
    assert error.value.code == "unavailable"


async def test_a_refused_service_is_reported_not_raised():
    router = Tier0Router(ENTITIES, Home(fails_with=HaError("Service failed")))
    result = await router.control(control("light.office", "toggle"))
    assert (result.ok, result.message) == (False, REFUSED)


@pytest.mark.parametrize(
    ("entity_id", "state", "action"),
    [
        ("light.office", "on", "toggle"),
        ("light.office", "off", "toggle"),
        ("switch.plug", "on", "toggle"),
        ("lock.front_door", "unlocked", "turn_on"),
        ("lock.front_door", "locked", None),
        ("lock.front_door", "jammed", None),
        ("sensor.temperature", "21.5", None),
        ("climate.living", "heat", None),
        ("cover.garage", "closed", None),
        ("media_player.tv", "playing", None),
    ],
)
def test_what_a_tap_on_a_tile_sends(entity_id, state, action):
    assert tap_action(entity_id, state) == action
    if action is not None:
        assert (entity_id.partition(".")[0], action) in RULES, "a tile must not offer what tier 0 refuses"
