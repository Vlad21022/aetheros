"""The line under the far clock: the most useful thing right now, in one line.

Pure rules over a snapshot and the time. The hub adds the result to every snapshot
and sends a glance update when it changes. See docs/decisions.md, 024.
"""

from __future__ import annotations

from datetime import datetime

from . import protocol as p

MAX_LENGTH = 120
SEPARATOR = " · "


def glance(snapshot: p.SnapshotPayload, now: datetime) -> str | None:
    """`now` must be timezone-aware, in the home's zone."""
    parts = [part for part in (_event(snapshot.nextEvent, now), _weather(snapshot.weather)) if part]
    if not parts:
        return None
    text = SEPARATOR.join(parts)
    return text if len(text) <= MAX_LENGTH else text[: MAX_LENGTH - 1].rstrip() + "…"


def with_glance(snapshot: p.SnapshotPayload, now: datetime) -> p.SnapshotPayload:
    """The snapshot with its glance set. Left unset when there is nothing to say, so
    the field is omitted on the wire rather than sent as null."""
    text = glance(snapshot, now)
    return snapshot if text is None else snapshot.model_copy(update={"glance": text})


def _event(event: p.Event | None, now: datetime) -> str | None:
    if event is None:
        return None
    start = event.start.astimezone(now.tzinfo)
    if start > now:
        # Only today's: tomorrow's event is not what matters right now.
        return f"{event.title} la {_hm(start)}" if start.date() == now.date() else None
    if event.end is not None and now < event.end:
        return f"{event.title} până la {_hm(event.end.astimezone(now.tzinfo))}"
    return None


def _weather(weather: p.Weather | None) -> str | None:
    if weather is None:
        return None
    if weather.summary:
        return weather.summary
    return f"{round(weather.temperatureC)}° · {weather.condition}"


def _hm(t: datetime) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"
