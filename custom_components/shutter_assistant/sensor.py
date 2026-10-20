"""Sensors: forecast high, and status plus last reason of every window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import MATCH_ALL, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .engine import ShutterConfigEntry, ShutterEngine
from .entity import GlobalEntity, WindowEntity
from .logic.window import STATUSES

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShutterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    engine = entry.runtime_data
    async_add_entities([ForecastMax(engine)])
    for window_id in engine.windows:
        async_add_entities(
            [Status(engine, window_id), LastReason(engine, window_id)],
            config_subentry_id=window_id,
        )


class ForecastMax(GlobalEntity, SensorEntity):
    """Today's forecast high used for the summer day."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, engine: ShutterEngine) -> None:
        super().__init__(engine, "forecast_max")
        # the forecast comes in the unit of the instance
        self._attr_native_unit_of_measurement = engine.temperature_unit

    @property
    def native_value(self) -> float | None:
        return self.coordinator.forecast_max


class Status(WindowEntity, SensorEntity):
    """What the automation currently does with the window."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES
    # control values for the panel and own cards, not worth keeping in the history
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "status")

    @property
    def native_value(self) -> str:
        return self.coordinator.status(self.window)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.coordinator.window_details(self.window)


class LastReason(WindowEntity, SensorEntity):
    """The last movement or decision and why."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "last_reason")

    @property
    def native_value(self) -> str | None:
        message = self.window.last_reason.get("message")
        return str(message)[:255] if message else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reason = self.window.last_reason
        return {
            "code": reason.get("code"),
            "position": reason.get("position"),
            "time": reason.get("time"),
        }
