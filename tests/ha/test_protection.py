"""Weather protection, tilted windows, the lockout protection and the evening position."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from .conftest import CONTACT, OUTDOOR, advance, make_entry, set_cover, setup_entry

WIND = "sensor.wind_gust"
RAIN = "binary_sensor.rain"
TILT = "binary_sensor.living_room_tilted"
STATUS = "sensor.living_room_status"
OVERRIDE = "binary_sensor.living_room_manual_override"
WIND_ON = "binary_sensor.shutter_assistant_wind_protection"


def positions(calls) -> list[int]:
    return [c.data["position"] for c in calls["set_cover_position"]]


async def test_wind_moves_also_during_an_override_and_releases_later(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    set_cover(hass, 40)
    await setup_entry(
        hass,
        make_entry(window={"wind_position": 100}, wind_entity=WIND, protection_release=15),
    )
    events = []
    hass.bus.async_listen("shutter_assistant_protection", events.append)
    # manual movement: override
    set_cover(hass, 40, state="closing")
    set_cover(hass, 30)
    await hass.async_block_till_done()
    assert hass.states.get(OVERRIDE).state == "on"
    hass.states.async_set(WIND, "70")
    await hass.async_block_till_done()
    assert len(calls["open_cover"]) == 1
    assert hass.states.get(STATUS).state == "protection"
    assert hass.states.get(WIND_ON).state == "on"
    assert events[-1].data == {"kind": "wind", "active": True}
    # an unavailable sensor does not end it
    hass.states.async_set(WIND, "unavailable")
    await hass.async_block_till_done()
    await advance(hass, freezer, 30 * 60)
    assert hass.states.get(WIND_ON).state == "on"
    # calm: ends only after the release time
    hass.states.async_set(WIND, "5")
    await hass.async_block_till_done()
    await advance(hass, freezer, 14 * 60)
    assert hass.states.get(WIND_ON).state == "on"
    await advance(hass, freezer, 2 * 60)
    assert hass.states.get(WIND_ON).state == "off"
    assert events[-1].data == {"kind": "wind", "active": False}
    assert hass.states.get(STATUS).state != "protection"


async def test_windows_without_a_position_are_not_affected(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    set_cover(hass, 40)
    await setup_entry(hass, make_entry(wind_entity=WIND))
    hass.states.async_set(WIND, "90")
    await hass.async_block_till_done()
    assert calls["open_cover"] == []
    assert hass.states.get(STATUS).state != "protection"


async def test_rain_closes_after_the_window_was_closed(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(RAIN, "off")
    hass.states.async_set(CONTACT, "on")
    await setup_entry(hass, make_entry(window={"rain_position": 0}, rain_entity=RAIN))
    hass.states.async_set(RAIN, "on")
    await hass.async_block_till_done()
    assert calls["close_cover"] == []
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 6, step=1)
    assert len(calls["close_cover"]) == 1


async def test_frost_keeps_a_gap_in_the_evening(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    hass.states.async_set(OUTDOOR, "-3.0")
    await setup_entry(hass, make_entry(window={"frost_position": 5}))
    assert hass.states.get("binary_sensor.shutter_assistant_frost_protection").state == "on"
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == []
    assert positions(calls) == [5]


async def test_evening_position_and_tilted_window(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-12-15 16:50:00+01:00")
    hass.states.async_set(TILT, "on")
    await setup_entry(hass, make_entry(window={"tilt_sensors": [TILT], "evening_position": 10}))
    await advance(hass, freezer, 15 * 60)
    # tilted: closes, but only down to the ventilation position
    assert positions(calls) == [30]
    attrs = hass.states.get(STATUS).attributes
    assert attrs["window_tilted"] is True and attrs["window_open"] is False


async def test_window_handle_open_blocks_tilted_allows(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    handle = "sensor.living_room_handle"
    freezer.move_to("2026-12-15 16:50:00+01:00")
    hass.states.async_set(handle, "open")
    await setup_entry(hass, make_entry(window={"window_sensors": [handle]}))
    await advance(hass, freezer, 15 * 60)
    assert calls["close_cover"] == [] and positions(calls) == []
    # turned to tilted: counts after the debounce time, the follow-up closes to 30 %
    hass.states.async_set(handle, "tilted")
    await hass.async_block_till_done()
    await advance(hass, freezer, 6, step=1)
    assert positions(calls) == [30]


async def test_lockout_protection_for_a_door(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    exception = "climate.mobile_ac"
    freezer.move_to("2026-12-15 16:50:00+01:00")
    hass.states.async_set(CONTACT, "on")
    hass.states.async_set(exception, "cool")
    await setup_entry(
        hass,
        make_entry(window={"lockout_protection": True, "window_exception_entity": exception}),
    )
    await advance(hass, freezer, 15 * 60)
    # the exception allows closing with the door open, the lockout keeps 30 %
    assert calls["close_cover"] == []
    assert positions(calls) == [30]
