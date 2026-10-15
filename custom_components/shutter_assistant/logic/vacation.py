"""Vacation simulation: random times and positions."""

from __future__ import annotations

import random
from datetime import datetime, timedelta


def random_time(start: datetime, window_minutes: float, rng: random.Random) -> datetime:
    """A random time between ``start`` and ``start + window`` (whole seconds)."""
    seconds = max(0, int(window_minutes * 60))
    return start + timedelta(seconds=rng.randint(0, seconds))


def random_position(low: int, high: int, rng: random.Random) -> int:
    """A random position between ``low`` and ``high`` (inclusive)."""
    low, high = sorted((int(low), int(high)))
    return rng.randint(low, high)
