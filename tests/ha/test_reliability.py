"""Command spacing, the position check with one repetition, and the events."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from .conftest import COVER, advance, make_entry, set_cover, setup_entry

SECOND = "cover.bedroom"


BEDROOM = {"window_bed": {"name": "Bedroom", "cover": SECOND, "window_sensors": []}}


async def test_commands_are_spaced(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    hass.states.async_set(SECOND, "open", {"current_position": 100, "supported_features": 15})
    moved = []
    hass.bus.async_listen("shutter_assistant_cover_moved", moved.append)
    await setup_entry(hass, make_entry(extra_windows=BEDROOM, command_interval=5))
    await advance(hass, freezer, 10 * 60 + 1)
    # evening at 17:00: the first cover at once, the second after the spacing
    assert len(calls["close_cover"]) == 1
    await advance(hass, freezer, 5, step=1)
    assert len(calls["close_cover"]) == 2
    assert {c.data["entity_id"] for c in calls["close_cover"]} == {COVER, SECOND}
    assert [e.data["reason"] for e in moved] == ["evening_close", "evening_close"]
    assert moved[0].data["position"] == 0


async def test_command_repeated_once_then_reported(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    failed = []
    hass.bus.async_listen("shutter_assistant_cover_failed", failed.append)
    await setup_entry(hass, make_entry(verify_after=90))
    await advance(hass, freezer, 10 * 60 + 1)
    assert len(calls["close_cover"]) == 1
    # the (mocked) cover does not move: repeated after 90 s
    await advance(hass, freezer, 90, step=10)
    assert len(calls["close_cover"]) == 2
    assert failed == []
    await advance(hass, freezer, 90, step=10)
    assert len(calls["close_cover"]) == 2
    assert len(failed) == 1
    assert failed[0].data["position"] == 0
    assert len(calls["notify"]) == 1
    reason = hass.states.get("sensor.living_room_last_reason")
    assert reason.attributes["code"] == "cover_failed"


async def test_reached_target_is_not_repeated(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    await setup_entry(hass, make_entry(verify_after=90))
    await advance(hass, freezer, 10 * 60 + 1)
    assert len(calls["close_cover"]) == 1
    set_cover(hass, 1)
    await hass.async_block_till_done()
    await advance(hass, freezer, 4 * 60, step=10)
    assert len(calls["close_cover"]) == 1
    assert calls["notify"] == []
