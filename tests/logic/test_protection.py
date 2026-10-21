"""Weather protection: on at once, off after the release time, invalid keeps the state."""

from logic.protection import Guard, above, freezing, raining


def test_on_immediately_off_after_release() -> None:
    guard = Guard(release=600)
    assert guard.update(True, 0)
    assert guard.active
    # below the threshold: still active until the release time
    assert not guard.update(False, 10)
    assert guard.due() == 610
    assert not guard.update(False, 300)
    assert guard.update(False, 610)
    assert not guard.active
    assert guard.due() is None


def test_back_over_the_threshold_restarts_the_release() -> None:
    guard = Guard(release=600)
    guard.update(True, 0)
    guard.update(False, 10)
    assert not guard.update(True, 100)
    assert guard.due() is None
    guard.update(False, 200)
    assert guard.due() == 800


def test_invalid_value_never_ends_a_protection() -> None:
    guard = Guard(release=600)
    guard.update(True, 0)
    guard.update(False, 10)
    assert not guard.update(None, 700)
    assert guard.active
    # no stale release time is left (it would fire right away)
    assert guard.due() is None
    assert not guard.update(None, 10_000)
    assert guard.active
    guard.update(False, 10_000)
    assert guard.due() == 10_600


def test_invalid_value_does_not_start_a_protection() -> None:
    guard = Guard(release=600)
    assert not guard.update(None, 0)
    assert not guard.active


def test_values() -> None:
    assert above("60.5", 50) is True
    assert above("50", 50) is False
    assert above("unavailable", 50) is None
    assert raining("on", 0) is True
    assert raining("off", 0) is False
    assert raining("0.0", 0) is False
    assert raining("0.4", 0) is True
    assert raining("unknown", 0) is None
    assert freezing(0.5, 1) is True
    assert freezing(1, 1) is True
    assert freezing(3, 1) is False
    assert freezing(None, 1) is None
