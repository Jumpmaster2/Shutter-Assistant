"""Sun sectors and crossing times."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer
from logic import sun

TZ = ZoneInfo("Europe/Berlin")
OBSERVER = Observer(latitude=48.14, longitude=11.58, elevation=0)  # Munich


def test_in_sector_bounds_are_exclusive() -> None:
    assert sun.in_sector(180, 90, 270)
    assert not sun.in_sector(90, 90, 270)
    assert not sun.in_sector(270, 90, 270)
    assert not sun.in_sector(300, 90, 270)


def test_sector_wrapping_north() -> None:
    assert sun.in_sector(350, 300, 30)
    assert sun.in_sector(10, 300, 30)
    assert not sun.in_sector(100, 300, 30)
    assert sun.past_sector_end(100, 300, 30)
    assert not sun.past_sector_end(350, 300, 30)


def test_past_sector_end_normal() -> None:
    assert sun.past_sector_end(270, 90, 270)
    assert sun.past_sector_end(300, 90, 270)
    assert not sun.past_sector_end(200, 90, 270)
    assert not sun.past_sector_end(10, 90, 270)


def test_next_azimuth_crossing_hits_the_angle() -> None:
    start = datetime(2026, 7, 1, 6, 0, tzinfo=TZ)
    for angle in (90.0, 180.0, 270.0):
        when = sun.next_azimuth_crossing(OBSERVER, start, angle)
        assert when is not None
        assert start < when < start + timedelta(hours=18)
        assert abs(sun.azimuth(OBSERVER, when) - angle) < 0.1
    # order of the day
    east = sun.next_azimuth_crossing(OBSERVER, start, 90.0)
    south = sun.next_azimuth_crossing(OBSERVER, start, 180.0)
    assert east is not None and south is not None and east < south


def test_next_crossing_after_the_angle_is_tomorrow() -> None:
    start = datetime(2026, 7, 1, 15, 0, tzinfo=TZ)
    when = sun.next_azimuth_crossing(OBSERVER, start, 180.0)
    assert when is not None and when.astimezone(TZ).date() == date(2026, 7, 2)


def test_crossing_near_north_through_midnight() -> None:
    start = datetime(2026, 7, 1, 20, 0, tzinfo=TZ)
    when = sun.next_azimuth_crossing(OBSERVER, start, 359.0)
    assert when is not None
    assert abs(sun.azimuth(OBSERVER, when) - 359.0) < 0.2


def test_time_at_elevation_and_sunrise() -> None:
    day = date(2026, 12, 21)
    setting = sun.time_at_elevation(OBSERVER, day, -4.0, rising=False, tz=TZ)
    rise = sun.sunrise(OBSERVER, day, TZ)
    assert setting is not None and rise is not None
    assert setting.hour == 16
    assert rise.hour in (7, 8)


def test_never_reached_elevation_returns_none() -> None:
    polar = Observer(latitude=78.2, longitude=15.6, elevation=0)
    assert sun.time_at_elevation(polar, date(2026, 6, 21), -4.0, rising=False, tz=TZ) is None
    assert sun.sunrise(polar, date(2026, 6, 21), TZ) is None
