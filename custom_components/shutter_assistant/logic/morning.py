"""Morning opening: when a window opens in the morning."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo

MODE_TIME = "time"
MODE_SUN = "sun"
MODE_BRIGHTNESS = "brightness"
MODE_TRIGGER = "trigger"
MODES = [MODE_TIME, MODE_SUN, MODE_BRIGHTNESS, MODE_TRIGGER]

SUN_SUNRISE = "sunrise"
SUN_ELEVATION = "elevation"


@dataclass(frozen=True)
class MorningSettings:
    mode: str
    earliest: time
    latest: time
    workday_time: time = time(6, 30)
    weekend_time: time = time(8, 0)
    sun_event: str = SUN_SUNRISE
    sun_elevation: float = 0.0
    sun_offset: float = 0.0
    trigger_offset: float = 0.0


WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def is_workday(
    day: date, workday_state: str | None, weekend: Iterable[str] = ("sat", "sun")
) -> bool:
    """Workday sensor wins; without it every day outside ``weekend`` is a workday."""
    if workday_state in ("on", "off"):
        return workday_state == "on"
    return WEEKDAY_KEYS[day.weekday()] not in set(weekend)


def bounds(day: date, tz: tzinfo, settings: MorningSettings) -> tuple[datetime, datetime]:
    return (
        datetime.combine(day, settings.earliest, tz),
        datetime.combine(day, settings.latest, tz),
    )


def clamp(value: datetime, low: datetime, high: datetime) -> datetime:
    return max(low, min(value, high))


def planned_time(
    day: date,
    tz: tzinfo,
    settings: MorningSettings,
    *,
    workday: bool,
    sunrise: datetime | None = None,
    elevation_time: datetime | None = None,
    trigger_time: datetime | None = None,
) -> datetime:
    """Planned opening time on ``day``.

    For brightness and for a trigger entity without a time (motion, switch) the
    opening is event driven; the planned time is then the latest time as fallback.
    """
    low, high = bounds(day, tz, settings)
    if settings.mode == MODE_TIME:
        chosen = settings.workday_time if workday else settings.weekend_time
        return clamp(datetime.combine(day, chosen, tz), low, high)
    if settings.mode == MODE_SUN:
        base = sunrise if settings.sun_event == SUN_SUNRISE else elevation_time
        if base is None:
            return high
        return clamp(base + timedelta(minutes=settings.sun_offset), low, high)
    if settings.mode == MODE_TRIGGER and trigger_time is not None:
        when = trigger_time + timedelta(minutes=settings.trigger_offset)
        if when.astimezone(tz).date() == day:
            return clamp(when, low, high)
    return high
