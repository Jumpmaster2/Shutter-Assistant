"""Today's high and the low of the coming night from a weather forecast."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

from .conditions import as_float

DAILY = "daily"
TWICE_DAILY = "twice_daily"
HOURLY = "hourly"
# WeatherEntityFeature.FORECAST_DAILY / FORECAST_HOURLY / FORECAST_TWICE_DAILY
FEATURES = {DAILY: 1, HOURLY: 2, TWICE_DAILY: 4}
# preferred order when the kind is chosen automatically
PREFERENCE = (DAILY, TWICE_DAILY, HOURLY)
# the coming night: from the evening of the day to the next morning
NIGHT_START = time(18, 0)
NIGHT_END = time(9, 0)


def supported(features: int) -> list[str]:
    """Forecast kinds a weather entity supports, in the preferred order."""
    return [kind for kind in PREFERENCE if features & FEATURES[kind]]


def choose(option: str, features: int | None) -> str | None:
    """The kind to request: the chosen one, or the first supported one ("auto").

    ``features`` None (unknown) keeps the old behaviour: daily.
    """
    if option in FEATURES:
        return option
    if features is None:
        return DAILY
    kinds = supported(features)
    return kinds[0] if kinds else None


def _time(item: Mapping[str, Any], tz: tzinfo) -> datetime | None:
    value = item.get("datetime")
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def _night_low_daily(forecast: list[Mapping[str, Any]]) -> float | None:
    """The low of tomorrow is the early morning after this night; without it today's."""
    for item in forecast[1:2] + forecast[:1]:
        if (low := as_float(item.get("templow"))) is not None:
            return low
    return None


def summarize(
    forecast: Iterable[Mapping[str, Any]], kind: str, day: date, tz: tzinfo
) -> tuple[float | None, float | None]:
    """(high of ``day``, low of the night after ``day``).

    Daily: the first entry is today. Twice daily and hourly: the entries of the
    day give the high (twice daily: the day parts), the entries starting in the
    night (18:00 to 09:00) give the low (``templow`` if there is one).
    """
    items = [item for item in forecast if isinstance(item, Mapping)]
    if not items:
        return None, None
    if kind == DAILY:
        return as_float(items[0].get("temperature")), _night_low_daily(items)
    dated = [(moment, item) for item in items if (moment := _time(item, tz)) is not None]
    today = [item for moment, item in dated if moment.date() == day]
    if kind == TWICE_DAILY:
        day_parts = [item for item in today if item.get("is_daytime") is not False]
        today = day_parts or today
    highs = [v for item in today if (v := as_float(item.get("temperature"))) is not None]
    start = datetime.combine(day, NIGHT_START, tz)
    end = datetime.combine(day + timedelta(days=1), NIGHT_END, tz)
    lows: list[float] = []
    for moment, item in dated:
        in_night = start <= moment < end
        if kind == TWICE_DAILY:
            # the night part starts in the evening (some services: at noon)
            in_night = (
                item.get("is_daytime") is False and start - timedelta(hours=6) <= moment < end
            )
        if not in_night:
            continue
        value = as_float(item.get("templow"))
        if value is None:
            value = as_float(item.get("temperature"))
        if value is not None:
            lows.append(value)
    return (max(highs) if highs else None), (min(lows) if lows else None)
