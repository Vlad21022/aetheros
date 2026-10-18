"""The rules for the line under the far clock."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from aether_hub import protocol as p
from aether_hub.glance import glance, with_glance

HOME = timezone(timedelta(hours=3))
NOW = datetime(2026, 10, 10, 16, 25, tzinfo=HOME)
EMPTY = p.SnapshotPayload(home=p.Home(summary="", tiles=[]))


def snapshot(event: p.Event | None = None, weather: p.Weather | None = None) -> p.SnapshotPayload:
    fields = {"home": EMPTY.home}
    if event is not None:
        fields["nextEvent"] = event
    if weather is not None:
        fields["weather"] = weather
    return p.SnapshotPayload(**fields)


def event(start: datetime, end: datetime | None = None, title: str = "Sala") -> p.Event:
    return p.Event(title=title, start=start, end=end) if end else p.Event(title=title, start=start)


RAIN = p.Weather(temperatureC=14, condition="Înnorat", summary="ploaie de la 19:00")
CLOUDY = p.Weather(temperatureC=14.4, condition="Înnorat")


def test_an_event_later_today():
    assert glance(snapshot(event(datetime(2026, 10, 10, 18, 30, tzinfo=HOME))), NOW) == "Sala la 18:30"


def test_event_times_are_shown_in_the_home_zone():
    start = datetime(2026, 10, 10, 15, 30, tzinfo=UTC)
    assert glance(snapshot(event(start)), NOW) == "Sala la 18:30"


def test_an_event_under_way_says_until_when():
    s = snapshot(event(NOW - timedelta(minutes=10), NOW + timedelta(minutes=50)))
    assert glance(s, NOW) == "Sala până la 17:15"


@pytest.mark.parametrize(
    "e",
    [
        event(datetime(2026, 10, 11, 9, 0, tzinfo=HOME)),
        event(NOW - timedelta(hours=2), NOW - timedelta(hours=1)),
        event(NOW - timedelta(hours=1)),
    ],
    ids=["tomorrow", "over", "started-without-end"],
)
def test_events_that_do_not_matter_now_are_left_out(e):
    assert glance(snapshot(e), NOW) is None


def test_weather_summary_wins_over_the_reading():
    assert glance(snapshot(weather=RAIN), NOW) == "ploaie de la 19:00"
    assert glance(snapshot(weather=CLOUDY), NOW) == "14° · Înnorat"


def test_event_then_weather():
    s = snapshot(event(datetime(2026, 10, 10, 18, 30, tzinfo=HOME)), RAIN)
    assert glance(s, NOW) == "Sala la 18:30 · ploaie de la 19:00"


def test_nothing_to_say():
    assert glance(EMPTY, NOW) is None
    assert with_glance(EMPTY, NOW) is EMPTY
    assert "glance" not in p.dump(p.new(p.StateSnapshot, with_glance(EMPTY, NOW)))


def test_long_lines_are_cut_to_the_protocol_limit():
    s = snapshot(event(datetime(2026, 10, 10, 18, 30, tzinfo=HOME), title="A" * 120), RAIN)
    text = glance(s, NOW)
    assert len(text) == 120 and text.endswith("…")
    p.UpdatePayload(section="glance", value=text)


def test_with_glance_sets_the_field_on_the_wire():
    wire = p.dump(p.new(p.StateSnapshot, with_glance(snapshot(weather=RAIN), NOW)))
    assert '"glance":"ploaie de la 19:00"' in wire


class OneEvent:
    """A state source with one event and no changes."""

    def __init__(self, e: p.Event) -> None:
        self.e = e

    async def snapshot(self) -> p.SnapshotPayload:
        return snapshot(self.e)

    async def updates(self):
        return
        yield


async def test_the_minute_tick_moves_the_glance_with_the_clock():
    from pathlib import Path

    from aether_hub.pairing import Pairing
    from aether_hub.server import Hub
    from aether_hub.tier0 import Tier0Router

    clock = [NOW]
    hub = Hub(
        OneEvent(event(NOW + timedelta(minutes=5), NOW + timedelta(hours=1))),
        Tier0Router([], None),
        Pairing(Path("unused") / "screens.json"),
        now=lambda: clock[0],
    )
    await hub.broadcast()  # seeds the last glance; the source has no changes
    assert hub._glance == "Sala la 16:30"

    sent = []
    hub._to_all = lambda msg: _record(sent, msg)
    await hub.refresh_glance()
    assert sent == []

    clock[0] = NOW + timedelta(minutes=10)
    await hub.refresh_glance()
    assert [m.payload.value for m in sent] == ["Sala până la 17:25"]

    clock[0] = NOW + timedelta(hours=2)
    await hub.refresh_glance()
    assert [m.payload.value for m in sent] == ["Sala până la 17:25", None]


async def _record(sent: list, msg) -> None:
    sent.append(msg)
