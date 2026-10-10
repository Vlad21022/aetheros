"""HomeAssistantState turns what the client reports into snapshots and updates."""

import asyncio

from aether_hub import ha_mapping as m
from aether_hub import protocol as p
from aether_hub.config import Entities
from aether_hub.ha_state import HomeAssistantState
from aether_hub.state import DemoState, changed_sections

ENTITIES = Entities.model_validate(
    {
        "home": {"tiles": [{"entity": "light.office", "title": "Birou"}, {"entity": "lock.front_door"}]},
        "sections": {"weather": "weather.home", "now_playing": "media_player.living_room"},
    }
)
STATES = [
    {"entity_id": "light.office", "state": "off", "attributes": {}},
    {"entity_id": "lock.front_door", "state": "locked", "attributes": {"friendly_name": "Ușa"}},
    {"entity_id": "weather.home", "state": "cloudy", "attributes": {"temperature": 14}},
    {"entity_id": "sun.sun", "state": "below_horizon", "attributes": {}},
]


def changed(entity_id: str, state: str | None, attributes: dict | None = None) -> dict:
    new = None if state is None else {"entity_id": entity_id, "state": state, "attributes": attributes or {}}
    return {"entity_id": entity_id, "old_state": None, "new_state": new}


async def drain(source: HomeAssistantState) -> list:
    """Everything queued so far."""
    found = []
    updates = source.updates()
    try:
        while True:
            found.append(await asyncio.wait_for(anext(updates), 0.01))
    except TimeoutError:
        return found


async def test_before_home_assistant_answers_nothing_is_invented():
    source = HomeAssistantState(ENTITIES)
    snapshot = await source.snapshot()
    assert snapshot.home.summary == m.SUMMARY_NO_HA
    assert [tile.state for tile in snapshot.home.tiles] == [m.UNAVAILABLE, m.UNAVAILABLE]
    assert snapshot.weather is None and snapshot.nextEvent is None and snapshot.nowPlaying is None
    assert await drain(source) == []


async def test_connecting_publishes_a_full_snapshot():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    snapshot = await source.snapshot()
    assert [(tile.title, tile.state) for tile in snapshot.home.tiles] == [("Birou", "Stinsă"), ("Ușa", "Încuiată")]
    assert snapshot.home.summary == m.SUMMARY_OK
    assert snapshot.weather.condition == "Înnorat"
    assert await drain(source) == [snapshot]


async def test_a_change_updates_only_its_section():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    await drain(source)

    source.state_changed(changed("light.office", "on"))
    (update,) = await drain(source)
    assert isinstance(update, p.UpdatePayload) and update.section == "home"
    assert update.value.tiles[0].state == "Aprinsă"
    assert (await source.snapshot()).home == update.value

    source.state_changed(changed("weather.home", "rainy", {"temperature": 9}))
    (update,) = await drain(source)
    assert (update.section, update.value.condition) == ("weather", "Ploaie")


async def test_changes_nobody_shows_are_not_sent():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    await drain(source)
    source.state_changed(changed("sun.sun", "above_horizon"))
    source.state_changed(changed("light.office", "off"))
    source.state_changed({"old_state": None})
    assert await drain(source) == []


async def test_a_section_can_appear_and_clear():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    await drain(source)
    playing = {"media_title": "Seară", "friendly_name": "HomePod"}
    source.state_changed(changed("media_player.living_room", "playing", playing))
    (update,) = await drain(source)
    assert (update.section, update.value.title) == ("nowPlaying", "Seară")
    source.state_changed(changed("media_player.living_room", "idle"))
    (update,) = await drain(source)
    assert (update.section, update.value) == ("nowPlaying", None)
    p.dump(p.new(p.StateUpdate, update))


async def test_removed_entity_becomes_unavailable():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    await drain(source)
    source.state_changed(changed("light.office", None))
    (update,) = await drain(source)
    assert update.value.tiles[0].state == m.UNAVAILABLE
    assert update.value.summary == m.SUMMARY_SOME_DOWN


async def test_losing_home_assistant_is_shown_not_hidden():
    source = HomeAssistantState(ENTITIES)
    source.connected(STATES)
    await drain(source)
    source.disconnected()
    source.disconnected()
    (snapshot,) = await drain(source)
    assert isinstance(snapshot, p.SnapshotPayload)
    assert snapshot.home.summary == m.SUMMARY_NO_HA
    assert [tile.state for tile in snapshot.home.tiles] == [m.UNAVAILABLE, m.UNAVAILABLE]
    assert snapshot.weather is None

    source.connected(STATES)
    (snapshot,) = await drain(source)
    assert snapshot.home.summary == m.SUMMARY_OK


async def test_changed_sections_compares_two_snapshots():
    demo = await DemoState().snapshot()
    assert changed_sections(demo, demo) == []
    other = demo.model_copy(update={"weather": None, "nowPlaying": None})
    assert [(u.section, u.value) for u in changed_sections(demo, other)] == [("weather", None), ("nowPlaying", None)]
