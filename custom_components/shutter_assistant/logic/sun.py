"""Sun position: azimuth sectors and the times the sun crosses them."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, tzinfo

from astral import Observer, SunDirection
from astral import sun as astral_sun

SCAN_STEP = timedelta(minutes=10)
PRECISION = timedelta(seconds=1)


def azimuth(observer: Observer, when: datetime) -> float:
    """Azimuth of the sun in degrees (0 = north, 90 = east)."""
    return float(astral_sun.azimuth(observer, when))


def in_sector(az: float, start: float, end: float) -> bool:
    """Is the azimuth strictly inside the sector?

    Bounds are exclusive. A sector with ``start > end`` wraps around north.
    """
    if start <= end:
        return start < az < end
    return az > start or az < end


def past_sector_end(az: float, start: float, end: float) -> bool:
    """Has the sun left the sector at its end bound (sun moves with rising azimuth)?

    For a normal sector this is ``az >= end`` (until the azimuth wraps at north,
    i.e. around midnight). For a sector wrapping around north it is the part
    between the end and the start.
    """
    if start <= end:
        return az >= end
    return end <= az <= start


def _signed_diff(a: float, b: float) -> float:
    """Signed angle difference a - b in (-180, 180]."""
    diff = (a - b) % 360.0
    return diff - 360.0 if diff > 180.0 else diff


def next_azimuth_crossing(
    observer: Observer, start: datetime, angle: float, horizon: timedelta = timedelta(hours=36)
) -> datetime | None:
    """Next time after ``start`` when the azimuth rises through ``angle``."""
    return _next_crossing(lambda t: _signed_diff(azimuth(observer, t), angle), start, horizon)


def _next_crossing(
    func: Callable[[datetime], float], start: datetime, horizon: timedelta
) -> datetime | None:
    """First time the function changes from negative to non-negative."""
    t0 = start
    v0 = func(t0)
    end = start + horizon
    while t0 < end:
        t1 = t0 + SCAN_STEP
        v1 = func(t1)
        # A jump of almost 360 degrees is the wrap on the opposite side, not a crossing.
        if v0 < 0 <= v1 and v1 - v0 < 180:
            low, high = t0, t1
            while high - low > PRECISION:
                mid = low + (high - low) / 2
                if func(mid) < 0:
                    low = mid
                else:
                    high = mid
            return high
        t0, v0 = t1, v1
    return None


def time_at_elevation(
    observer: Observer, day: date, degrees: float, rising: bool, tz: tzinfo
) -> datetime | None:
    """Time on ``day`` when the sun passes the elevation (None if it never does)."""
    direction = SunDirection.RISING if rising else SunDirection.SETTING
    try:
        return astral_sun.time_at_elevation(observer, degrees, day, direction, tzinfo=tz)
    except ValueError:
        return None


def sunrise(observer: Observer, day: date, tz: tzinfo) -> datetime | None:
    """Sunrise on ``day`` (None in polar day or night)."""
    try:
        return astral_sun.sunrise(observer, day, tzinfo=tz)
    except ValueError:
        return None
