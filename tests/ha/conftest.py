"""Fixtures for tests with a Home Assistant test instance."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.shutter_assistant.const import (
    CONF_OUTDOOR_TEMP,
    DEFAULTS,
    DOMAIN,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
)

COVER = "cover.living_room"
CONTACT = "binary_sensor.living_room_window"
OUTDOOR = "sensor.outdoor_temperature"
PV = "sensor.pv_south"
RADIATION = "sensor.radiation"
TV = "media_player.tv"
VACATION = "input_boolean.vacation"

GROUP_ID = "group_south"
WINDOW_ID = "window_living"

GROUP_DATA = {
    "name": "South",
    "azimuth_from": 90,
    "azimuth_to": 270,
    "pv_sensors": [PV],
    "radiation_sensors": [RADIATION],
    "lux_sensors": [],
}

WINDOW_DATA = {
    "name": "Living room",
    "cover": COVER,
    "window_sensors": [CONTACT],
    "group": GROUP_ID,
    "notify_open_window": True,
}

SUMMER_NOON = "2026-07-01 12:00:00+02:00"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations."""
    return


@pytest.fixture
async def setup_location(hass: HomeAssistant) -> None:
    """A location in central Europe."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    hass.config.latitude = 48.14
    hass.config.longitude = 11.58
    hass.config.elevation = 500


@pytest.fixture
def calls(hass: HomeAssistant) -> dict[str, list[ServiceCall]]:
    """Record cover and notify service calls."""
    return {
        "set_cover_position": async_mock_service(hass, "cover", "set_cover_position"),
        "open_cover": async_mock_service(hass, "cover", "open_cover"),
        "close_cover": async_mock_service(hass, "cover", "close_cover"),
        "notify": async_mock_service(hass, "notify", "phone"),
    }


def set_cover(hass: HomeAssistant, position: int, state: str | None = None, context=None) -> None:
    state = state or ("closed" if position == 0 else "open")
    hass.states.async_set(
        COVER,
        state,
        {"current_position": position, "supported_features": 15, "device_class": "shutter"},
        context=context,
    )


@pytest.fixture
async def base_states(hass: HomeAssistant, setup_location) -> None:
    hass.states.async_set(OUTDOOR, "15.0", {"unit_of_measurement": "°C"})
    hass.states.async_set(PV, "500", {"unit_of_measurement": "W"})
    hass.states.async_set(RADIATION, "400", {"unit_of_measurement": "W/m²"})
    hass.states.async_set(CONTACT, "off")
    hass.states.async_set(TV, "off")
    hass.states.async_set(VACATION, "off")
    set_cover(hass, 100)
    await hass.async_block_till_done()


def make_entry(
    window: dict[str, Any] | None = None,
    group: dict[str, Any] | None = None,
    **options: Any,
) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Shutter Assistant",
        data={},
        options={
            **DEFAULTS,
            CONF_OUTDOOR_TEMP: OUTDOOR,
            "notify_services": ["notify.phone"],
            "vacation_entities": [VACATION],
            **options,
        },
        subentries_data=[
            ConfigSubentryData(
                data=group or GROUP_DATA,
                subentry_id=GROUP_ID,
                subentry_type=SUBENTRY_GROUP,
                title=(group or GROUP_DATA)["name"],
                unique_id=None,
            ),
            ConfigSubentryData(
                data={**WINDOW_DATA, **(window or {})},
                subentry_id=WINDOW_ID,
                subentry_type=SUBENTRY_WINDOW,
                title=(window or {}).get("name", WINDOW_DATA["name"]),
                unique_id=None,
            ),
        ],
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float, step: float = 60
) -> None:
    """Move time forward in steps and fire the time listeners."""
    remaining = seconds
    while remaining > 0:
        delta = min(step, remaining)
        freezer.tick(timedelta(seconds=delta))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        remaining -= delta
