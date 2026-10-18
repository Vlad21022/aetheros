"""Where the ambient screen's data comes from.

`DemoState` serves fixed demo data, for tests and for running without Home
Assistant. `HomeAssistantState` (ha_state.py) is the real source behind the same
interface.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Protocol

from . import protocol as p

Change = p.UpdatePayload | p.SnapshotPayload
"""One changed section, or everything again (after the source reconnects)."""

_SECTIONS = ("home", "weather", "nextEvent", "nowPlaying")


class StateSource(Protocol):
    async def snapshot(self) -> p.SnapshotPayload: ...

    def updates(self) -> AsyncIterator[Change]:
        """Changes since the last snapshot, as they happen. One consumer: the hub."""
        ...


def changed_sections(old: p.SnapshotPayload, new: p.SnapshotPayload) -> list[p.UpdatePayload]:
    """A state.update payload for each section that differs between two snapshots."""
    return [
        p.UpdatePayload(section=section, value=getattr(new, section))
        for section in _SECTIONS
        if getattr(old, section) != getattr(new, section)
    ]


class DemoState:
    """A made-up home that also reacts to tier 0 service calls, in memory."""

    LIGHTS = "light.group_on"
    LOCK = "lock.front_door"
    PLAYER = "media_player.living_room"
    TRACKS = ("Seară", "Dimineață lentă", "Concentrare")
    entities = (LIGHTS, LOCK, "sensor.living_room_temperature", "aether.pc_office", PLAYER)

    def __init__(self) -> None:
        self._lights_on = True
        self._locked = True
        self._playing = False
        self._track = 0
        self._changes: asyncio.Queue[Change] = asyncio.Queue()

    async def snapshot(self) -> p.SnapshotPayload:
        return self._build()

    async def call_service(self, domain: str, service: str, entity_id: str) -> None:
        old = self._build()
        match entity_id, service:
            case self.LIGHTS, "toggle":
                self._lights_on = not self._lights_on
            case self.LIGHTS, "turn_on" | "turn_off":
                self._lights_on = service == "turn_on"
            case self.LOCK, "lock":
                self._locked = True
            case self.PLAYER, "media_play_pause":
                self._playing = not self._playing
            case self.PLAYER, "media_next_track":
                self._track = (self._track + 1) % len(self.TRACKS)
            case self.PLAYER, "media_previous_track":
                self._track = (self._track - 1) % len(self.TRACKS)
        for update in changed_sections(old, self._build()):
            self._changes.put_nowait(update)

    def _build(self) -> p.SnapshotPayload:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        return p.SnapshotPayload(
            home=p.Home(
                summary="Totul e în regulă",
                tiles=[
                    p.Tile(
                        entityId=self.LIGHTS,
                        kind="light",
                        title="Lumini",
                        state="3 aprinse" if self._lights_on else "Stinse",
                        active=self._lights_on,
                        tap="toggle",
                    ),
                    p.Tile(
                        entityId=self.LOCK,
                        kind="lock",
                        title="Ușa",
                        state="Încuiată" if self._locked else "Descuiată",
                        active=self._locked,
                    ),
                    p.Tile(
                        entityId="sensor.living_room_temperature",
                        kind="climate",
                        title="21,5 °C",
                        state="Sufragerie",
                        active=False,
                    ),
                    p.Tile(
                        entityId="aether.pc_office", kind="computer", title="PC birou", state="Doarme", active=False
                    ),
                ],
            ),
            weather=p.Weather(temperatureC=14, condition="Înnorat", summary="ploaie de la 19:00"),
            nextEvent=p.Event(
                title="Antrenament la sală",
                start=now + timedelta(hours=2),
                end=now + timedelta(hours=3),
                note="Demo: datele reale vin din calendar în faza 1.",
            ),
            nowPlaying=p.NowPlaying(
                source="HomePod sufragerie",
                title=self.TRACKS[self._track],
                subtitle="Playlist",
                playing=self._playing,
                progress=0.38,
                entityId=self.PLAYER,
                controls=["previous", "toggle", "next"],
            ),
        )

    async def updates(self) -> AsyncIterator[Change]:
        while True:
            yield await self._changes.get()
