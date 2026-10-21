"""Weather protection: wind, rain and frost.

A protection turns on as soon as its value crosses the threshold and turns off
only after the value has stayed on the safe side for the release time. An
invalid value (sensor unavailable) changes nothing: a failing sensor never ends
a running protection.
"""

from __future__ import annotations

from dataclasses import dataclass

from .conditions import as_float

WIND = "wind"
RAIN = "rain"
FROST = "frost"
KINDS = (WIND, RAIN, FROST)


@dataclass
class Guard:
    """State of one protection (on immediately, off after the release time)."""

    release: float
    active: bool = False
    release_due: float | None = None

    def update(self, over: bool | None, now: float) -> bool:
        """``over``: value on the dangerous side (None = invalid). True if it changed."""
        if over is None:
            # the release starts again once the value is valid
            self.release_due = None
            return False
        if over:
            changed = not self.active
            self.active = True
            self.release_due = None
            return changed
        if not self.active:
            return False
        if self.release_due is None:
            self.release_due = now + self.release
        if now >= self.release_due:
            self.active = False
            self.release_due = None
            return True
        return False

    def due(self) -> float | None:
        """Time at which the protection may end (None if not pending)."""
        return self.release_due if self.active else None


def above(value: object, threshold: float) -> bool | None:
    """Wind: number above the threshold. None for an invalid value."""
    number = as_float(value)
    return None if number is None else number > threshold


def raining(value: object, threshold: float) -> bool | None:
    """Rain: a binary state (on/off) or an amount above the threshold."""
    if value == "on":
        return True
    if value == "off":
        return False
    return above(value, threshold)


def freezing(value: float | None, threshold: float) -> bool | None:
    """Frost: outdoor temperature at or below the threshold."""
    return None if value is None else value <= threshold
