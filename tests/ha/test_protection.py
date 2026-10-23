"""Weather protection, tilted windows, the lockout protection and the evening position."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant

from .conftest import CONTACT, OUTDOOR, advance, make_entry, set_cover, setup_entry
from .conftest import COVER as COVER_LIVING

WIND = "sensor.wind_gust"
RAIN = "binary_sensor.rain"
TILT = "binary_sensor.living_room_tilted"
STATUS = "sensor.living_room_status"
OVERRIDE = "binary_sensor.living_room_manual_override"
WIND_ON = "binary_sensor.shutter_assistant_wind_protection"
AUTOMATIC = "switch.shutter_assistant_automatic"
WINDOW_AUTOMATIC = "switch.living_room_automatic"


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
        make_entry(
            window={"weather_protection": True, "wind_position": 100},
            wind_entity=WIND,
            protection_release=15,
        ),
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


async def test_own_wind_threshold_per_window(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    second = "cover.balcony"
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    hass.states.async_set(second, "open", {"current_position": 100, "supported_features": 15})
    set_cover(hass, 40)
    balcony = {
        "window_balcony": {
            "name": "Balcony",
            "cover": second,
            "window_sensors": [],
            "weather_protection": True,
            "wind_position": 20,
            "window_wind_threshold": 50,
        }
    }
    entry = make_entry(
        window={"weather_protection": True, "wind_position": 20},
        extra_windows=balcony,
        wind_entity=WIND,
        wind_threshold=75,
        protection_release=15,
    )
    await setup_entry(hass, entry)
    events = []
    hass.bus.async_listen("shutter_assistant_protection", events.append)

    def moved() -> list[tuple[str, int]]:
        return [(c.data["entity_id"], c.data["position"]) for c in calls["set_cover_position"]]

    # above the own threshold of the balcony, below the global one
    hass.states.async_set(WIND, "60")
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    assert moved() == [(second, 20)]
    assert hass.states.get(WIND_ON).state == "on"
    assert hass.states.get(WIND_ON).attributes["windows"] == ["Balcony"]
    assert events[-1].data == {
        "kind": "wind",
        "active": True,
        "window": "Balcony",
        "window_id": "window_balcony",
    }
    assert hass.states.get(STATUS).state != "protection"

    # the own state survives a reload
    await advance(hass, freezer, 10, step=1)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(WIND_ON).state == "on"

    # above the global threshold: the living room follows
    hass.states.async_set(WIND, "80")
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    assert (COVER_LIVING, 20) in moved()
    assert hass.states.get(STATUS).state == "protection"

    # calm: both end after the release time
    hass.states.async_set(WIND, "5")
    await hass.async_block_till_done()
    await advance(hass, freezer, 14 * 60)
    assert hass.states.get(WIND_ON).state == "on"
    await advance(hass, freezer, 2 * 60)
    assert hass.states.get(WIND_ON).state == "off"
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


async def test_positions_without_the_switch_of_the_window_do_nothing(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    set_cover(hass, 40)
    await setup_entry(
        hass,
        make_entry(window={"wind_position": 100, "window_wind_threshold": 20}, wind_entity=WIND),
    )
    hass.states.async_set(WIND, "90")
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    assert calls["open_cover"] == [] and positions(calls) == []
    assert hass.states.get(STATUS).state != "protection"


async def test_no_weather_protection_with_the_automatic_off(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    set_cover(hass, 40)
    await setup_entry(
        hass,
        make_entry(window={"weather_protection": True, "wind_position": 100}, wind_entity=WIND),
    )
    await hass.services.async_call("switch", "turn_off", {"entity_id": AUTOMATIC}, blocking=True)
    hass.states.async_set(WIND, "90")
    await hass.async_block_till_done()
    assert calls["open_cover"] == []
    assert hass.states.get(STATUS).state == "off"
    # automatic on again: the running protection applies
    await hass.services.async_call("switch", "turn_on", {"entity_id": AUTOMATIC}, blocking=True)
    assert len(calls["open_cover"]) == 1
    assert hass.states.get(STATUS).state == "protection"
    # the automatic of the window off ends it for this window, nothing moves
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": WINDOW_AUTOMATIC}, blocking=True
    )
    assert hass.states.get(STATUS).state == "off"
    assert len(calls["open_cover"]) == 1 and positions(calls) == []
    reason = hass.states.get("sensor.living_room_last_reason")
    assert reason.attributes["code"] == "protection_automatic_off"


async def test_saving_settings_does_not_move_protected_covers_again(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    second = "cover.balcony"
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(WIND, "10")
    hass.states.async_set(second, "open", {"current_position": 100, "supported_features": 15})
    set_cover(hass, 100)
    balcony = {
        "window_balcony": {
            "name": "Balcony",
            "cover": second,
            "window_sensors": [],
            "weather_protection": True,
            "wind_position": 20,
            "window_wind_threshold": 50,
        }
    }
    entry = make_entry(
        window={"weather_protection": True, "wind_position": 20},
        extra_windows=balcony,
        wind_entity=WIND,
        wind_threshold=75,
    )
    await setup_entry(hass, entry)
    hass.states.async_set(WIND, "80")
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    assert len(calls["set_cover_position"]) == 2
    # moved up by hand during the protection
    set_cover(hass, 100)
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)

    # own wind threshold of the balcony changed: reload, nothing moves again
    sub = entry.subentries["window_balcony"]
    hass.config_entries.async_update_subentry(
        entry, sub, data={**sub.data, "window_wind_threshold": 60}
    )
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    # global threshold changed: reload, nothing moves again either
    hass.config_entries.async_update_entry(entry, options={**entry.options, "wind_threshold": 70})
    await hass.async_block_till_done()
    await advance(hass, freezer, 30, step=1)
    assert len(calls["set_cover_position"]) == 2
    assert hass.states.get(STATUS).state == "protection"


async def test_rain_closes_after_the_window_was_closed(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-15 12:00:00+02:00")
    hass.states.async_set(RAIN, "off")
    hass.states.async_set(CONTACT, "on")
    await setup_entry(
        hass, make_entry(window={"weather_protection": True, "rain_position": 0}, rain_entity=RAIN)
    )
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
    await setup_entry(hass, make_entry(window={"weather_protection": True, "frost_position": 5}))
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
