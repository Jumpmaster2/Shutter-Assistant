"""Evening mode: when it starts and when it ends."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo


@dataclass(frozen=True)
class EveningSettings:
    """Evening starts when the sun is below ``elevation`` but never before
    ``earliest`` and at the latest at ``latest``."""

    earliest: time
    elevation: float
    latest: time


def evening_day(now: datetime, night_end: time) -> date:
    """The evening ``now`` belongs to (before the night end it is still yesterday's)."""
    if now.timetz().replace(tzinfo=None) < night_end:
        return now.date() - timedelta(days=1)
    return now.date()


def evening_start(
    day: date, tz: tzinfo, settings: EveningSettings, below_elevation_at: datetime | None
) -> datetime:
    """Start of the evening of ``day``.

    ``below_elevation_at`` is the time the sun drops below the elevation on that
    day (None if it never does, then the latest time applies).
    """
    earliest = datetime.combine(day, settings.earliest, tz)
    latest = datetime.combine(day, settings.latest, tz)
    by_sun = latest if below_elevation_at is None else min(below_elevation_at, latest)
    return max(earliest, by_sun)


def evening_end(day: date, tz: tzinfo, night_end: time, next_sunrise: datetime | None) -> datetime:
    """End of the evening of ``day``: night end of the next day or sunrise, whichever is first."""
    end = datetime.combine(day + timedelta(days=1), night_end, tz)
    if next_sunrise is not None and next_sunrise < end:
        return next_sunrise
    return end


def is_evening(now: datetime, start: datetime, end: datetime) -> bool:
    return start <= now < end
