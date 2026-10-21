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


def summer_day(
    forecast_max: float | None,
    threshold: float,
    raised_today: bool,
    night_low: float | None = None,
    night_threshold: float | None = None,
) -> bool:
    """Summer day: forecast high reaches the threshold, or the outdoor temperature
    exceeded it today.

    A summer day only by the outdoor temperature (forecast below the threshold)
    also needs a warm night: when the forecast low of the coming night is below
    ``night_threshold``, the house cools down again and a warm afternoon alone is
    no reason for sun protection. Without a forecast low it counts as before.
    """
    if forecast_max is not None and forecast_max >= threshold:
        return True
    if not raised_today:
        return False
    return night_threshold is None or night_low is None or night_low >= night_threshold


def room_warm(
    current: float | None,
    setpoint: float | None,
    margin: float,
    threshold: float,
) -> bool | None:
    """Is the room too warm? None if the room temperature is unknown.

    With a setpoint (thermostat) the room is too warm from setpoint + margin on,
    otherwise from the fixed threshold.
    """
    if current is None:
        return None
    limit = setpoint + margin if setpoint is not None else threshold
    return current >= limit


def cooling_active(
    hvac_mode: str | None,
    hvac_action: str | None,
    current: float | None = None,
    target: float | None = None,
) -> bool:
    """Is an air conditioner cooling?

    It cools while its action is ``cooling``. In the mode ``cool`` it also counts
    while idle (it holds the room cool) and when it reports no action.

    Many air conditioners (e.g. Midea) report no action at all. In the mode
    ``auto`` or ``heat_cool`` it then counts as cooling while the room is warmer
    than its target.
    """
    if hvac_action == "cooling":
        return True
    if hvac_mode == "cool":
        return hvac_action in (None, "idle")
    return (
        hvac_mode in ("auto", "heat_cool")
        and hvac_action is None
        and current is not None
        and target is not None
        and current > target
    )


def heat_need(room: bool | None, cooling: bool, heating_day: bool) -> bool:
    """Is there a reason to keep the heat of the sun out of the room?

    ``room``: the room is too warm (None: no room entity or unknown value). A
    cooling air conditioner counts as a warm room (sun protection saves cooling
    energy). Without a room value it counts as warm (as before), except on a
    heating day: then the warmth of the sun is welcome.
    """
    if cooling or room is True:
        return True
    if room is False:
        return False
    return not heating_day


CONTACT_OPEN = "open"
CONTACT_TILTED = "tilted"
CONTACT_CLOSED = "closed"
_OPEN_STATES = ("on", "open", "opened")
_TILTED_STATES = ("tilted", "tilt")
_CLOSED_STATES = ("off", "closed", "close")


def contact(state: str | None, tilt_sensor: bool = False) -> str:
    """State of one contact: binary (on = open, or tilted for a tilt contact) or a
    window handle with the states open, tilted and closed.

    An unknown state is not safe: a window contact then counts as open, a tilt
    contact as tilted.
    """
    if state in _CLOSED_STATES:
        return CONTACT_CLOSED
    if state in _TILTED_STATES:
        return CONTACT_TILTED
    if state in _OPEN_STATES:
        return CONTACT_TILTED if tilt_sensor else CONTACT_OPEN
    return CONTACT_TILTED if tilt_sensor else CONTACT_OPEN


def window_contact(states: Iterable[str | None], tilt_states: Iterable[str | None] = ()) -> str:
    """Open if any contact is open, else tilted if any is tilted, else closed."""
    found = {contact(s) for s in states} | {contact(s, True) for s in tilt_states}
    for result in (CONTACT_OPEN, CONTACT_TILTED):
        if result in found:
            return result
    return CONTACT_CLOSED


def reported_open(states: Iterable[str | None]) -> bool:
    """A contact really reports open (an unavailable contact only blocks)."""
    return any(s in _OPEN_STATES for s in states)
