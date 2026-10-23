"""Switches: the automatic as a whole, and automatic and sun protection per window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    async_add_entities([AutomaticSwitch(engine)])
    for window_id in engine.windows:
        async_add_entities(
            [
                WindowSwitch(engine, window_id, "window_automatic", "automatic"),
                WindowSwitch(engine, window_id, "window_sun_protection", "sun_enabled"),
            ],
            config_subentry_id=window_id,
        )


class AutomaticSwitch(GlobalEntity, SwitchEntity):
    """Main switch: off means no automatic movement at all (kept over restarts)."""

    def __init__(self, engine: ShutterEngine) -> None:
        super().__init__(engine, "automatic")

    @property
    def is_on(self) -> bool:
        return self.coordinator.automatic

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        until = self.coordinator.startup_until
        return {
            "restart_protection_until": (
                until.isoformat() if until and until > dt_util.now() else None
            )
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic(False)


class WindowSwitch(WindowEntity, SwitchEntity):
    """Automatic (off = like the main switch, but for this window) or sun protection
    (off = not lowered for the sun; opens again if it was lowered) of one window.
    The automatic off also ends the weather protection of the window."""

    def __init__(self, engine: ShutterEngine, window_id: str, key: str, attribute: str) -> None:
        super().__init__(engine, window_id, key)
        self._attribute = attribute

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.window, self._attribute))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.set_window_switch(self.window_id, self._attribute, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.set_window_switch(self.window_id, self._attribute, False)
