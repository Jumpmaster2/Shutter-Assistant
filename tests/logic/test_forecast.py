"""High and night low from daily, twice daily and hourly forecasts."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from logic import forecast

TZ = ZoneInfo("Europe/Berlin")
DAY = date(2026, 7, 1)


def test_choose_kind() -> None:
    assert forecast.choose("hourly", 1) == "hourly"  # chosen by hand
    assert forecast.choose("auto", None) == "daily"  # unknown features: as before
    assert forecast.choose("auto", 1 | 2) == "daily"
    assert forecast.choose("auto", 2 | 4) == "twice_daily"
    assert forecast.choose("auto", 2) == "hourly"
    assert forecast.choose("auto", 0) is None


def test_daily() -> None:
    items = [{"temperature": 27, "templow": 12}, {"temperature": 25, "templow": 16}]
    assert forecast.summarize(items, "daily", DAY, TZ) == (27, 16)
    assert forecast.summarize(items[:1], "daily", DAY, TZ) == (27, 12)
    assert forecast.summarize([], "daily", DAY, TZ) == (None, None)


def test_hourly() -> None:
    start = datetime(2026, 7, 1, 0, 0, tzinfo=TZ)
    items = [
        {"datetime": (start + timedelta(hours=h)).isoformat(), "temperature": t}
        for h, t in [(6, 14), (14, 29), (17, 27), (22, 19), (28, 15), (34, 18), (40, 26)]
    ]
    # high of today, low between 18:00 and 09:00 of the next day
    assert forecast.summarize(items, "hourly", DAY, TZ) == (29, 15)


def test_twice_daily() -> None:
    items = [
        {"datetime": "2026-07-01T06:00:00+02:00", "is_daytime": True, "temperature": 28},
        {"datetime": "2026-07-01T18:00:00+02:00", "is_daytime": False, "temperature": 17},
        {"datetime": "2026-07-02T06:00:00+02:00", "is_daytime": True, "temperature": 30},
    ]
    assert forecast.summarize(items, "twice_daily", DAY, TZ) == (28, 17)


def test_forecast_without_dates() -> None:
    assert forecast.summarize([{"temperature": 20}], "hourly", DAY, TZ) == (None, None)
