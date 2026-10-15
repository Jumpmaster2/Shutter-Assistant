"""Own commands and manual movements."""

from datetime import UTC, datetime, timedelta

from logic.override import CommandTracker, is_manual, override_until


def test_tracker_explains_reports_until_target_and_grace() -> None:
    tracker = CommandTracker(timeout=120, grace=15)
    tracker.register("cover.a", 10, "ctx1", 0)
    assert tracker.explains("cover.a", "ctx1", "closing", 100, 0.5)
    assert tracker.explains("cover.a", None, "closing", 60, 5)
    assert tracker.explains("cover.a", None, "open", 10, 20)  # reached target
    assert tracker.explains("cover.a", None, "open", 11, 30)  # late report within grace
    assert not tracker.explains("cover.a", None, "open", 50, 40)  # after grace: not ours
    assert not tracker.pending("cover.a")


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


def test_override_until() -> None:
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    sunrise = datetime(2026, 10, 16, 6, 0, tzinfo=UTC)
    assert override_until(now, 60, sunrise) == now + timedelta(minutes=60)
    assert override_until(now, 0, sunrise) == sunrise
