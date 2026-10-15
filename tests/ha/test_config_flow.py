"""Config flow, options flow and subentry flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, FlowType
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.shutter_assistant.const import DOMAIN, SUBENTRY_GROUP, SUBENTRY_WINDOW

from .conftest import COVER, GROUP_ID, OUTDOOR, PV, WINDOW_ID, make_entry, setup_entry

GENERAL = {"outdoor_temperature": OUTDOOR, "language": "auto", "notify_services": []}
SUMMER = {"summer_threshold": 23.0, "day_change_time": "01:00:00"}
EVENING = {
    "evening_earliest": "17:00:00",
    "evening_elevation": -4.0,
    "evening_latest": "21:00:00",
    "night_end": "03:30:00",
    "follow_up_earliest": "16:00:00",
}


async def test_user_flow(hass: HomeAssistant, base_states) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], GENERAL)
    assert result["step_id"] == "summer"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], SUMMER)
    assert result["step_id"] == "evening"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**EVENING, "evening_latest": "16:00:00"}
    )
    assert result["errors"] == {"evening_latest": "latest_before_earliest"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**EVENING, "night_end": "18:00:00"}
    )
    assert result["errors"] == {"night_end": "night_end_after_evening"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], EVENING)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.options["outdoor_temperature"] == OUTDOOR
    assert entry.options["vacation_morning_start"] == "07:00:00"
    assert result["next_flow"][0] == FlowType.CONFIG_SUBENTRIES_FLOW


async def test_options_flow(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "vacation"}
    )
    data = {
        "vacation_entities": [],
        "vacation_morning_start": "07:00:00",
        "vacation_morning_window": 60,
        "vacation_position_min": 90,
        "vacation_position_max": 60,
        "vacation_evening_start": "19:00:00",
        "vacation_evening_window": 90,
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], data)
    assert result["errors"] == {"vacation_position_max": "min_above_max"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**data, "vacation_position_min": 50}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["vacation_position_min"] == 50
    assert entry.options["outdoor_temperature"] == OUTDOOR


async def test_group_subentry(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_GROUP), context={"source": SOURCE_USER}
    )
    data = {"name": "West", "azimuth_from": 200, "azimuth_to": 200, "pv_sensors": [PV]}
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], data)
    assert result["errors"] == {"azimuth_to": "azimuth_equal"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**data, "azimuth_to": 320}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    titles = {sub.title for sub in entry.subentries.values()}
    assert "West" in titles

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_GROUP),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": GROUP_ID},
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "South", "azimuth_from": 100, "azimuth_to": 260}
    )
    assert result["type"] is FlowResultType.ABORT
    assert entry.subentries[GROUP_ID].data["azimuth_from"] == 100


async def test_window_subentry_with_group_and_morning(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WINDOW), context={"source": SOURCE_USER}
    )
    assert result["step_id"] == "basics"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Kitchen", "cover": COVER, "group": GROUP_ID}
    )
    assert result["step_id"] == "sun"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert "pv_threshold" in schema_keys and "radiation_threshold" in schema_keys
    assert "lux_threshold" not in schema_keys
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "pv_threshold": 130,
            "radiation_threshold": 150,
            "temperature_threshold": 19,
            "temperature_hold": 10,
            "sun_hold": 5,
            "sun_position": 20,
            "position_tolerance": 5,
            "auto_up": True,
            "notify_open_window": True,
            "manual_max_position": 25,
            "manual_detection_window": 5,
            "manual_follow_up": 5,
            "manual_at_sun_position": False,
        },
    )
    assert result["step_id"] == "behavior"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            "override": {
                "override_duration": 60,
                "override_sunrise_reset": False,
                "override_ignore_evening": False,
            },
            "conditions": {
                "open_block_free_states": ["off"],
                "close_trigger_entities": [],
                "close_trigger_active_states": ["on"],
                "close_trigger_on_delay": 8,
                "close_trigger_off_delay": 15,
                "close_trigger_min_position": 20,
                "close_trigger_max_lock": 12,
            },
            "evening": {
                "evening_close": True,
                "follow_up_close": True,
                "evening_custom": False,
                "evening_earliest": "17:00:00",
                "evening_elevation": -4,
                "evening_latest": "21:00:00",
            },
            "ventilation_settings": {
                "ventilation": True,
                "ventilation_position": 30,
                "closed_position": 5,
                "ventilation_delay_evening": 3,
                "ventilation_delay_day": 60,
                "vacation": True,
            },
        },
    )
    assert result["step_id"] == "morning"
    morning = {
        "morning_enabled": True,
        "morning_mode": "brightness",
        "morning_earliest": "06:00:00",
        "morning_latest": "09:00:00",
        "morning_position": 100,
        "morning_sun_position": True,
    }
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], morning)
    assert result["errors"] == {"morning_mode": "no_lux_sensor"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**morning, "morning_mode": "time"}
    )
    assert result["step_id"] == "morning_time"
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {"morning_time_workday": "06:45:00", "morning_time_weekend": "08:30:00"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    sub = next(s for s in entry.subentries.values() if s.title == "Kitchen")
    assert sub.data["sun_position"] == 20
    assert sub.data["morning_time_workday"] == "06:45:00"
    assert sub.data["override_duration"] == 60
    assert "open_block_entity" not in sub.data


async def test_window_without_group_skips_sun(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WINDOW), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": " ", "cover": COVER}
    )
    assert result["errors"] == {"name": "name_required"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Hall", "cover": COVER}
    )
    assert result["step_id"] == "behavior"


async def test_window_reconfigure_menu_saves_one_category(hass: HomeAssistant, base_states) -> None:
    entry = make_entry(window={"sun_position": 15, "override_ignore_evening": True})
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WINDOW),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": WINDOW_ID},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"] == ["basics", "sun", "behavior", "morning"]
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "sun"}
    )
    assert result["step_id"] == "sun"
    assert result["last_step"] is True
    values = {str(k): k.default() for k in result["data_schema"].schema if callable(k.default)}
    assert values["sun_position"] == 15
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**values, "sun_position": 25}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    data = entry.subentries[WINDOW_ID].data
    assert data["sun_position"] == 25
    # everything else is kept
    assert data["override_ignore_evening"] is True
    assert data["cover"] == COVER


async def test_window_reconfigure_basics_only(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WINDOW),
        context={"source": SOURCE_RECONFIGURE, "subentry_id": WINDOW_ID},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "basics"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"name": "Lounge", "cover": COVER, "group": GROUP_ID}
    )
    assert result["type"] is FlowResultType.ABORT
    assert entry.subentries[WINDOW_ID].title == "Lounge"
    assert entry.subentries[WINDOW_ID].data["sun_position"] == 10


async def test_window_creation_steps_say_next(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_WINDOW), context={"source": SOURCE_USER}
    )
    assert result["last_step"] is False
