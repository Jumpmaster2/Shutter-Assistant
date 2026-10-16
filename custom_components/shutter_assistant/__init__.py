"""Shutter Assistant: sun protection, evening, ventilation and vacation for covers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store

from .const import DOMAIN, PLATFORMS, STORAGE_VERSION
from .engine import ShutterConfigEntry, ShutterEngine
from .entity import global_device_info
from .panel import async_register_panel, async_unregister_panel
from .websocket import async_register_websocket


async def async_setup_entry(hass: HomeAssistant, entry: ShutterConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    engine = ShutterEngine(hass, entry)
    # Create the main device first so window devices can point to it by id.
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **global_device_info(entry.entry_id)
    )
    engine.global_device_id = device.id
    await engine.async_setup()
    entry.runtime_data = engine
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    async_register_websocket(hass)
    await async_register_panel(hass, entry.entry_id)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ShutterConfigEntry) -> None:
    """Options, groups or windows changed: reload."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ShutterConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ShutterConfigEntry) -> None:
    """Delete the stored state when the integration is removed."""
    async_unregister_panel(hass)
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
