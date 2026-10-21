"""Manual override: tell own movements from manual ones and compute the end."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

MOVING = ("opening", "closing")
INVALID = ("unavailable", "unknown")
STATIONARY_TOLERANCE = 2
# Without a sunrise (polar day or night) an override until sunrise ends after this time.
NO_SUNRISE_FALLBACK = timedelta(hours=24)


@dataclass
class _Command:
    target: int | None
    context_id: str | None
    last_seen: float
    reached_at: float | None = None


@dataclass
class CommandTracker:
    """Remembers the movements Shutter Assistant started itself.

    A command stays responsible for all state reports of its cover until the
    cover stands still at the target plus a short grace period (late position
    reports), or until nothing happened for ``timeout`` seconds.
    """

    timeout: float = 120.0
    grace: float = 15.0
    _commands: dict[str, _Command] = field(default_factory=dict)

    def register(self, cover: str, target: int | None, context_id: str | None, now: float) -> None:
        self._commands[cover] = _Command(target, context_id, now)

    def explains(
        self,
        cover: str,
        context_id: str | None,
        state: str,
        position: int | None,
        now: float,
    ) -> bool:
        """Is this state report caused by our own command?"""
        command = self._commands.get(cover)
        if command is None:
            return False
        if context_id is not None and context_id == command.context_id:
            command.last_seen = now
            return True
        if now - command.last_seen > self.timeout or (
            command.reached_at is not None and now - command.reached_at > self.grace
        ):
            del self._commands[cover]
            return False
        command.last_seen = now
        if state not in MOVING and (
            command.target is None
            or position is None
            or abs(position - command.target) <= STATIONARY_TOLERANCE
        ):
            command.reached_at = command.reached_at or now
        return True


def is_manual(
    *,
    own: bool,
    parent_id: str | None,
    old_state: str | None,
    new_state: str,
    old_position: int | None,
    new_position: int | None,
) -> bool:
    """A movement counts as manual if it was not started by Shutter Assistant,
    not by another automation or script (context with parent), starts from a
    standing cover and really changes something."""
    if own or parent_id is not None or old_state is None:
        return False
    if old_state in MOVING or old_state in INVALID or new_state in INVALID:
        return False
    return old_state != new_state or old_position != new_position


@dataclass
class _Start:
    state: str
    position: float | None
    since: float


@dataclass
class MovementWatch:
    """Override only after a real movement.

    Remembers where a cover stood when a manual command began and reports once
    it has really moved. A command to a cover already at its target (e.g. "open
    all" while it is open) makes many covers report opening and open again
    without a change of position; that is no movement.
    """

    timeout: float = 180.0
    _starts: dict[str, _Start] = field(default_factory=dict)

    def update(
        self,
        cover: str,
        *,
        started: bool,
        own: bool,
        old_state: str | None,
        old_position: float | None,
        new_state: str,
        new_position: float | None,
        now: float,
    ) -> bool:
        """True once the cover really moved after a manual command (``started``)."""
        if own or new_state in INVALID:
            self._starts.pop(cover, None)
            return False
        start = self._starts.get(cover)
        if start is not None and now - start.since > self.timeout:
            del self._starts[cover]
            start = None
        if start is None:
            if not started or old_state is None:
                return False
            start = self._starts[cover] = _Start(old_state, old_position, now)
        if _moved(start, new_state, new_position):
            del self._starts[cover]
            return True
        if new_state not in MOVING:
            # standing again where it started: the command changed nothing
            del self._starts[cover]
        return False


def _moved(start: _Start, state: str, position: float | None) -> bool:
    if start.position is not None and position is not None:
        return abs(position - start.position) > STATIONARY_TOLERANCE
    # covers without a position: standing in another state than before
    return state not in MOVING and state != start.state


def override_until(
    now: datetime, duration_minutes: float, next_sunrise: datetime | None
) -> datetime:
    """End of an override started now. Duration 0 means until the next sunrise
    (without a sunrise, e.g. in polar regions, after 24 hours)."""
    if duration_minutes > 0:
        return now + timedelta(minutes=duration_minutes)
    return next_sunrise if next_sunrise is not None else now + NO_SUNRISE_FALLBACK


def reached(target: int, position: int | None, state: str | None, tolerance: int = 5) -> bool:
    """Did a cover reach the target of a command? Without a position only the end
    positions can be checked (open or closed)."""
    if position is not None:
        return abs(position - target) <= tolerance
    if target >= 100:
        return state == "open"
    if target <= 0:
        return state == "closed"
    return True
