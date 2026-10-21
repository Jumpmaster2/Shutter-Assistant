"""Services, the switches per window and the next action sensor."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from .conftest import COVER, OUTDOOR, advance, make_entry, set_cover, setup_entry

DOMAIN = "shutter_assistant"
OVERRIDE = "binary_sensor.living_room_manual_override"
EVENING_CLOSED = "binary_sensor.living_room_closed_this_evening"
WINDOW_AUTOMATIC = "switch.living_room_automatic"
WINDOW_SUN = "switch.living_room_sun_protection"
NEXT = "sensor.living_room_next_action"
STATUS = "sensor.living_room_status"


async def test_move_service_starts_no_override(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    await setup_entry(hass, make_entry())
    await hass.services.async_call(
        DOMAIN, "move", {"entity_id": [COVER], "action": "position", "position": 40}, blocking=True
    )
    assert [c.data["position"] for c in calls["set_cover_position"]] == [40]
    set_cover(hass, 100, state="closing")
    set_cover(hass, 40)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "off"
    reason = hass.states.get("sensor.living_room_last_reason")
    assert reason.attributes["code"] == "service"


async def test_move_evening_is_remembered(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:30:00+01:00")
    await setup_entry(hass, make_entry(window={"evening_position": 20}))
    # no covers: all windows
    await hass.services.async_call(DOMAIN, "move", {"action": "evening"}, blocking=True)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [20]
    set_cover(hass, 20)
    await advance(hass, freezer, 40 * 60)
    # the evening run does not close a second time
    assert calls["close_cover"] == []
    assert hass.states.get(EVENING_CLOSED).state == "on"


async def test_move_service_errors(hass: HomeAssistant, base_states, calls) -> None:
    await setup_entry(hass, make_entry())
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "move", {"entity_id": ["cover.unknown"], "action": "open"}, blocking=True
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "move", {"entity_id": [COVER], "action": "position"}, blocking=True
        )


async def test_override_services_and_resume(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:30:00+01:00")
    await setup_entry(hass, make_entry())
    await hass.services.async_call(
        DOMAIN, "start_override", {"entity_id": [COVER], "duration": 120}, blocking=True
    )
    assert hass.states.get(OVERRIDE).state == "on"
    until = dt_util.parse_datetime(hass.states.get(OVERRIDE).attributes["until"])
    assert until == dt_util.now() + timedelta(minutes=120)
    # evening run skipped during the override
    await advance(hass, freezer, 40 * 60)
    assert calls["close_cover"] == []
    # resume: the override ends and the evening run is caught up right away
    await hass.services.async_call(DOMAIN, "resume", {"entity_id": [COVER]}, blocking=True)
    assert hass.states.get(OVERRIDE).state == "off"
    assert len(calls["close_cover"]) == 1


async def test_end_override_service(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    await setup_entry(hass, make_entry())
    await hass.services.async_call(DOMAIN, "start_override", {}, blocking=True)
    assert hass.states.get(OVERRIDE).state == "on"
    await hass.services.async_call(DOMAIN, "end_override", {"entity_id": [STATUS]}, blocking=True)
    assert hass.states.get(OVERRIDE).state == "off"


async def test_window_automatic_switch(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    await setup_entry(hass, make_entry())
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": WINDOW_AUTOMATIC}, blocking=True
    )
    assert hass.states.get(WINDOW_AUTOMATIC).state == "off"
    assert hass.states.get(STATUS).state == "off"
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == []
    # the main switch stays on
    assert hass.states.get("switch.shutter_assistant_automatic").state == "on"


async def test_window_sun_switch(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-07-01 12:00:00+02:00")
    await setup_entry(hass, make_entry())
    await hass.services.async_call("switch", "turn_off", {"entity_id": WINDOW_SUN}, blocking=True)
    hass.states.async_set(OUTDOOR, "25.0")
    await hass.async_block_till_done()
    await advance(hass, freezer, 20 * 60)
    assert calls["set_cover_position"] == []
    await hass.services.async_call("switch", "turn_on", {"entity_id": WINDOW_SUN}, blocking=True)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_next_action(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 15:00:00+01:00")
    await setup_entry(hass, make_entry())
    state = hass.states.get(NEXT)
    assert state.attributes["action"] == "evening"
    assert dt_util.parse_datetime(state.state) == dt_util.parse_datetime(
        "2026-12-15 17:00:00+01:00"
    )
    await hass.services.async_call(
        DOMAIN, "start_override", {"entity_id": [COVER], "duration": 30}, blocking=True
    )
    state = hass.states.get(NEXT)
    assert state.attributes["action"] == "override_end"
    assert dt_util.parse_datetime(state.state) == dt_util.parse_datetime(
        "2026-12-15 15:30:00+01:00"
    )
