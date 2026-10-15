"""Binary sensors: summer day, evening mode and the state of every window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .engine import ShutterConfigEntry, ShutterEngine
from .entity import GlobalEntity, WindowEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShutterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    engine = entry.runtime_data
    async_add_entities([SummerDay(engine), EveningMode(engine)])
    for window_id in engine.windows:
        async_add_entities(
            [
                Override(engine, window_id),
                SunCondition(engine, window_id),
                SunProtectionToday(engine, window_id),
                EveningClosed(engine, window_id),
            ],
            config_subentry_id=window_id,
        )


class SummerDay(GlobalEntity, BinarySensorEntity):
    """Is today a summer day (forecast high or outdoor temperature above the threshold)?"""

    def __init__(self, engine: ShutterEngine) -> None:
        super().__init__(engine, "summer_day")

    @property
    def is_on(self) -> bool:
        return self.coordinator.summer

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        engine = self.coordinator
        return {
            "forecast_max": engine.forecast_max,
            "forecast_day": engine.forecast_day.isoformat() if engine.forecast_day else None,
            "raised_by_outdoor_temperature": engine.raised_day is not None
            and engine.raised_day == engine._sun_day(dt_util.now()),
        }


class EveningMode(GlobalEntity, BinarySensorEntity):
    """Evening mode with the global settings."""

    def __init__(self, engine: ShutterEngine) -> None:
        super().__init__(engine, "evening_mode")

    @property
    def is_on(self) -> bool:
        return self.coordinator.global_evening_active


class Override(WindowEntity, BinarySensorEntity):
    """Manual override active."""

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "override")

    @property
    def is_on(self) -> bool:
        return self.window.override_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        win = self.window
        return {
            "until": win.override_until.isoformat() if win.override_until else None,
            "since": win.override_since.isoformat() if win.override_since else None,
            "ends_at_sunrise": win.override_sunrise,
        }


class SunCondition(WindowEntity, BinarySensorEntity):
    """Sun condition met (summer day, temperature and sun sensors, including hold times)."""

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "sun_condition")

    @property
    def is_on(self) -> bool:
        return self.coordinator.live(self.window)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.coordinator.sun_details(self.window)


class SunProtectionToday(WindowEntity, BinarySensorEntity):
    """The window was protected from the sun today (lowered or marked)."""

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "sun_protection_today")

    @property
    def is_on(self) -> bool:
        return self.coordinator.sun_marker(self.window)


class EveningClosed(WindowEntity, BinarySensorEntity):
    """The window was closed by the evening run this evening."""

    def __init__(self, engine: ShutterEngine, window_id: str) -> None:
        super().__init__(engine, window_id, "evening_closed")

    @property
    def is_on(self) -> bool:
        return self.coordinator.evening_marker(self.window)
