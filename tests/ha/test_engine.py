"""Scenarios of the engine with a Home Assistant test instance."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, CoreState, HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.shutter_assistant.logic import sun as sunlib

from .conftest import (
    CONTACT,
    COVER,
    OUTDOOR,
    PV,
    SUMMER_NOON,
    TV,
    VACATION,
    WINDOW_ID,
    advance,
    make_entry,
    set_cover,
    setup_entry,
)

SUN_TODAY = "binary_sensor.living_room_sun_protection_today"
OVERRIDE = "binary_sensor.living_room_manual_override"
STATUS = "sensor.living_room_status"
EVENING_CLOSED = "binary_sensor.living_room_closed_this_evening"
SUMMER = "binary_sensor.shutter_assistant_summer_day"


async def _summer_noon(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **kwargs) -> None:
    freezer.move_to(SUMMER_NOON)
    await setup_entry(hass, make_entry(**kwargs))
    # outdoor temperature rises above the summer threshold: summer day
    hass.states.async_set(OUTDOOR, "25.0")
    await hass.async_block_till_done()


async def test_sun_protection_after_hold_times(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    assert hass.states.get(SUMMER).state == "on"
    # 10 min temperature hold, then 5 min sun hold
    await advance(hass, freezer, 14 * 60)
    assert calls["set_cover_position"] == []
    await advance(hass, freezer, 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]
    assert hass.states.get(SUN_TODAY).state == "on"
    assert hass.states.get(STATUS).state == "sun_protection"
    # only once a day
    set_cover(hass, 100)
    await advance(hass, freezer, 30 * 60)
    assert len(calls["set_cover_position"]) == 1


async def test_sun_condition_ends_immediately(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 14 * 60)
    hass.states.async_set(PV, "100")  # below 130 W
    await hass.async_block_till_done()
    await advance(hass, freezer, 5 * 60)
    assert calls["set_cover_position"] == []
    hass.states.async_set(PV, "300")
    await hass.async_block_till_done()
    await advance(hass, freezer, 4 * 60)
    assert calls["set_cover_position"] == []
    await advance(hass, freezer, 60)
    assert len(calls["set_cover_position"]) == 1


async def test_already_closed_cover_is_only_marked(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    set_cover(hass, 5)
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    assert calls["set_cover_position"] == []
    assert hass.states.get(SUN_TODAY).state == "on"


async def test_open_window_notifies_once_and_lowers_after_closing(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(CONTACT, "on")
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    assert calls["set_cover_position"] == []
    assert len(calls["notify"]) == 1
    assert "Living room" in calls["notify"][0].data["message"]
    await advance(hass, freezer, 30 * 60)
    assert len(calls["notify"]) == 1
    # window closed: lowered after the debounce
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 6, step=1)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_no_notification_when_disabled(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(CONTACT, "on")
    await _summer_noon(hass, freezer, window={"notify_open_window": False})
    await advance(hass, freezer, 15 * 60)
    assert calls["notify"] == []


async def test_auto_up_when_sun_leaves_sector(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    set_cover(hass, 10)  # the cover reached the sun protection position
    await hass.async_block_till_done()
    engine = hass.config_entries.async_entries("shutter_assistant")[0].runtime_data
    exit_time = sunlib.next_azimuth_crossing(engine.observer, dt_util.now(), 270.0)
    assert exit_time is not None
    freezer.move_to(exit_time - timedelta(minutes=1))
    await advance(hass, freezer, 3 * 60)
    assert len(calls["open_cover"]) == 1
    assert hass.states.get(SUN_TODAY).state == "off"


async def test_auto_up_waits_for_the_override(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    set_cover(hass, 10)
    await hass.async_block_till_done()
    engine = hass.config_entries.async_entries("shutter_assistant")[0].runtime_data
    exit_time = sunlib.next_azimuth_crossing(engine.observer, dt_util.now(), 270.0)
    freezer.move_to(exit_time - timedelta(minutes=30))
    await advance(hass, freezer, 60)
    # manual movement and back to the sun position: override for 60 min
    set_cover(hass, 10, state="opening")
    set_cover(hass, 20)
    await hass.async_block_till_done()
    set_cover(hass, 10, state="closing")
    set_cover(hass, 10)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"
    await advance(hass, freezer, 40 * 60)
    assert calls["open_cover"] == []
    await advance(hass, freezer, 25 * 60)
    assert len(calls["open_cover"]) == 1


async def test_manual_movement_is_detected_but_own_is_not(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    assert len(calls["set_cover_position"]) == 1
    # report of our own movement (no context) arrives later
    set_cover(hass, 100, state="closing")
    set_cover(hass, 10)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "off"
    # another automation moves it: not manual (as before)
    await advance(hass, freezer, 60)
    set_cover(hass, 10, state="opening", context=Context(parent_id="automation"))
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "off"
    set_cover(hass, 50)
    await hass.async_block_till_done()
    # a real manual movement from standstill (counts once the position changes)
    set_cover(hass, 50, state="closing")
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "off"
    set_cover(hass, 40, state="closing")
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"
    assert hass.states.get(STATUS).state == "override"
    await advance(hass, freezer, 61 * 60)
    assert hass.states.get(OVERRIDE).state == "off"


async def test_command_without_movement_starts_no_override(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 10:00:00+02:00")
    await setup_entry(hass, make_entry())
    # "open all covers" while it is open: opening and open again without moving
    set_cover(hass, 100, state="opening", context=Context(user_id="voice"))
    set_cover(hass, 100, context=Context(user_id="voice"))
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "off"
    # a command that really moves the cover
    set_cover(hass, 100, state="closing")
    set_cover(hass, 70, state="closing")
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"


async def test_every_command_starts_an_override_when_chosen(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 10:00:00+02:00")
    await setup_entry(hass, make_entry(override_trigger="command"))
    set_cover(hass, 100, state="opening", context=Context(user_id="voice"))
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"


async def test_evening_run_and_follow_up(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-07-01 20:50:00+02:00")
    hass.states.async_set(CONTACT, "on")
    await setup_entry(hass, make_entry())
    await advance(hass, freezer, 11 * 60)  # evening at 21:00 (latest time)
    assert hass.states.get("binary_sensor.shutter_assistant_evening_mode").state == "on"
    assert calls["close_cover"] == []  # window open
    # ventilation: window opened while the cover is closed
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 6, step=1)
    assert len(calls["close_cover"]) == 1  # follow-up after closing the window
    assert hass.states.get(EVENING_CLOSED).state == "on"
    set_cover(hass, 0)
    hass.states.async_set(CONTACT, "on")
    await hass.async_block_till_done()
    await advance(hass, freezer, 4, step=1)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [30]
    # the night ends at 03:30
    freezer.move_to("2026-07-02 03:31:00+02:00")
    await advance(hass, freezer, 60)
    assert hass.states.get(EVENING_CLOSED).state == "off"


async def test_evening_run_at_the_earliest_time(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:55:00+01:00")
    await setup_entry(hass, make_entry())
    await advance(
        hass, freezer, 10 * 60
    )  # December: sun below -4 degrees before 17:00, evening at 17:00 (earliest)
    assert len(calls["close_cover"]) == 1


async def test_evening_run_skipped_with_override_unless_ignored(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    await setup_entry(hass, make_entry())
    set_cover(hass, 100, state="closing")
    set_cover(hass, 80)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == []


async def test_evening_run_ignoring_override(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    await setup_entry(hass, make_entry(window={"override_ignore_evening": True}))
    set_cover(hass, 100, state="closing")
    set_cover(hass, 80)
    await hass.async_block_till_done()
    await advance(hass, freezer, 15 * 60)
    assert len(calls["close_cover"]) == 1


async def test_close_trigger_waits_for_the_window(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    await setup_entry(
        hass,
        make_entry(
            window={
                "close_trigger_entities": [TV],
                "close_trigger_active_states": ["idle", "paused", "playing"],
                "open_block_entity": TV,
            }
        ),
    )
    hass.states.async_set(CONTACT, "on")
    hass.states.async_set(TV, "playing")
    await hass.async_block_till_done()
    await advance(hass, freezer, 10, step=1)
    assert calls["close_cover"] == []
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 6, step=1)
    assert len(calls["close_cover"]) == 1
    # only once per cycle
    set_cover(hass, 100)
    hass.states.async_set(TV, "paused")
    await hass.async_block_till_done()
    await advance(hass, freezer, 20, step=1)
    assert len(calls["close_cover"]) == 1
    # off for 15 s ends the cycle, the next one closes again
    hass.states.async_set(TV, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 16, step=1)
    hass.states.async_set(TV, "playing")
    await hass.async_block_till_done()
    await advance(hass, freezer, 9, step=1)
    assert len(calls["close_cover"]) == 2


async def test_open_block_prevents_ventilation(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    set_cover(hass, 0)
    await setup_entry(hass, make_entry(window={"open_block_entity": TV}))
    hass.states.async_set(TV, "playing")
    hass.states.async_set(CONTACT, "on")
    await hass.async_block_till_done()
    await advance(hass, freezer, 70, step=10)
    assert calls["set_cover_position"] == []
    hass.states.async_set(TV, "standby")  # standby counts as off
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 10, step=1)
    hass.states.async_set(CONTACT, "on")
    await hass.async_block_till_done()
    await advance(hass, freezer, 70, step=10)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [30]


async def test_vacation_runs(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 18:59:00+02:00")
    hass.states.async_set(VACATION, "on")
    await setup_entry(
        hass,
        make_entry(
            vacation_evening_window=0,
            vacation_morning_window=0,
            vacation_position_min=80,
            vacation_position_max=80,
        ),
    )
    # the regular evening run (17:00) rests during vacation
    assert calls["close_cover"] == []
    await advance(hass, freezer, 2 * 60)
    assert len(calls["close_cover"]) == 1
    assert hass.states.get(STATUS).state == "evening"
    set_cover(hass, 0)
    freezer.move_to("2026-10-16 06:59:00+02:00")
    await advance(hass, freezer, 2 * 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [80]


async def test_restart_keeps_override_and_markers(
    hass: HomeAssistant, base_states, calls, hass_storage, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 20:00:00+02:00")
    entry = make_entry()
    until = (dt_util.utcnow() + timedelta(minutes=30)).isoformat()
    hass_storage[f"shutter_assistant.{entry.entry_id}"] = {
        "version": 1,
        "key": f"shutter_assistant.{entry.entry_id}",
        "data": {
            "automatic": True,
            "windows": {WINDOW_ID: {"override_until": until, "evening_day": "2026-10-15"}},
        },
    }
    await setup_entry(hass, entry)
    assert hass.states.get(OVERRIDE).state == "on"
    assert hass.states.get(EVENING_CLOSED).state == "on"
    await advance(hass, freezer, 31 * 60)
    assert hass.states.get(OVERRIDE).state == "off"
    assert calls["close_cover"] == []  # already closed this evening


async def test_restart_protection_and_catch_up(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 20:00:00+02:00")
    hass.set_state(CoreState.starting)
    await setup_entry(hass, make_entry())
    assert hass.states.get(STATUS).state == "startup"
    await advance(hass, freezer, 4 * 60)
    assert calls["close_cover"] == []
    await advance(hass, freezer, 2 * 60)
    assert len(calls["close_cover"]) == 1


async def test_automatic_switch_is_kept(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    entry = make_entry()
    await setup_entry(hass, entry)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.shutter_assistant_automatic"}, blocking=True
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("switch.shutter_assistant_automatic").state == "off"
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == []
    assert hass.states.get(STATUS).state == "off"


async def test_no_evaluation_without_state_change(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    engine = hass.config_entries.async_entries("shutter_assistant")[0].runtime_data
    with patch.object(engine, "_evaluate", wraps=engine._evaluate) as evaluate:
        for value in ("510", "520", "530"):
            hass.states.async_set(PV, value)
            await hass.async_block_till_done()
        assert evaluate.call_count == 0
    timers = sorted(engine._timers)
    assert all(not key.endswith(":poll") for key in timers)


async def test_morning_opening_by_time(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 05:00:00+02:00")  # Thursday
    set_cover(hass, 0)
    await setup_entry(
        hass,
        make_entry(
            window={
                "morning_enabled": True,
                "morning_mode": "time",
                "morning_time_workday": "06:30:00",
            }
        ),
    )
    await advance(hass, freezer, 89 * 60, step=300)
    assert calls["open_cover"] == []
    await advance(hass, freezer, 2 * 60)
    assert len(calls["open_cover"]) == 1


async def test_morning_opening_skipped_after_manual_change(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 05:00:00+02:00")
    set_cover(hass, 0)
    entry = make_entry(window={"morning_enabled": True, "morning_time_workday": "06:30:00"})
    await setup_entry(hass, entry)
    engine = entry.runtime_data
    engine.windows[WINDOW_ID].last_manual = datetime.fromisoformat("2026-10-14T22:00:00+02:00")
    await advance(hass, freezer, 95 * 60, step=300)
    assert calls["open_cover"] == []


async def test_evening_starts_with_the_sun_in_october(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 18:00:00+02:00")
    entry = make_entry()
    await setup_entry(hass, entry)
    engine = entry.runtime_data
    start, _end = engine._evening_window(engine.global_evening, dt_util.now().date())
    local = dt_util.as_local(start)
    assert (local.hour, local.minute) >= (18, 30) and local.hour < 19
    await advance(hass, freezer, (start - dt_util.now()).total_seconds() - 60)
    assert calls["close_cover"] == []
    await advance(hass, freezer, 120)
    assert len(calls["close_cover"]) == 1


async def test_manual_lowering_counts_as_sun_protection(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 60)
    set_cover(hass, 100, state="closing")
    set_cover(hass, 20)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"
    assert hass.states.get(SUN_TODAY).state == "on"
    await advance(hass, freezer, 20 * 60)
    assert calls["set_cover_position"] == []


async def test_window_exception_allows_lowering(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(CONTACT, "on")
    hass.states.async_set("climate.ac", "cool")
    await _summer_noon(hass, freezer, window={"window_exception_entity": "climate.ac"})
    await advance(hass, freezer, 15 * 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]
    assert calls["notify"] == []


async def test_moving_onto_sun_position_counts(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(CONTACT, "on")
    await _summer_noon(hass, freezer, window={"manual_at_sun_position": True})
    await advance(hass, freezer, 15 * 60)
    assert hass.states.get(SUN_TODAY).state == "off"
    set_cover(hass, 100, state="closing")
    set_cover(hass, 12)
    await hass.async_block_till_done()
    assert hass.states.get(SUN_TODAY).state == "on"


async def test_morning_opening_by_brightness(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 05:00:00+02:00")
    set_cover(hass, 0)
    hass.states.async_set("sensor.lux", "50")
    group = {
        "name": "South",
        "azimuth_from": 90,
        "azimuth_to": 270,
        "lux_sensors": ["sensor.lux"],
        "pv_sensors": [],
        "radiation_sensors": [],
    }
    window = {
        "morning_enabled": True,
        "morning_mode": "brightness",
        "morning_lux_threshold": 1000,
        "morning_lux_hold": 5,
        "morning_earliest": "06:00:00",
        "morning_latest": "09:00:00",
    }
    await setup_entry(hass, make_entry(window=window, group=group))
    hass.states.async_set("sensor.lux", "2000")  # bright before the earliest time
    await hass.async_block_till_done()
    await advance(hass, freezer, 55 * 60, step=300)
    assert calls["open_cover"] == []
    await advance(hass, freezer, 6 * 60)
    assert len(calls["open_cover"]) == 1


async def test_forecast_failure_keeps_last_value_and_retries(
    hass: HomeAssistant, base_states, calls, hass_storage, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(SUMMER_NOON)
    entry = make_entry(weather="weather.home")
    hass_storage[f"shutter_assistant.{entry.entry_id}"] = {
        "version": 1,
        "key": f"shutter_assistant.{entry.entry_id}",
        "data": {"forecast_day": "2026-06-30", "forecast_max": 26.0},
    }
    hass.states.async_set("weather.home", "sunny")
    answer = {"fail": True}

    async def get_forecasts(call: ServiceCall) -> dict:
        if answer["fail"]:
            raise HomeAssistantError("weather service down")
        return {"weather.home": {"forecast": [{"temperature": 18.0}]}}

    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    await setup_entry(hass, entry)
    # today's forecast failed: the last value (26 °C) still counts
    assert hass.states.get(SUMMER).state == "on"
    answer["fail"] = False
    await advance(hass, freezer, 31 * 60)
    assert hass.states.get(SUMMER).state == "off"
    assert entry.runtime_data.forecast_day.isoformat() == "2026-07-01"


async def test_no_push_for_an_unavailable_contact(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(CONTACT, "unavailable")
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 15 * 60)
    assert calls["set_cover_position"] == []
    assert calls["notify"] == []


async def test_evening_run_caught_up_when_automatic_switched_on(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    await setup_entry(hass, make_entry())
    switch = {"entity_id": "switch.shutter_assistant_automatic"}
    await hass.services.async_call("switch", "turn_off", switch, blocking=True)
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == []
    await hass.services.async_call("switch", "turn_on", switch, blocking=True)
    await hass.async_block_till_done()
    assert len(calls["close_cover"]) == 1
    # switching again does not repeat it
    await hass.services.async_call("switch", "turn_off", switch, blocking=True)
    await hass.services.async_call("switch", "turn_on", switch, blocking=True)
    await hass.async_block_till_done()
    assert len(calls["close_cover"]) == 1


async def test_every_trigger_device_gets_an_attempt(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    set_cover(hass, 0)
    hass.states.async_set("media_player.fire_tv", "off")
    await setup_entry(
        hass,
        make_entry(
            window={
                "close_trigger_entities": ["media_player.fire_tv", TV],
                "close_trigger_active_states": ["idle", "paused", "playing"],
            }
        ),
    )
    hass.states.async_set("media_player.fire_tv", "playing")
    await hass.async_block_till_done()
    await advance(hass, freezer, 10, step=1)
    assert calls["close_cover"] == []  # cover already closed, no cycle lock
    set_cover(hass, 100)
    hass.states.async_set(TV, "playing")
    await hass.async_block_till_done()
    await advance(hass, freezer, 10, step=1)
    assert len(calls["close_cover"]) == 1


async def test_control_attributes(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _summer_noon(hass, freezer)
    await advance(hass, freezer, 60)
    attrs = hass.states.get("binary_sensor.living_room_sun_condition").attributes
    assert attrs["summer_day"] is True
    assert attrs["temperature_sensor"] == OUTDOOR
    assert attrs["temperature_threshold"] == 19.0
    assert attrs["temperature_ok"] is False
    assert attrs["temperature_ok_at"].startswith("2026-07-01T12:10")
    assert attrs["sensors"]["pv"] == {"entities": [PV], "threshold": 130.0}
    assert attrs["sensors"]["radiation"]["threshold"] == 150.0
    assert (attrs["azimuth_from"], attrs["azimuth_to"]) == (90.0, 270.0)
    assert attrs["sun_position"] == 10
    status = hass.states.get(STATUS).attributes
    assert status["cover"] == COVER
    assert status["window_open"] is False
    assert status["evening_start"].startswith("2026-07-01T21:00")
    assert status["override_until"] is None


AUTUMN_AFTERNOON = "2026-10-16 15:00:00+02:00"
ROOM = "climate.living_room"
AIR_CONDITIONER = "climate.living_room_ac"
HEATING_DAY = "binary_sensor.heating_day"


def _forecast_service(hass: HomeAssistant, high: float, low_tomorrow: float | None) -> None:
    forecast: list[dict] = [{"temperature": high, "templow": 8.0}]
    if low_tomorrow is not None:
        forecast.append({"temperature": high, "templow": low_tomorrow})

    async def get_forecasts(call: ServiceCall) -> dict:
        return {"weather.home": {"forecast": forecast}}

    hass.states.async_set("weather.home", "sunny")
    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )


async def _autumn_afternoon(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, night_low: float | None
) -> None:
    freezer.move_to(AUTUMN_AFTERNOON)
    _forecast_service(hass, 19.4, night_low)
    await setup_entry(hass, make_entry(weather="weather.home"))
    # a warm autumn afternoon: the outdoor temperature rises above 23 °C
    hass.states.async_set(OUTDOOR, "24.5")
    await hass.async_block_till_done()


async def test_warm_autumn_afternoon_with_cool_night_is_no_summer_day(
    hass: HomeAssistant, base_states, calls, hass_storage, freezer: FrozenDateTimeFactory
) -> None:
    await _autumn_afternoon(hass, freezer, night_low=9.0)
    engine = hass.config_entries.async_entries("shutter_assistant")[0].runtime_data
    assert engine.forecast_night_low == 9.0
    assert hass.states.get(SUMMER).state == "off"
    await advance(hass, freezer, 20 * 60)
    assert calls["set_cover_position"] == []
    details = engine.sun_details(engine.windows[WINDOW_ID])
    assert details["raised_by_outdoor_temperature"]
    assert details["night_low"] == 9.0
    assert details["night_threshold"] == 14.0


async def test_warm_autumn_afternoon_with_warm_night_is_a_summer_day(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    await _autumn_afternoon(hass, freezer, night_low=15.0)
    assert hass.states.get(SUMMER).state == "on"
    await advance(hass, freezer, 15 * 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_night_low_falls_back_to_today_and_is_restored(
    hass: HomeAssistant, base_states, calls, hass_storage, freezer: FrozenDateTimeFactory
) -> None:
    await _autumn_afternoon(hass, freezer, night_low=None)
    entry = hass.config_entries.async_entries("shutter_assistant")[0]
    assert entry.runtime_data.forecast_night_low == 8.0
    await advance(hass, freezer, 10)
    stored = hass_storage[f"shutter_assistant.{entry.entry_id}"]["data"]
    assert stored["forecast_night_low"] == 8.0


def _room(hass: HomeAssistant, current: float, setpoint: float = 21.0) -> None:
    hass.states.async_set(ROOM, "heat", {"current_temperature": current, "temperature": setpoint})


async def test_sun_protection_waits_for_a_warm_room(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    _room(hass, 21.5)
    await _summer_noon(hass, freezer, window={"room_entity": ROOM})
    await advance(hass, freezer, 30 * 60)
    assert calls["set_cover_position"] == []
    # setpoint 21 °C + 2 K reached: lowered after the sun hold time
    _room(hass, 23.0)
    await hass.async_block_till_done()
    await advance(hass, freezer, 4 * 60)
    assert calls["set_cover_position"] == []
    await advance(hass, freezer, 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_room_sensor_uses_the_fixed_threshold(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.room", "23.5", {"unit_of_measurement": "°C"})
    await _summer_noon(hass, freezer, window={"room_entity": "sensor.room"})
    await advance(hass, freezer, 20 * 60)
    assert calls["set_cover_position"] == []
    hass.states.async_set("sensor.room", "24.0", {"unit_of_measurement": "°C"})
    await hass.async_block_till_done()
    await advance(hass, freezer, 5 * 60)
    assert len(calls["set_cover_position"]) == 1


async def test_cooling_air_conditioner_counts_as_warm_room(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    _room(hass, 21.0)
    hass.states.async_set(AIR_CONDITIONER, "cool", {"hvac_action": "cooling"})
    await _summer_noon(
        hass, freezer, window={"room_entity": ROOM, "cooling_entity": AIR_CONDITIONER}
    )
    await advance(hass, freezer, 15 * 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_heating_day_keeps_the_warmth_of_the_sun(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(HEATING_DAY, "on")
    await _summer_noon(hass, freezer, heating_entity=HEATING_DAY)
    await advance(hass, freezer, 30 * 60)
    assert calls["set_cover_position"] == []
    hass.states.async_set(HEATING_DAY, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 5 * 60)
    assert len(calls["set_cover_position"]) == 1


async def test_heating_day_with_a_too_warm_room_still_protects(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set(HEATING_DAY, "on")
    _room(hass, 23.5)
    await _summer_noon(hass, freezer, heating_entity=HEATING_DAY, window={"room_entity": ROOM})
    await advance(hass, freezer, 15 * 60)
    assert len(calls["set_cover_position"]) == 1
