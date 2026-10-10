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
    def __init__(self) -> None:
        self._changes: asyncio.Queue[Change] = asyncio.Queue()

    async def snapshot(self) -> p.SnapshotPayload:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        return p.SnapshotPayload(
            home=p.Home(
                summary="Totul e în regulă",
                tiles=[
                    p.Tile(entityId="light.group_on", kind="light", title="Lumini", state="3 aprinse", active=True),
                    p.Tile(entityId="lock.front_door", kind="lock", title="Ușa", state="Încuiată", active=True),
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
                source="HomePod sufragerie", title="Seară", subtitle="Playlist", playing=False, progress=0.38
            ),
        )

    async def updates(self) -> AsyncIterator[Change]:
        while True:
            yield await self._changes.get()
