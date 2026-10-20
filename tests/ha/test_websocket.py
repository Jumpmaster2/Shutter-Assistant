"""WebSocket API of the panel."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.shutter_assistant.const import (
    DEFAULTS,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    WINDOW_DEFAULTS,
)
from custom_components.shutter_assistant.websocket import (
    OPTION_KEYS,
    WINDOW_KEYS,
    _all_window_fields,
    _key,
    _option_fields,
)

from .conftest import COVER, GROUP_ID, OUTDOOR, PV, TV, WINDOW_ID, make_entry, setup_entry


async def _send(client, **msg):
    await client.send_json_auto_id(msg)
    return await client.receive_json()


async def test_config(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    msg = await _send(client, type="shutter_assistant/config")
    assert msg["success"], msg
    cfg = msg["result"]
    assert cfg["loaded"] is True
    assert cfg["options"]["outdoor_temperature"] == OUTDOOR
    assert [g["id"] for g in cfg["groups"]] == [GROUP_ID]
    window = cfg["windows"][0]
    assert window["id"] == WINDOW_ID
    assert window["data"]["cover"] == COVER
    assert window["entities"]["status"].startswith("sensor.")
    assert window["entities"]["sun_condition"].startswith("binary_sensor.")
    assert cfg["entities"]["automatic"] == "switch.shutter_assistant_automatic"
    assert cfg["defaults"]["window"]["sun_position"] == 10
    fields = cfg["fields"]
    assert fields["sun_position"]["number"]["max"] == 100
    assert fields["sun_position"]["number"]["unit_of_measurement"] == "%"
    assert fields["cover"]["entity"]["domain"] == ["cover"]
    assert fields["window_sensors"]["entity"]["multiple"] is True
    assert "time" in fields["evening_earliest"]
    assert "boolean" in fields["auto_up"]
    # every morning mode and every sensor type is described
    for key in ("morning_trigger_entity", "morning_lux_threshold", "lux_threshold"):
        assert key in fields
    assert fields["language"]["select"]["translation_key"] == "language"
    assert fields["override_trigger"]["select"]["options"] == ["movement", "command"]
    assert cfg["options"]["override_trigger"] == "movement"


async def test_save_options(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry(weather="weather.home")
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"summer_threshold": "25", "evening_earliest": "17:30", "weather": None},
    )
    assert msg["success"], msg
    assert "errors" not in msg["result"]
    assert entry.options["summer_threshold"] == 25
    assert entry.options["evening_earliest"] == "17:30:00"
    assert "weather" not in entry.options
    assert entry.options["outdoor_temperature"] == OUTDOOR

    # same checks as the dialogs
    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"evening_latest": "16:00:00"},
    )
    assert msg["result"]["errors"] == {"evening_latest": "latest_before_earliest"}
    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"vacation_position_min": 90, "vacation_position_max": 50},
    )
    assert msg["result"]["errors"] == {"vacation_position_max": "min_above_max"}
    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"summer_threshold": 99, "weather": "light.x"},
    )
    assert msg["result"]["errors"] == {
        "summer_threshold": "invalid_value",
        "weather": "invalid_value",
    }
    # without outdoor sensor and weather entity there is no temperature
    msg = await _send(
        client, type="shutter_assistant/save_options", options={"outdoor_temperature": ""}
    )
    assert msg["result"]["errors"] == {"outdoor_temperature": "need_temperature_source"}
    # only notification services
    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"notify_services": ["homeassistant.restart"]},
    )
    assert msg["result"]["errors"] == {"notify_services": "invalid_notify_service"}
    assert entry.options["summer_threshold"] == 25

    msg = await _send(
        client, type="shutter_assistant/save_options", options={"override_trigger": "sometimes"}
    )
    assert msg["result"]["errors"] == {"override_trigger": "invalid_value"}
    msg = await _send(
        client, type="shutter_assistant/save_options", options={"override_trigger": "command"}
    )
    assert entry.options["override_trigger"] == "command"

    msg = await _send(client, type="shutter_assistant/save_options", options={"nope": 1})
    assert not msg["success"]


async def test_every_field_can_be_saved(hass: HomeAssistant, base_states) -> None:
    """Every field the panel shows is accepted when saving."""
    entry = make_entry()
    await setup_entry(hass, entry)
    options = {_key(m) for m in _option_fields(hass, {**DEFAULTS})}
    windows = {_key(m) for m in _all_window_fields(entry, {**WINDOW_DEFAULTS}, "°C")}
    assert options - OPTION_KEYS == set()
    assert windows - WINDOW_KEYS == set()


async def test_save_heat_need_entities(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    hass.states.async_set("binary_sensor.heating_day", "off")
    hass.states.async_set("climate.living_room", "heat")
    hass.states.async_set("climate.living_room_ac", "off")
    client = await hass_ws_client(hass)

    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"heating_entity": "binary_sensor.heating_day", "night_threshold": 15},
    )
    assert msg["success"], msg
    assert "errors" not in msg["result"]
    assert entry.options["heating_entity"] == "binary_sensor.heating_day"
    assert entry.options["night_threshold"] == 15

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"room_entity": "climate.living_room", "cooling_entity": "climate.living_room_ac"},
    )
    assert msg["success"], msg
    assert "errors" not in msg["result"]
    data = entry.subentries[WINDOW_ID].data
    assert data["room_entity"] == "climate.living_room"
    assert data["cooling_entity"] == "climate.living_room_ac"
    assert data["cover"] == COVER

    # cleared again
    msg = await _send(
        client, type="shutter_assistant/save_options", options={"heating_entity": None}
    )
    assert "heating_entity" not in entry.options
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"cooling_entity": None},
    )
    assert "cooling_entity" not in entry.subentries[WINDOW_ID].data
    assert entry.subentries[WINDOW_ID].data["room_entity"] == "climate.living_room"


async def test_save_group(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        data={"name": " West ", "azimuth_from": 200, "azimuth_to": 330, "pv_sensors": [PV]},
    )
    assert msg["success"], msg
    sub_id = msg["result"]["subentry_id"]
    sub = entry.subentries[sub_id]
    assert sub.title == "West"
    assert sub.data["azimuth_from"] == 200
    assert sub.data["lux_sensors"] == []

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        subentry_id=sub_id,
        data={"name": "", "azimuth_to": 200},
    )
    assert msg["result"]["errors"] == {"name": "name_required"}
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        subentry_id=sub_id,
        data={"azimuth_to": 200},
    )
    assert msg["result"]["errors"] == {"azimuth_to": "azimuth_equal"}

    msg = await _send(client, type="shutter_assistant/delete_subentry", subentry_id=sub_id)
    assert msg["success"]
    assert sub_id not in entry.subentries


async def test_save_window(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    # change: thresholds, clear the group and an optional entity
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"pv_threshold": 300, "open_block_entity": TV, "unknown_key": 1},
    )
    assert msg["success"], msg
    data = entry.subentries[WINDOW_ID].data
    assert data["pv_threshold"] == 300
    assert data["open_block_entity"] == TV
    assert data["cover"] == COVER
    assert "unknown_key" not in data
    # the global evening times are taken over like in the dialog
    assert data["evening_earliest"] == "17:00:00"

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"group": None, "open_block_entity": ""},
    )
    data = entry.subentries[WINDOW_ID].data
    assert "group" not in data
    assert "open_block_entity" not in data

    # checks: name, cover domain, range, unknown group, morning
    errors = (
        await _send(
            client,
            type="shutter_assistant/save_subentry",
            subentry_type=SUBENTRY_WINDOW,
            data={"name": " ", "cover": "light.x", "sun_position": 120, "group": "nope"},
        )
    )["result"]["errors"]
    assert errors == {
        "name": "name_required",
        "cover": "invalid_value",
        "group": "invalid_value",
        # not shown without a group, but checked anyway
        "sun_position": "invalid_value",
    }
    errors = (
        await _send(
            client,
            type="shutter_assistant/save_subentry",
            subentry_type=SUBENTRY_WINDOW,
            data={
                "name": "Bath",
                "cover": "cover.bath",
                "morning_enabled": True,
                "morning_mode": "trigger",
            },
        )
    )["result"]["errors"]
    assert errors == {"morning_trigger_entity": "required"}
    errors = (
        await _send(
            client,
            type="shutter_assistant/save_subentry",
            subentry_type=SUBENTRY_WINDOW,
            data={
                "name": "Bath",
                "cover": "cover.bath",
                "group": GROUP_ID,
                "morning_enabled": True,
                "morning_mode": "brightness",
            },
        )
    )["result"]["errors"]
    assert errors == {"morning_mode": "no_lux_sensor"}
    errors = (
        await _send(
            client,
            type="shutter_assistant/save_subentry",
            subentry_type=SUBENTRY_WINDOW,
            data={
                "name": "Bath",
                "cover": "cover.bath",
                "evening_custom": True,
                "evening_earliest": "20:00",
                "evening_latest": "19:00",
            },
        )
    )["result"]["errors"]
    assert errors == {"evening_latest": "latest_before_earliest"}

    # new window with the defaults
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        data={"name": "Bath", "cover": "cover.bath", "group": GROUP_ID, "morning_latest": "08:30"},
    )
    assert msg["success"], msg
    sub = entry.subentries[msg["result"]["subentry_id"]]
    assert sub.title == "Bath"
    assert sub.data["group"] == GROUP_ID
    assert sub.data["sun_position"] == 10
    assert sub.data["morning_latest"] == "08:30:00"

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        subentry_id=WINDOW_ID,
        data={"name": "x"},
    )
    assert not msg["success"]


async def test_end_override(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)
    engine = entry.runtime_data

    msg = await _send(client, type="shutter_assistant/end_override", window_id=WINDOW_ID)
    assert msg["result"] == {"ended": False}

    engine._start_override(engine.windows[WINDOW_ID], dt_util.now())
    assert engine.windows[WINDOW_ID].override_active
    msg = await _send(client, type="shutter_assistant/end_override", window_id=WINDOW_ID)
    assert msg["result"] == {"ended": True}
    assert not engine.windows[WINDOW_ID].override_active

    msg = await _send(client, type="shutter_assistant/end_override", window_id="nope")
    assert not msg["success"]


async def test_attributes_for_the_panel(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    evening = hass.states.get("binary_sensor.shutter_assistant_evening_mode")
    assert evening.attributes["start"] < evening.attributes["end"]
    automatic = hass.states.get("switch.shutter_assistant_automatic")
    # loaded while Home Assistant runs: no restart protection
    assert automatic.attributes["restart_protection_until"] is None
    engine = entry.runtime_data
    engine.startup_until = dt_util.now() + timedelta(minutes=5)
    engine.async_update_listeners()
    await hass.async_block_till_done()
    automatic = hass.states.get("switch.shutter_assistant_automatic")
    assert automatic.attributes["restart_protection_until"] == engine.startup_until.isoformat()


async def test_house_and_walls(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)

    msg = await _send(client, type="shutter_assistant/config")
    fields = msg["result"]["fields"]
    assert fields["house_width"]["number"]["unit_of_measurement"] == "m"
    assert fields["wall"]["select"]["options"] == ["front", "right", "back", "left"]

    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"house_azimuth": 175, "house_width": "10.5", "house_depth": 8},
    )
    assert "errors" not in msg["result"], msg
    assert entry.options["house_azimuth"] == 175
    assert entry.options["house_width"] == 10.5
    msg = await _send(
        client,
        type="shutter_assistant/save_options",
        options={"house_azimuth": 400, "house_depth": 0},
    )
    assert msg["result"]["errors"] == {
        "house_azimuth": "invalid_value",
        "house_depth": "invalid_value",
    }
    # the house is optional: clearing a value removes it
    msg = await _send(client, type="shutter_assistant/save_options", options={"house_depth": None})
    assert "house_depth" not in entry.options
    assert entry.options["house_width"] == 10.5

    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        subentry_id=GROUP_ID,
        data={"wall": "front"},
    )
    assert msg["success"], msg
    assert entry.subentries[GROUP_ID].data["wall"] == "front"
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"wall": "nope"},
    )
    assert msg["result"]["errors"] == {"wall": "invalid_value"}
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"wall": "left"},
    )
    assert entry.subentries[WINDOW_ID].data["wall"] == "left"
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"wall_position": 2},
    )
    assert entry.subentries[WINDOW_ID].data["wall_position"] == 2
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"wall_position": 0},
    )
    assert msg["result"]["errors"] == {"wall_position": "invalid_value"}
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"wall": None},
    )
    assert "wall" not in entry.subentries[WINDOW_ID].data


async def test_commands_need_an_admin(
    hass: HomeAssistant, base_states, hass_ws_client, hass_read_only_access_token
) -> None:
    await setup_entry(hass, make_entry())
    client = await hass_ws_client(hass, hass_read_only_access_token)
    for msg in (
        {"type": "shutter_assistant/config"},
        {"type": "shutter_assistant/save_options", "options": {}},
        {"type": "shutter_assistant/end_override", "window_id": WINDOW_ID},
    ):
        result = await _send(client, **msg)
        assert not result["success"]
        assert result["error"]["code"] == "unauthorized"


async def test_cover_and_sensor_checks(hass: HomeAssistant, base_states, hass_ws_client) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    client = await hass_ws_client(hass)
    # a second window for the same cover
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        data={"name": "Copy", "cover": COVER},
    )
    assert msg["result"]["errors"] == {"cover": "cover_in_use"}
    # the own window may keep its cover
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_WINDOW,
        subentry_id=WINDOW_ID,
        data={"cover": COVER},
    )
    assert "errors" not in msg["result"]
    # a sun sensor without a number
    hass.states.async_set("sensor.weather_text", "sunny")
    msg = await _send(
        client,
        type="shutter_assistant/save_subentry",
        subentry_type=SUBENTRY_GROUP,
        data={
            "name": "East",
            "azimuth_from": 0,
            "azimuth_to": 180,
            "lux_sensors": ["sensor.weather_text"],
        },
    )
    assert msg["result"]["errors"] == {"lux_sensors": "not_numeric"}


async def test_config_payload_has_the_temperature_unit(
    hass: HomeAssistant, base_states, hass_ws_client
) -> None:
    await setup_entry(hass, make_entry())
    client = await hass_ws_client(hass)
    msg = await _send(client, type="shutter_assistant/config")
    assert msg["result"]["temperature_unit"] == "°C"
    assert msg["result"]["interval_unit"] == "K"
    assert msg["result"]["fields"]["summer_threshold"]["number"]["unit_of_measurement"] == "°C"
