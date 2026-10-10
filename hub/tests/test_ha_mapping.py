"""Home Assistant states become the tiles and widgets of the ambient screen."""

from datetime import datetime

import pytest

from aether_hub import ha_mapping as m
from aether_hub.config import Entities, SectionsConfig, TileConfig
from aether_hub.ha_mapping import EntityState


def states(*entities: EntityState) -> dict[str, EntityState]:
    return {entity.entity_id: entity for entity in entities}


def one(entity: EntityState, **config) -> m.p.Tile:
    return m.tile(TileConfig(entity=entity.entity_id, **config), states(entity))


def test_from_json_reads_a_home_assistant_state():
    entity = EntityState.from_json(
        {"entity_id": "light.office", "state": "on", "attributes": {"friendly_name": "Birou"}, "last_changed": "x"}
    )
    assert (entity.domain, entity.name, entity.state, entity.down) == ("light", "Birou", "on", False)


@pytest.mark.parametrize(("state", "text", "active"), [("on", "Aprinsă", True), ("off", "Stinsă", False)])
def test_single_light(state, text, active):
    tile = one(EntityState("light.office", state, {"friendly_name": "Birou"}))
    assert (tile.kind, tile.title, tile.state, tile.active) == ("light", "Birou", text, active)


@pytest.mark.parametrize(
    ("on", "text", "active"),
    [(0, "Stinse", False), (1, "1 aprinsă", True), (3, "3 aprinse", True), (20, "20 de aprinse", True)],
)
def test_light_group_counts_its_lights(on, text, active):
    members = [EntityState(f"light.l{i}", "on" if i < on else "off") for i in range(22)]
    group = EntityState("light.all", "on" if on else "off", {"entity_id": [x.entity_id for x in members]})
    tile = m.tile(TileConfig(entity="light.all", title="Lumini"), states(group, *members))
    assert (tile.title, tile.state, tile.active) == ("Lumini", text, active)


@pytest.mark.parametrize(
    ("state", "text", "active"),
    [("locked", "Încuiată", True), ("unlocked", "Descuiată", False), ("jammed", "Blocată", False)],
)
def test_lock(state, text, active):
    tile = one(EntityState("lock.front_door", state), title="Ușa")
    assert (tile.kind, tile.state, tile.active) == ("lock", text, active)


def test_switch_cover_and_media_player():
    assert one(EntityState("switch.plug", "on")).state == "Pornit"
    cover = one(EntityState("cover.blinds", "closed"))
    assert (cover.kind, cover.state, cover.active) == ("cover", "Închis", False)
    media = one(EntityState("media_player.tv", "paused"))
    assert (media.kind, media.state, media.active) == ("media", "În pauză", False)
    assert one(EntityState("media_player.tv", "idle")).state == "Oprit"


def test_temperature_sensor_shows_the_reading_as_title():
    entity = EntityState(
        "sensor.living_room_temperature",
        "21.5",
        {"unit_of_measurement": "°C", "device_class": "temperature", "friendly_name": "Temperatură sufragerie"},
    )
    tile = one(entity, title="Sufragerie")
    assert (tile.kind, tile.title, tile.state, tile.active) == ("climate", "21,5 °C", "Sufragerie", False)
    assert one(EntityState("sensor.t", "21.0", {"unit_of_measurement": "°C"})).title == "21 °C"


def test_other_sensor_keeps_its_unit_and_kind():
    tile = one(EntityState("sensor.power", "340", {"unit_of_measurement": "W", "friendly_name": "Consum"}))
    assert (tile.kind, tile.title, tile.state) == ("sensor", "340 W", "Consum")


def test_climate_entity_shows_the_current_temperature():
    tile = one(EntityState("climate.living", "heat", {"current_temperature": 22, "friendly_name": "Sufragerie"}))
    assert (tile.kind, tile.title, tile.state, tile.active) == ("climate", "22 °C", "Sufragerie", True)


def test_kind_can_be_set_in_the_config():
    assert one(EntityState("switch.pc_office", "off"), kind="computer").kind == "computer"


@pytest.mark.parametrize("state", ["unavailable", "unknown"])
def test_entity_that_does_not_answer(state):
    tile = one(EntityState("light.office", state, {"friendly_name": "Birou"}))
    assert (tile.title, tile.state, tile.active) == ("Birou", m.UNAVAILABLE, False)


def test_entity_home_assistant_does_not_know():
    tile = m.tile(TileConfig(entity="light.ghost"), {})
    assert (tile.kind, tile.title, tile.state) == ("light", "light.ghost", m.UNAVAILABLE)


def test_long_names_fit_the_protocol():
    tile = one(EntityState("light.office", "on", {"friendly_name": "L" * 200}))
    assert len(tile.title) == 60


def test_home_summary():
    entities = Entities.model_validate({"home": {"tiles": [{"entity": "light.a"}, {"entity": "lock.b"}]}})
    ok = states(EntityState("light.a", "on"), EntityState("lock.b", "locked"))
    assert m.home(entities, ok).summary == m.SUMMARY_OK
    assert [tile.entityId for tile in m.home(entities, ok).tiles] == ["light.a", "lock.b"]
    assert m.home(entities, states(EntityState("light.a", "on"))).summary == m.SUMMARY_SOME_DOWN
    down = m.home(entities, {}, connected=False)
    assert down.summary == m.SUMMARY_NO_HA
    assert [tile.state for tile in down.tiles] == [m.UNAVAILABLE, m.UNAVAILABLE]


def test_weather():
    entity = EntityState("weather.home", "cloudy", {"temperature": 14.2, "temperature_unit": "°C"})
    weather = m.weather("weather.home", states(entity))
    assert (weather.temperatureC, weather.condition, weather.summary) == (14.2, "Înnorat", None)


def test_weather_in_fahrenheit_is_converted():
    entity = EntityState("weather.home", "sunny", {"temperature": 68, "temperature_unit": "°F"})
    assert m.weather("weather.home", states(entity)).temperatureC == 20.0


def test_weather_is_hidden_when_there_is_nothing_to_show():
    assert m.weather(None, {}) is None
    assert m.weather("weather.home", {}) is None
    assert m.weather("weather.home", states(EntityState("weather.home", "unavailable"))) is None
    assert m.weather("weather.home", states(EntityState("weather.home", "sunny"))) is None


def test_unknown_weather_condition_is_passed_through():
    entity = EntityState("weather.home", "tornado", {"temperature": 10})
    assert m.weather("weather.home", states(entity)).condition == "tornado"


def test_next_event():
    entity = EntityState(
        "calendar.personal",
        "off",
        {
            "message": "Antrenament la sală",
            "start_time": "2026-10-10 18:30:00",
            "end_time": "2026-10-10 19:30:00",
            "location": "World Class",
        },
    )
    event = m.next_event("calendar.personal", states(entity))
    assert (event.title, event.note) == ("Antrenament la sală", "World Class")
    assert event.start == datetime(2026, 10, 10, 18, 30).astimezone()
    assert event.start.tzinfo is not None
    assert event.end == datetime(2026, 10, 10, 19, 30).astimezone()


def test_calendar_without_an_event():
    assert m.next_event("calendar.personal", states(EntityState("calendar.personal", "off"))) is None
    assert m.next_event(None, {}) is None
    broken = EntityState("calendar.personal", "off", {"message": "X", "start_time": "soon"})
    assert m.next_event("calendar.personal", states(broken)) is None


def test_now_playing():
    entity = EntityState(
        "media_player.living_room",
        "paused",
        {
            "friendly_name": "HomePod sufragerie",
            "media_title": "Seară",
            "media_artist": "Playlist",
            "media_position": 38,
            "media_duration": 100,
        },
    )
    playing = m.now_playing("media_player.living_room", states(entity))
    assert (playing.source, playing.title, playing.subtitle) == ("HomePod sufragerie", "Seară", "Playlist")
    assert (playing.playing, playing.progress) == (False, 0.38)


def test_now_playing_is_hidden_when_nothing_plays():
    idle = EntityState("media_player.living_room", "idle", {"media_title": "Seară"})
    assert m.now_playing("media_player.living_room", states(idle)) is None
    untitled = EntityState("media_player.living_room", "playing")
    assert m.now_playing("media_player.living_room", states(untitled)) is None
    assert m.now_playing(None, {}) is None


def test_progress_stays_between_zero_and_one():
    entity = EntityState(
        "media_player.tv", "playing", {"media_title": "Film", "media_position": 120, "media_duration": 100}
    )
    assert m.now_playing("media_player.tv", states(entity)).progress == 1.0


def test_snapshot_puts_the_sections_together():
    entities = Entities(sections=SectionsConfig(weather="weather.home"))
    snapshot = m.snapshot(entities, states(EntityState("weather.home", "rainy", {"temperature": 9})))
    assert snapshot.weather.condition == "Ploaie"
    assert snapshot.nextEvent is None and snapshot.nowPlaying is None
    assert snapshot.home.tiles == []
