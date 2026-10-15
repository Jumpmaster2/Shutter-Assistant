"""Evening start and end."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from logic.evening import EveningSettings, evening_day, evening_end, evening_start, is_evening

TZ = ZoneInfo("Europe/Berlin")
SETTINGS = EveningSettings(earliest=time(17, 0), elevation=-4.0, latest=time(21, 0))
DAY = date(2026, 10, 15)


def at(hour: int, minute: int = 0, day: date = DAY) -> datetime:
    return datetime.combine(day, time(hour, minute), TZ)


def test_sun_between_earliest_and_latest() -> None:
    assert evening_start(DAY, TZ, SETTINGS, at(19, 7)) == at(19, 7)


def test_never_before_earliest() -> None:
    assert evening_start(DAY, TZ, SETTINGS, at(16, 50)) == at(17, 0)


def test_latest_time_fallback() -> None:
    assert evening_start(DAY, TZ, SETTINGS, at(22, 15)) == at(21, 0)
    assert evening_start(DAY, TZ, SETTINGS, None) == at(21, 0)


def test_evening_day_switches_at_night_end() -> None:
    night_end = time(3, 30)
    assert evening_day(at(2, 0, date(2026, 10, 16)), night_end) == DAY
    assert evening_day(at(3, 30, date(2026, 10, 16)), night_end) == date(2026, 10, 16)
    assert evening_day(at(23, 0), night_end) == DAY


def test_end_is_night_end_or_earlier_sunrise() -> None:
    sunrise = at(7, 50, date(2026, 10, 16))
    assert evening_end(DAY, TZ, time(3, 30), sunrise) == at(3, 30, date(2026, 10, 16))
    early_sunrise = at(3, 0, date(2026, 10, 16))
    assert evening_end(DAY, TZ, time(3, 30), early_sunrise) == early_sunrise


def test_is_evening() -> None:
    start, end = at(19, 7), at(3, 30, date(2026, 10, 16))
    assert not is_evening(at(19, 6), start, end)
    assert is_evening(at(19, 7), start, end)
    assert is_evening(at(2, 0, date(2026, 10, 16)), start, end)
    assert not is_evening(at(3, 30, date(2026, 10, 16)), start, end)
