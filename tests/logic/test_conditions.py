"""Hold times, follow-up and sensor thresholds."""

from logic.conditions import (
    FollowUp,
    Hold,
    as_float,
    at_least,
    cooling_active,
    heat_need,
    room_warm,
    sensors_ok,
    summer_day,
)


def test_hold_turns_on_after_hold_and_off_immediately() -> None:
    hold = Hold(300)
    hold.update(True, 0)
    assert not hold.state(299)
    assert hold.due(10) == 300
    assert hold.state(300)
    assert hold.due(300) is None
    hold.update(True, 400)  # still true: keeps the original start
    assert hold.state(400)
    hold.update(False, 401)
    assert not hold.state(401)
    assert hold.due(401) is None


def test_hold_starts_again_after_interruption() -> None:
    hold = Hold(600)
    hold.update(True, 0)
    hold.update(False, 100)
    hold.update(True, 200)
    assert not hold.state(700)
    assert hold.state(800)


def test_hold_zero_is_immediate() -> None:
    hold = Hold(0)
    hold.update(True, 5)
    assert hold.state(5)


def test_follow_up() -> None:
    follow = FollowUp(300)
    assert not follow.state(0)
    follow.update(True, 0)
    assert follow.state(0)
    follow.update(False, 100)
    assert follow.state(399)
    assert follow.due(150) == 400
    assert not follow.state(400)
    follow.update(True, 500)
    assert follow.state(500)


def test_follow_up_false_without_prior_true_stays_off() -> None:
    follow = FollowUp(300)
    follow.update(False, 10)
    assert not follow.state(10)
    assert follow.due(10) is None


def test_numbers() -> None:
    assert as_float("12.5") == 12.5
    assert as_float("unavailable") is None
    assert as_float(None) is None
    assert as_float("nan") is None
    assert at_least("150", 150)
    assert not at_least("149.9", 150)
    assert not at_least("unknown", 0)


def test_sensors_ok_requires_every_sensor() -> None:
    thresholds = {"radiation": 150, "pv": 130, "lux": 14500}
    assert sensors_ok({"radiation": ["200"], "pv": ["131"]}, thresholds)
    assert not sensors_ok({"radiation": ["200"], "pv": ["129"]}, thresholds)
    assert not sensors_ok({"pv": ["200", "unavailable"]}, thresholds)
    assert sensors_ok({"lux": ["14500"]}, thresholds)
    # no sensors at all: only azimuth and temperature decide
    assert sensors_ok({}, thresholds)
    # a type without threshold never passes
    assert not sensors_ok({"pv": ["500"]}, {})


def test_summer_day() -> None:
    assert summer_day(23.0, 23.0, False)
    assert not summer_day(22.9, 23.0, False)
    assert summer_day(18.0, 23.0, True)
    assert not summer_day(None, 23.0, False)


def test_late_summer_day_needs_a_warm_night() -> None:
    # by the forecast: the night does not matter
    assert summer_day(25.0, 23.0, False, 8.0, 14.0)
    # only by the outdoor temperature: the night decides
    assert not summer_day(19.4, 23.0, True, 9.0, 14.0)
    assert summer_day(19.4, 23.0, True, 14.0, 14.0)
    # unknown low or no threshold: as before
    assert summer_day(19.4, 23.0, True, None, 14.0)
    assert summer_day(19.4, 23.0, True, 9.0, None)
    assert summer_day(None, 23.0, True, 9.0, None)
    assert not summer_day(19.4, 23.0, False, 20.0, 14.0)


def test_room_warm() -> None:
    assert room_warm(23.0, 21.0, 2.0, 24.0)
    assert not room_warm(22.9, 21.0, 2.0, 24.0)
    # without a setpoint the fixed threshold counts
    assert room_warm(24.0, None, 2.0, 24.0)
    assert not room_warm(23.9, None, 2.0, 24.0)
    assert room_warm(None, 21.0, 2.0, 24.0) is None


def test_cooling_active() -> None:
    assert cooling_active("cool", "cooling")
    assert cooling_active("cool", "idle")
    assert cooling_active("cool", None)
    assert cooling_active("auto", "cooling")
    assert cooling_active("heat_cool", "cooling")
    assert not cooling_active("auto", "idle")
    assert not cooling_active("cool", "off")
    assert not cooling_active("off", None)
    assert not cooling_active("heat", "heating")
    assert not cooling_active(None, None)


def test_heat_need() -> None:
    # no room entity: as before, except on a heating day
    assert heat_need(None, False, False)
    assert not heat_need(None, False, True)
    # the room decides
    assert heat_need(True, False, True)
    assert not heat_need(False, False, False)
    # a cooling air conditioner counts as a warm room
    assert heat_need(False, True, True)
