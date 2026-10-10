"""Where the ambient screen's data comes from.

Phase 0 serves fixed demo data so the screen can be built against a real hub.
Phase 1 replaces it with a Home Assistant source behind the same interface.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from . import protocol as p


class StateSource(Protocol):
    async def snapshot(self) -> p.SnapshotPayload: ...


class DemoState:
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


def demo_state() -> StateSource:
    return DemoState()
