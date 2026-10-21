"""Own commands and manual movements."""

from datetime import UTC, datetime, timedelta

from logic.override import CommandTracker, MovementWatch, is_manual, override_until


def test_tracker_explains_reports_until_target_and_grace() -> None:
    tracker = CommandTracker(timeout=120, grace=15)
    tracker.register("cover.a", 10, "ctx1", 0)
    assert tracker.explains("cover.a", "ctx1", "closing", 100, 0.5)
    assert tracker.explains("cover.a", None, "closing", 60, 5)
    assert tracker.explains("cover.a", None, "open", 10, 20)  # reached target
    assert tracker.explains("cover.a", None, "open", 11, 30)  # late report within grace
    assert not tracker.explains("cover.a", None, "open", 50, 40)  # after grace: not ours


def test_tracker_times_out() -> None:
    tracker = CommandTracker(timeout=120, grace=15)
    tracker.register("cover.a", 0, "ctx1", 0)
    assert not tracker.explains("cover.a", None, "opening", 50, 200)


def test_tracker_ignores_other_covers() -> None:
    tracker = CommandTracker()
    tracker.register("cover.a", 0, "ctx1", 0)
    assert not tracker.explains("cover.b", None, "closing", 50, 1)


def test_is_manual() -> None:
    base = {"own": False, "parent_id": None, "old_position": 100, "new_position": 90}
    assert is_manual(old_state="open", new_state="closing", **base)
    # own command or other automation
    assert not is_manual(**{**base, "own": True}, old_state="open", new_state="closing")
    assert not is_manual(**{**base, "parent_id": "x"}, old_state="open", new_state="closing")
    # movement reports and coming back online
    assert not is_manual(old_state="closing", new_state="closing", **base)
    assert not is_manual(old_state="unavailable", new_state="open", **base)
    assert not is_manual(old_state="open", new_state="unknown", **base)
    assert not is_manual(old_state=None, new_state="open", **base)
    # nothing changed
    assert not is_manual(
        own=False,
        parent_id=None,
        old_state="open",
        new_state="open",
        old_position=50,
        new_position=50,
    )


def _report(watch: MovementWatch, old, new, now, *, started=None, own=False) -> bool:
    (old_state, old_pos), (new_state, new_pos) = old, new
    if started is None:
        started = is_manual(
            own=own,
            parent_id=None,
            old_state=old_state,
            new_state=new_state,
            old_position=old_pos,
            new_position=new_pos,
        )
    return watch.update(
        "cover.a",
        started=started,
        own=own,
        old_state=old_state,
        old_position=old_pos,
        new_state=new_state,
        new_position=new_pos,
        now=now,
    )


def test_movement_watch_ignores_commands_without_movement() -> None:
    watch = MovementWatch()
    # "open all" while the cover is open: opening and open again at 100
    assert not _report(watch, ("open", 100), ("opening", 100), 0)
    assert not _report(watch, ("opening", 100), ("open", 100), 2)
    # a position jitter within the tolerance is no movement either
    assert not _report(watch, ("open", 100), ("open", 99), 10)


def test_movement_watch_reports_a_real_movement() -> None:
    watch = MovementWatch()
    assert not _report(watch, ("open", 100), ("closing", 100), 0)
    assert not _report(watch, ("closing", 100), ("closing", 99), 1)
    assert _report(watch, ("closing", 99), ("closing", 90), 2)
    # only once per command
    assert not _report(watch, ("closing", 90), ("open", 60), 5)
    # a direct jump without a moving state
    assert _report(watch, ("open", 60), ("open", 40), 10)


def test_movement_watch_without_position_and_own_moves() -> None:
    watch = MovementWatch()
    assert not _report(watch, ("open", None), ("closing", None), 0)
    assert _report(watch, ("closing", None), ("closed", None), 20)
    assert not _report(watch, ("closed", None), ("opening", None), 30)
    assert not _report(watch, ("opening", None), ("closed", None), 40)
    # own movement or an unavailable cover forget the start
    assert not _report(watch, ("open", 100), ("closing", 100), 50)
    assert not _report(watch, ("closing", 100), ("closing", 50), 51, own=True)
    assert not _report(watch, ("closing", 50), ("closing", 20), 52)
    # a start older than the timeout is forgotten
    watch = MovementWatch(timeout=60)
    assert not _report(watch, ("open", 100), ("closing", 100), 0)
    assert not _report(watch, ("closing", 100), ("closing", 50), 100)


def test_override_until() -> None:
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    sunrise = datetime(2026, 10, 16, 6, 0, tzinfo=UTC)
    assert override_until(now, 60, sunrise) == now + timedelta(minutes=60)
    assert override_until(now, 0, sunrise) == sunrise
    # polar day or night: no sunrise
    assert override_until(now, 0, None) == now + timedelta(hours=24)


def test_reached() -> None:
    from logic.override import reached

    assert reached(10, 12, "open")
    assert not reached(10, 14, "open")
    # without a position only the end positions can be checked
    assert reached(100, None, "open")
    assert not reached(100, None, "closed")
    assert reached(0, None, "closed")
    assert reached(50, None, "open")
