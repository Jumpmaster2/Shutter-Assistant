"""Manual override: tell own movements from manual ones and compute the end."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

MOVING = ("opening", "closing")
INVALID = ("unavailable", "unknown")
STATIONARY_TOLERANCE = 2


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

    def pending(self, cover: str) -> bool:
        return cover in self._commands

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


def override_until(
    now: datetime, duration_minutes: float, next_sunrise: datetime | None
) -> datetime | None:
    """End of an override started now. Duration 0 means until the next sunrise."""
    if duration_minutes > 0:
        return now + timedelta(minutes=duration_minutes)
    return next_sunrise
