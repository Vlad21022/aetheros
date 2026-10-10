"""Home Assistant states → what the ambient screen shows.

Pure functions: no network, no clock. All Romanian text for home data lives here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import protocol as p
from .config import Entities, TileConfig

UNAVAILABLE = "Indisponibil"
SUMMARY_OK = "Totul e în regulă"
SUMMARY_SOME_DOWN = "Unele dispozitive nu răspund"
SUMMARY_NO_HA = "Home Assistant nu răspunde"

_DOWN = {"unavailable", "unknown"}

_KIND_BY_DOMAIN: dict[str, p.TileKind] = {
    "light": "light",
    "switch": "switch",
    "lock": "lock",
    "climate": "climate",
    "media_player": "media",
    "cover": "cover",
}

_LOCK = {
    "locked": "Încuiată",
    "unlocked": "Descuiată",
    "locking": "Se încuie",
    "unlocking": "Se descuie",
    "jammed": "Blocată",
    "open": "Deschisă",
    "opening": "Se deschide",
}

_COVER = {"open": "Deschis", "closed": "Închis", "opening": "Se deschide", "closing": "Se închide"}

_MEDIA = {"playing": "Redă", "paused": "În pauză", "buffering": "Se încarcă"}

_WEATHER = {
    "clear-night": "Senin",
    "cloudy": "Înnorat",
    "exceptional": "Vreme neobișnuită",
    "fog": "Ceață",
    "hail": "Grindină",
    "lightning": "Furtună",
    "lightning-rainy": "Furtună cu ploaie",
    "partlycloudy": "Parțial înnorat",
    "pouring": "Ploaie torențială",
    "rainy": "Ploaie",
    "snowy": "Ninsoare",
    "snowy-rainy": "Lapoviță",
    "sunny": "Însorit",
    "windy": "Vânt",
    "windy-variant": "Vânt și nori",
}


@dataclass(frozen=True)
class EntityState:
    """One entity as Home Assistant reports it."""

    entity_id: str
    state: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: Mapping[str, Any]) -> EntityState:
        return cls(
            entity_id=str(data["entity_id"]),
            state=str(data.get("state", "unknown")),
            attributes=data.get("attributes") or {},
        )

    @property
    def domain(self) -> str:
        return self.entity_id.partition(".")[0]

    @property
    def name(self) -> str:
        return str(self.attributes.get("friendly_name") or self.entity_id)

    @property
    def down(self) -> bool:
        return self.state in _DOWN


States = Mapping[str, EntityState]


def home(entities: Entities, states: States, *, connected: bool = True) -> p.Home:
    tiles = [tile(config, states) for config in entities.home.tiles]
    if not connected:
        summary = SUMMARY_NO_HA
    elif any(_is_down(states.get(config.entity)) for config in entities.home.tiles):
        summary = SUMMARY_SOME_DOWN
    else:
        summary = SUMMARY_OK
    return p.Home(summary=summary, tiles=tiles)


def tile(config: TileConfig, states: States) -> p.Tile:
    entity = states.get(config.entity)
    domain = config.entity.partition(".")[0]
    kind = config.kind or _kind(domain, entity)

    if entity is None or entity.down:
        title = config.title or (entity.name if entity else config.entity)
        return p.Tile(entityId=config.entity, kind=kind, title=_fit(title), state=UNAVAILABLE, active=False)

    title = config.title or entity.name
    match domain:
        case "light":
            text, active = _light(entity, states)
        case "switch" | "input_boolean":
            active = entity.state == "on"
            text = "Pornit" if active else "Oprit"
        case "lock":
            active = entity.state == "locked"
            text = _LOCK.get(entity.state, entity.state)
        case "cover":
            active = entity.state not in ("closed", "closing")
            text = _COVER.get(entity.state, entity.state)
        case "media_player":
            active = entity.state == "playing"
            text = _MEDIA.get(entity.state, "Oprit")
        case "climate":
            # As in the design: the reading is the title, the room is the line under it.
            reading = _number(entity.attributes.get("current_temperature"))
            active = entity.state not in ("off", "idle")
            text, title = title, f"{reading} °C" if reading else UNAVAILABLE
        case "sensor":
            unit = str(entity.attributes.get("unit_of_measurement") or "")
            reading = _number(entity.state) or entity.state
            active = False
            text, title = title, f"{reading} {unit}".strip()
        case _:
            active = entity.state == "on"
            text = entity.state
    return p.Tile(entityId=config.entity, kind=kind, title=_fit(title), state=_fit(text), active=active)


def weather(entity_id: str | None, states: States) -> p.Weather | None:
    entity = states.get(entity_id) if entity_id else None
    if entity is None or entity.down:
        return None
    temperature = _float(entity.attributes.get("temperature"))
    if temperature is None:
        return None
    if entity.attributes.get("temperature_unit") == "°F":
        temperature = (temperature - 32) * 5 / 9
    return p.Weather(temperatureC=round(temperature, 1), condition=_WEATHER.get(entity.state, entity.state)[:60])


def next_event(entity_id: str | None, states: States) -> p.Event | None:
    """The current or next event of a calendar entity, from its attributes."""
    entity = states.get(entity_id) if entity_id else None
    if entity is None or entity.down:
        return None
    title = entity.attributes.get("message")
    start = _time(entity.attributes.get("start_time"))
    if not title or start is None:
        return None
    location = entity.attributes.get("location")
    return p.Event(
        title=str(title)[:120],
        start=start,
        end=_time(entity.attributes.get("end_time")),
        note=str(location)[:160] if location else None,
    )


def now_playing(entity_id: str | None, states: States) -> p.NowPlaying | None:
    entity = states.get(entity_id) if entity_id else None
    if entity is None or entity.state not in _MEDIA:
        return None
    attributes = entity.attributes
    title = attributes.get("media_title") or attributes.get("app_name")
    if not title:
        return None
    subtitle = attributes.get("media_artist") or attributes.get("media_album_name")
    position, duration = _float(attributes.get("media_position")), _float(attributes.get("media_duration"))
    progress = min(max(position / duration, 0.0), 1.0) if position is not None and duration else None
    return p.NowPlaying(
        source=entity.name[:80],
        title=str(title)[:120],
        subtitle=str(subtitle)[:120] if subtitle else None,
        playing=entity.state == "playing",
        progress=progress,
    )


def snapshot(entities: Entities, states: States, *, connected: bool = True) -> p.SnapshotPayload:
    sections = entities.sections
    return p.SnapshotPayload(
        home=home(entities, states, connected=connected),
        weather=weather(sections.weather, states),
        nextEvent=next_event(sections.calendar, states),
        nowPlaying=now_playing(sections.now_playing, states),
    )


def _kind(domain: str, entity: EntityState | None) -> p.TileKind:
    if domain == "sensor" and entity is not None and entity.attributes.get("device_class") == "temperature":
        return "climate"
    return _KIND_BY_DOMAIN.get(domain, "sensor")


def _is_down(entity: EntityState | None) -> bool:
    return entity is None or entity.down


def _light(entity: EntityState, states: States) -> tuple[str, bool]:
    members = entity.attributes.get("entity_id")
    if isinstance(members, list) and members:
        on = sum(1 for member in members if (found := states.get(str(member))) is not None and found.state == "on")
        if on == 0:
            return "Stinse", False
        if on == 1:
            return "1 aprinsă", True
        # Romanian puts "de" after numbers ending in 00 or 20–99.
        return (f"{on} de aprinse" if on % 100 == 0 or on % 100 >= 20 else f"{on} aprinse"), True
    active = entity.state == "on"
    return ("Aprinsă" if active else "Stinsă"), active


def _float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _number(value: object) -> str | None:
    """21.5 → "21,5", 21.0 → "21". None when the value is not a number."""
    number = _float(value)
    if number is None:
        return None
    return f"{number:.1f}".removesuffix(".0").replace(".", ",")


def _time(value: object) -> datetime | None:
    """Calendar attributes carry local wall-clock times ("2026-10-10 18:30:00")."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # A naive time is in Home Assistant's zone, which is the hub's: same house.
    return parsed.astimezone()


def _fit(text: str) -> str:
    return text if len(text) <= 60 else text[:59] + "…"
