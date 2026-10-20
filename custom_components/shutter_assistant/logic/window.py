"""Rules for one window: what to do in a given situation.

Every function receives the configuration and a snapshot of the current
situation and returns the actions to execute. The engine decides when a rule
is evaluated (which event triggers it); the functions themselves have no state.
"""

from __future__ import annotations

from dataclasses import dataclass

OPEN = 100
CLOSED = 0

# Action kinds
POSITION = "position"
MARK_SUN = "mark_sun"
CLEAR_SUN = "clear_sun"
MARK_EVENING = "mark_evening"
CLEAR_EVENING = "clear_evening"
NOTIFY = "notify"

# Reasons (also used for the logbook and the "last reason" sensor)
R_SUN_LOWER = "sun_lower"
R_SUN_ALREADY = "sun_already"
R_SUN_BLOCKED = "sun_blocked_window"
R_SUN_MANUAL = "sun_manual"
R_SUN_POSITION_MANUAL = "sun_position_manual"
R_AUTO_UP = "auto_up"
R_EVENING = "evening_close"
R_FOLLOW_UP = "follow_up_close"
R_VENTILATION = "ventilation"
R_TRIGGER = "trigger_close"
R_VACATION_OPEN = "vacation_open"
R_VACATION_CLOSE = "vacation_close"
R_MORNING = "morning_open"
R_MORNING_SUN = "morning_sun"

# Status values of a window
S_OFF = "off"
S_STARTUP = "startup"
S_OVERRIDE = "override"
S_EVENING = "evening"
S_SUN = "sun_protection"
S_VACATION = "vacation"
S_READY = "ready"
STATUSES = [S_OFF, S_STARTUP, S_OVERRIDE, S_EVENING, S_SUN, S_VACATION, S_READY]


@dataclass(frozen=True)
class Action:
    kind: str
    reason: str
    position: int | None = None


@dataclass(frozen=True)
class WindowRules:
    """The part of a window configuration the rules need."""

    sun_position: int = 10
    tolerance: int = 5
    auto_up: bool = True
    notify_open: bool = True
    manual_max_position: int = 25
    manual_at_sun_position: bool = False
    override_ignore_evening: bool = False
    evening_close: bool = True
    follow_up_close: bool = True
    ventilation: bool = True
    ventilation_position: int = 30
    closed_position: int = 5
    trigger_min_position: int = 20
    vacation: bool = True
    morning: bool = False
    morning_position: int = OPEN
    morning_sun_position: bool = True


@dataclass(frozen=True)
class Situation:
    """Snapshot of everything a rule may look at."""

    automatic: bool = True
    startup: bool = False
    position: int | None = None
    # open or unknown contact: blocks closing movements
    window_open: bool = False
    # a contact really reports "on" (None: same as window_open)
    window_on: bool | None = None
    window_exception: bool = False
    override: bool = False
    sun_marker: bool = False
    evening_marker: bool = False
    notified: bool = False
    live: bool = False
    no_temp: bool = False
    in_sector: bool = False
    past_sector_end: bool = False
    evening: bool = False
    open_blocked: bool = False
    vacation: bool = False

    @property
    def window_blocks(self) -> bool:
        """Open window that prevents closing movements (the exception entity lifts it)."""
        return self.window_open and not self.window_exception

    @property
    def window_reported_open(self) -> bool:
        """A contact really reports open (an unavailable contact only blocks)."""
        return self.window_open if self.window_on is None else self.window_on

    @property
    def active(self) -> bool:
        return self.automatic and not self.startup and self.position is not None


def _move(position: int, reason: str) -> Action:
    return Action(POSITION, reason, position)


def sun(rules: WindowRules, s: Situation) -> list[Action]:
    """Lower to the sun protection position, mark, notify, and open again later.

    Lowering: sun condition met (summer day, temperature, sensors, all held),
    sun in the sector, no override, not yet done today. A cover that is already
    further closed is only marked. An open window prevents the movement; a push
    message is sent once a day, only if a movement was really prevented.

    Auto up: the sun has left the sector, the window was protected today, the
    cover still stands at the sun protection position (up to the tolerance), no
    override, not in the evening and no opening block.
    """
    if not s.active or s.position is None:
        return []
    if s.live and s.in_sector and not s.override and not s.sun_marker:
        if s.position <= rules.sun_position:
            return [Action(MARK_SUN, R_SUN_ALREADY)]
        if not s.window_blocks:
            return [_move(rules.sun_position, R_SUN_LOWER), Action(MARK_SUN, R_SUN_LOWER)]
        if rules.notify_open and not s.notified and s.window_reported_open:
            return [Action(NOTIFY, R_SUN_BLOCKED)]
        return []
    if (
        rules.auto_up
        and s.sun_marker
        and s.past_sector_end
        and not s.override
        and not s.evening
        and not s.open_blocked
        and rules.sun_position <= s.position <= rules.sun_position + rules.tolerance
    ):
        return [_move(OPEN, R_AUTO_UP), Action(CLEAR_SUN, R_AUTO_UP)]
    return []


def manual_sun(rules: WindowRules, s: Situation, recent: bool) -> list[Action]:
    """A manual lowering during sun counts as sun protection for today.

    ``recent``: the override started or the cover moved within the detection window.
    The condition without temperature (``no_temp``) has a follow-up time.
    """
    if (
        s.active
        and recent
        and s.no_temp
        and s.override
        and not s.window_blocks
        and not s.sun_marker
        and s.position is not None
        and s.position <= rules.manual_max_position
    ):
        return [Action(MARK_SUN, R_SUN_MANUAL)]
    return []


def sun_position_reached(rules: WindowRules, s: Situation) -> list[Action]:
    """Option: a cover moved (by anyone) onto the sun protection position while the
    sun condition applies counts as sun protection (so it opens again later)."""
    if (
        rules.manual_at_sun_position
        and s.active
        and s.live
        and s.in_sector
        and not s.sun_marker
        and s.position is not None
        and rules.sun_position <= s.position <= rules.sun_position + rules.tolerance
    ):
        return [Action(MARK_SUN, R_SUN_POSITION_MANUAL)]
    return []


def _vacation_applies(rules: WindowRules, s: Situation) -> bool:
    return s.vacation and rules.vacation


def _override_blocks_evening(rules: WindowRules, s: Situation) -> bool:
    return s.override and not rules.override_ignore_evening


def evening(rules: WindowRules, s: Situation) -> list[Action]:
    """Evening run: close once per evening if the window is closed and no override
    (unless the window ignores overrides in the evening). Not during vacation."""
    if (
        not rules.evening_close
        or not s.active
        or not s.evening
        or _vacation_applies(rules, s)
        or s.evening_marker
        or s.window_blocks
        or _override_blocks_evening(rules, s)
    ):
        return []
    return [_move(CLOSED, R_EVENING), Action(MARK_EVENING, R_EVENING)]


def follow_up(rules: WindowRules, s: Situation, after_earliest: bool) -> list[Action]:
    """Window closed in the evening: close the cover (ignores overrides)."""
    if rules.follow_up_close and s.active and s.evening and after_earliest:
        return [_move(CLOSED, R_FOLLOW_UP), Action(MARK_EVENING, R_FOLLOW_UP)]
    return []


def ventilation(rules: WindowRules, s: Situation) -> list[Action]:
    """Window opened and cover (almost) closed: open to the ventilation position."""
    if (
        rules.ventilation
        and s.active
        and s.window_open
        and not s.open_blocked
        and s.position is not None
        and s.position <= rules.closed_position
    ):
        return [_move(rules.ventilation_position, R_VENTILATION)]
    return []


def trigger_close(rules: WindowRules, s: Situation) -> list[Action]:
    """Close trigger (e.g. TV switched on): close once per cycle if the cover is
    open more than the minimum position and the window is closed."""
    if (
        s.active
        and not s.window_blocks
        and s.position is not None
        and s.position > rules.trigger_min_position
    ):
        return [_move(CLOSED, R_TRIGGER)]
    return []


def vacation_open(rules: WindowRules, s: Situation, position: int) -> list[Action]:
    """Vacation morning: open covers that were closed for the night."""
    if not s.active or not _vacation_applies(rules, s) or _override_blocks_evening(rules, s):
        return []
    if s.open_blocked or s.position is None:
        return []
    if not (s.evening_marker or s.position <= rules.closed_position):
        return []
    return [_move(position, R_VACATION_OPEN), Action(CLEAR_EVENING, R_VACATION_OPEN)]


def vacation_close(rules: WindowRules, s: Situation) -> list[Action]:
    """Vacation evening: mark as closed for the night and close if the window is
    closed. Only the window sensor counts here (no exception entity)."""
    if (
        not s.active
        or s.position is None
        or not _vacation_applies(rules, s)
        or _override_blocks_evening(rules, s)
    ):
        return []
    actions = [Action(MARK_EVENING, R_VACATION_CLOSE)]
    if s.position > CLOSED and not s.window_open:
        actions.insert(0, _move(CLOSED, R_VACATION_CLOSE))
    return actions


def morning(rules: WindowRules, s: Situation, manual_since_evening: bool) -> list[Action]:
    """Morning opening. Not during vacation (the simulation opens), not with an
    override, an opening block or a cover moved by hand since the evening.
    Directly to the sun protection position if the sun condition applies."""
    if not rules.morning or not s.active or _vacation_applies(rules, s):
        return []
    if s.override or s.open_blocked or manual_since_evening or s.position is None:
        return []
    target, reason = rules.morning_position, R_MORNING
    sun_now = rules.morning_sun_position and s.live and s.in_sector
    if sun_now:
        target, reason = min(target, rules.sun_position), R_MORNING_SUN
    if s.position >= target:
        return []
    actions = [_move(target, reason), Action(CLEAR_EVENING, reason)]
    if sun_now:
        actions.append(Action(MARK_SUN, reason))
    return actions


def status(rules: WindowRules, s: Situation) -> str:
    if not s.automatic:
        return S_OFF
    if s.startup:
        return S_STARTUP
    if s.override:
        return S_OVERRIDE
    if s.evening_marker and s.evening:
        return S_EVENING
    if s.sun_marker:
        return S_SUN
    if _vacation_applies(rules, s):
        return S_VACATION
    return S_READY
