"""Switch: the automatic as a whole."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .engine import ShutterConfigEntry, ShutterEngine
from .entity import GlobalEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShutterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([AutomaticSwitch(entry.runtime_data)])


class AutomaticSwitch(GlobalEntity, SwitchEntity):
    """Main switch: off means no automatic movement at all (kept over restarts)."""

    def __init__(self, engine: ShutterEngine) -> None:
        super().__init__(engine, "automatic")

    @property
    def is_on(self) -> bool:
        return self.coordinator.automatic

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_automatic(False)
