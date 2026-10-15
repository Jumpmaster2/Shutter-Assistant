"""Conditions with hold times and sensor thresholds."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass
class Hold:
    """On only after the input has been true for ``hold`` seconds, off immediately.

    ``since`` is the time the input became true. After a restart the input is
    evaluated again and the hold starts at that moment.
    """

    hold: float
    since: float | None = None

    def update(self, value: bool, now: float) -> None:
        if not value:
            self.since = None
        elif self.since is None:
            self.since = now

    def state(self, now: float) -> bool:
        return self.since is not None and now - self.since >= self.hold

    def due(self, now: float) -> float | None:
        """Time at which the state turns on (None if not pending)."""
        if self.since is None or self.state(now):
            return None
        return self.since + self.hold


@dataclass
class FollowUp:
    """On immediately while the input is true, stays on ``delay`` seconds after it ends."""

    delay: float
    until: float | None = None
    active: bool = False

    def update(self, value: bool, now: float) -> None:
        if value:
            self.active = True
            self.until = None
        elif self.active:
            self.active = False
            self.until = now + self.delay

    def state(self, now: float) -> bool:
        return self.active or (self.until is not None and now < self.until)

    def due(self, now: float) -> float | None:
        if self.active or self.until is None or now >= self.until:
            return None
        return self.until


def as_float(value: object) -> float | None:
    """Numeric value of a state, None for unavailable or non numeric states."""
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN
        return None
    return result


def at_least(value: object, threshold: float) -> bool:
    """value >= threshold; unknown values never pass."""
    number = as_float(value)
    return number is not None and number >= threshold


def sensors_ok(values: Mapping[str, Iterable[object]], thresholds: Mapping[str, float]) -> bool:
    """All sensors of every type reach the threshold of their type.

    ``values`` maps a sensor type (pv, lux, radiation) to the current states of
    the sensors of that type. Types without sensors are ignored.
    """
    for kind, states in values.items():
        threshold = thresholds.get(kind)
        for state in states:
            if threshold is None or not at_least(state, threshold):
                return False
    return True


def summer_day(forecast_max: float | None, threshold: float, raised_today: bool) -> bool:
    """Summer day: forecast high reaches the threshold, or the outdoor temperature
    exceeded it today."""
    if raised_today:
        return True
    return forecast_max is not None and forecast_max >= threshold
