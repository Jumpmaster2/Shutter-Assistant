"""Morning opening times and vacation randomness."""

import random
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from logic import morning, vacation

TZ = ZoneInfo("Europe/Berlin")
DAY = date(2026, 10, 15)  # Thursday


def at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    return datetime.combine(day, time(hour, minute), TZ)


def settings(**kwargs) -> morning.MorningSettings:
    base = {"mode": morning.MODE_TIME, "earliest": time(6, 0), "latest": time(9, 0)}
    return morning.MorningSettings(**{**base, **kwargs})


def test_workday() -> None:
    assert morning.is_workday(DAY, None)
    assert not morning.is_workday(date(2026, 10, 17), None)
    assert not morning.is_workday(DAY, "off")  # holiday by sensor
    assert morning.is_workday(date(2026, 10, 17), "on")


def test_fixed_time() -> None:
    s = settings(workday_time=time(6, 30), weekend_time=time(8, 15))
    assert morning.planned_time(DAY, TZ, s, workday=True) == at(6, 30)
    assert morning.planned_time(DAY, TZ, s, workday=False) == at(8, 15)


def test_fixed_time_is_clamped() -> None:
    s = settings(workday_time=time(5, 0))
    assert morning.planned_time(DAY, TZ, s, workday=True) == at(6, 0)


def test_sun_with_offset() -> None:
    s = settings(mode=morning.MODE_SUN, sun_offset=30)
    assert morning.planned_time(DAY, TZ, s, workday=True, sunrise=at(7, 40)) == at(8, 10)
    s = settings(mode=morning.MODE_SUN, sun_event=morning.SUN_ELEVATION, sun_offset=-10)
    assert morning.planned_time(DAY, TZ, s, workday=True, elevation_time=at(8, 0)) == at(7, 50)
    assert morning.planned_time(DAY, TZ, s, workday=True) == at(9, 0)


def test_trigger_time() -> None:
    s = settings(mode=morning.MODE_TRIGGER, trigger_offset=5)
    assert morning.planned_time(DAY, TZ, s, workday=True, trigger_time=at(6, 45)) == at(6, 50)
    # alarm of another day: latest time as fallback
    other = at(6, 45, date(2026, 10, 16))
    assert morning.planned_time(DAY, TZ, s, workday=True, trigger_time=other) == at(9, 0)


def test_event_driven_modes_fall_back_to_latest() -> None:
    s = settings(mode=morning.MODE_BRIGHTNESS)
    assert morning.planned_time(DAY, TZ, s, workday=True) == at(9, 0)


def test_vacation_random_values_stay_in_range() -> None:
    rng = random.Random(1)
    start = at(7, 0)
    for _ in range(200):
        when = vacation.random_time(start, 60, rng)
        assert at(7, 0) <= when <= at(8, 0)
        assert 60 <= vacation.random_position(60, 100, rng) <= 100
    assert vacation.random_position(100, 60, rng) in range(60, 101)
