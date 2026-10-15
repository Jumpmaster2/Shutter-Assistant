"""Window rules (one scenario per behaviour of the replaced automations)."""

from dataclasses import replace

from logic import window as w
from logic.window import Action, Situation, WindowRules

RULES = WindowRules(sun_position=10, tolerance=5)
SUNNY = Situation(position=100, live=True, in_sector=True, no_temp=True)


def kinds(actions: list[Action]) -> list[tuple[str, str, int | None]]:
    return [(a.kind, a.reason, a.position) for a in actions]


# ---------------------------------------------------------------- sun protection


def test_lowers_to_sun_position_and_marks() -> None:
    assert kinds(w.sun(RULES, SUNNY)) == [
        (w.POSITION, w.R_SUN_LOWER, 10),
        (w.MARK_SUN, w.R_SUN_LOWER, None),
    ]


def test_already_further_closed_is_only_marked() -> None:
    assert kinds(w.sun(RULES, replace(SUNNY, position=5))) == [(w.MARK_SUN, w.R_SUN_ALREADY, None)]
    assert kinds(w.sun(RULES, replace(SUNNY, position=10))) == [(w.MARK_SUN, w.R_SUN_ALREADY, None)]


def test_only_marked_even_with_open_window() -> None:
    s = replace(SUNNY, position=0, window_open=True)
    assert kinds(w.sun(RULES, s)) == [(w.MARK_SUN, w.R_SUN_ALREADY, None)]


def test_no_sun_protection_without_conditions() -> None:
    for s in (
        replace(SUNNY, live=False),
        replace(SUNNY, in_sector=False),
        replace(SUNNY, override=True),
        replace(SUNNY, sun_marker=True),
        replace(SUNNY, automatic=False),
        replace(SUNNY, startup=True),
        replace(SUNNY, position=None),
    ):
        assert w.sun(RULES, s) == []


def test_open_window_prevents_lowering_and_notifies_once() -> None:
    s = replace(SUNNY, window_open=True)
    assert kinds(w.sun(RULES, s)) == [(w.NOTIFY, w.R_SUN_BLOCKED, None)]
    assert w.sun(RULES, replace(s, notified=True)) == []
    assert w.sun(replace(RULES, notify_open=False), s) == []


def test_window_exception_lifts_open_window() -> None:
    s = replace(SUNNY, window_open=True, window_exception=True)
    assert kinds(w.sun(RULES, s))[0] == (w.POSITION, w.R_SUN_LOWER, 10)


def test_no_notification_if_nothing_to_do() -> None:
    # override active or already protected: no push (decision B7)
    assert w.sun(RULES, replace(SUNNY, window_open=True, override=True)) == []
    assert w.sun(RULES, replace(SUNNY, window_open=True, sun_marker=True)) == []


# ---------------------------------------------------------------- auto up

PROTECTED = Situation(position=10, sun_marker=True, past_sector_end=True)


def test_auto_up_when_sun_left_sector() -> None:
    assert kinds(w.sun(RULES, PROTECTED)) == [
        (w.POSITION, w.R_AUTO_UP, 100),
        (w.CLEAR_SUN, w.R_AUTO_UP, None),
    ]
    assert kinds(w.sun(RULES, replace(PROTECTED, position=15)))[0][1] == w.R_AUTO_UP


def test_auto_up_only_at_sun_position() -> None:
    assert w.sun(RULES, replace(PROTECTED, position=16)) == []
    assert w.sun(RULES, replace(PROTECTED, position=9)) == []


def test_auto_up_blockers() -> None:
    for s in (
        replace(PROTECTED, past_sector_end=False),
        replace(PROTECTED, override=True),
        replace(PROTECTED, evening=True),
        replace(PROTECTED, open_blocked=True),
        replace(PROTECTED, sun_marker=False),
    ):
        assert w.sun(RULES, s) == []
    assert w.sun(replace(RULES, auto_up=False), PROTECTED) == []


def test_auto_up_does_not_need_summer_day() -> None:
    # decision B13: only the marker counts (live is False here)
    assert w.sun(RULES, replace(PROTECTED, live=False))


# ---------------------------------------------------------------- manual detection


MANUAL = Situation(position=20, override=True, no_temp=True)


def test_manual_lowering_marks_sun_protection() -> None:
    assert kinds(w.manual_sun(RULES, MANUAL, recent=True)) == [(w.MARK_SUN, w.R_SUN_MANUAL, None)]


def test_manual_lowering_requirements() -> None:
    assert w.manual_sun(RULES, MANUAL, recent=False) == []
    assert w.manual_sun(RULES, replace(MANUAL, position=26), recent=True) == []
    assert w.manual_sun(RULES, replace(MANUAL, override=False), recent=True) == []
    assert w.manual_sun(RULES, replace(MANUAL, no_temp=False), recent=True) == []
    assert w.manual_sun(RULES, replace(MANUAL, window_open=True), recent=True) == []
    assert w.manual_sun(RULES, replace(MANUAL, sun_marker=True), recent=True) == []
    custom = replace(RULES, manual_max_position=30)
    assert w.manual_sun(custom, replace(MANUAL, position=30), recent=True)


def test_sun_position_reached_option() -> None:
    rules = replace(RULES, manual_at_sun_position=True)
    s = Situation(position=12, live=True, in_sector=True, override=True)
    assert kinds(w.sun_position_reached(rules, s)) == [(w.MARK_SUN, w.R_SUN_POSITION_MANUAL, None)]
    assert w.sun_position_reached(RULES, s) == []
    assert w.sun_position_reached(rules, replace(s, position=16)) == []
    assert w.sun_position_reached(rules, replace(s, live=False)) == []


# ---------------------------------------------------------------- evening

EVENING = Situation(position=100, evening=True)


def test_evening_run_closes_and_marks() -> None:
    assert kinds(w.evening(RULES, EVENING)) == [
        (w.POSITION, w.R_EVENING, 0),
        (w.MARK_EVENING, w.R_EVENING, None),
    ]


def test_evening_run_blockers() -> None:
    for s in (
        replace(EVENING, evening=False),
        replace(EVENING, evening_marker=True),
        replace(EVENING, window_open=True),
        replace(EVENING, override=True),
        replace(EVENING, vacation=True),
        replace(EVENING, startup=True),
    ):
        assert w.evening(RULES, s) == []
    assert w.evening(replace(RULES, evening_close=False), EVENING) == []


def test_evening_run_ignoring_override() -> None:
    rules = replace(RULES, override_ignore_evening=True)
    assert w.evening(rules, replace(EVENING, override=True))


def test_evening_run_with_window_exception() -> None:
    assert w.evening(RULES, replace(EVENING, window_open=True, window_exception=True))


def test_evening_run_for_window_not_in_vacation_simulation() -> None:
    assert w.evening(replace(RULES, vacation=False), replace(EVENING, vacation=True))


def test_follow_up_closes_in_the_evening_regardless_of_override() -> None:
    s = replace(EVENING, override=True, evening_marker=True)
    assert kinds(w.follow_up(RULES, s, after_earliest=True))[0] == (w.POSITION, w.R_FOLLOW_UP, 0)
    assert w.follow_up(RULES, s, after_earliest=False) == []
    assert w.follow_up(RULES, replace(s, evening=False), after_earliest=True) == []
    assert w.follow_up(replace(RULES, follow_up_close=False), s, after_earliest=True) == []


# ---------------------------------------------------------------- ventilation


def test_ventilation_position() -> None:
    s = Situation(position=0, window_open=True)
    assert kinds(w.ventilation(RULES, s)) == [(w.POSITION, w.R_VENTILATION, 30)]
    assert w.ventilation(RULES, replace(s, position=6)) == []
    assert w.ventilation(RULES, replace(s, window_open=False)) == []
    assert w.ventilation(RULES, replace(s, open_blocked=True)) == []
    # override does not matter (as before)
    assert w.ventilation(RULES, replace(s, override=True))


# ---------------------------------------------------------------- close trigger (TV)


def test_trigger_close() -> None:
    s = Situation(position=100)
    assert kinds(w.trigger_close(RULES, s)) == [(w.POSITION, w.R_TRIGGER, 0)]
    assert w.trigger_close(RULES, replace(s, position=20)) == []
    # decision B8: open window and startup block
    assert w.trigger_close(RULES, replace(s, window_open=True)) == []
    assert w.trigger_close(RULES, replace(s, startup=True)) == []
    # override and evening do not matter
    assert w.trigger_close(RULES, replace(s, override=True, evening=True))


# ---------------------------------------------------------------- vacation


def test_vacation_morning_opens_closed_covers() -> None:
    s = Situation(position=0, vacation=True)
    assert kinds(w.vacation_open(RULES, s, 73)) == [
        (w.POSITION, w.R_VACATION_OPEN, 73),
        (w.CLEAR_EVENING, w.R_VACATION_OPEN, None),
    ]
    assert w.vacation_open(RULES, replace(s, position=50), 73) == []
    assert w.vacation_open(RULES, replace(s, position=50, evening_marker=True), 73)
    assert w.vacation_open(RULES, replace(s, override=True), 73) == []
    assert w.vacation_open(
        replace(RULES, override_ignore_evening=True), replace(s, override=True), 73
    )
    assert w.vacation_open(RULES, replace(s, open_blocked=True), 73) == []
    assert w.vacation_open(replace(RULES, vacation=False), s, 73) == []
    assert w.vacation_open(RULES, replace(s, vacation=False), 73) == []


def test_vacation_evening() -> None:
    s = Situation(position=100, vacation=True)
    assert kinds(w.vacation_close(RULES, s)) == [
        (w.POSITION, w.R_VACATION_CLOSE, 0),
        (w.MARK_EVENING, w.R_VACATION_CLOSE, None),
    ]
    # open window: only marked, the follow-up closes later
    assert kinds(w.vacation_close(RULES, replace(s, window_open=True))) == [
        (w.MARK_EVENING, w.R_VACATION_CLOSE, None)
    ]
    # decision B10: the exception entity does not apply here
    assert kinds(w.vacation_close(RULES, replace(s, window_open=True, window_exception=True))) == [
        (w.MARK_EVENING, w.R_VACATION_CLOSE, None)
    ]
    assert w.vacation_close(RULES, replace(s, override=True)) == []


# ---------------------------------------------------------------- morning

MORNING_RULES = replace(RULES, morning=True)
MORNING = Situation(position=0, evening_marker=True)


def test_morning_opening() -> None:
    assert kinds(w.morning(MORNING_RULES, MORNING, manual_since_evening=False)) == [
        (w.POSITION, w.R_MORNING, 100),
        (w.CLEAR_EVENING, w.R_MORNING, None),
    ]
    partial = replace(MORNING_RULES, morning_position=60)
    assert kinds(w.morning(partial, MORNING, manual_since_evening=False))[0][2] == 60


def test_morning_opening_directly_to_sun_position() -> None:
    s = replace(MORNING, live=True, in_sector=True)
    assert kinds(w.morning(MORNING_RULES, s, manual_since_evening=False)) == [
        (w.POSITION, w.R_MORNING_SUN, 10),
        (w.CLEAR_EVENING, w.R_MORNING_SUN, None),
        (w.MARK_SUN, w.R_MORNING_SUN, None),
    ]


def test_morning_opening_blockers() -> None:
    assert w.morning(RULES, MORNING, manual_since_evening=False) == []
    assert w.morning(MORNING_RULES, MORNING, manual_since_evening=True) == []
    for s in (
        replace(MORNING, override=True),
        replace(MORNING, open_blocked=True),
        replace(MORNING, vacation=True),
        replace(MORNING, position=100),
    ):
        assert w.morning(MORNING_RULES, s, manual_since_evening=False) == []


# ---------------------------------------------------------------- status


def test_status_order() -> None:
    assert w.status(RULES, Situation(automatic=False, override=True)) == w.S_OFF
    assert w.status(RULES, Situation(startup=True)) == w.S_STARTUP
    assert w.status(RULES, Situation(override=True, sun_marker=True)) == w.S_OVERRIDE
    assert w.status(RULES, Situation(evening=True, evening_marker=True)) == w.S_EVENING
    assert w.status(RULES, Situation(sun_marker=True)) == w.S_SUN
    assert w.status(RULES, Situation(vacation=True)) == w.S_VACATION
    assert w.status(RULES, Situation()) == w.S_READY


def test_no_notification_for_an_unavailable_contact() -> None:
    # an unavailable contact blocks the movement but is not reported as open
    s = replace(SUNNY, window_open=True, window_on=False)
    assert w.sun(RULES, s) == []
    assert kinds(w.sun(RULES, replace(s, window_on=True))) == [(w.NOTIFY, w.R_SUN_BLOCKED, None)]
