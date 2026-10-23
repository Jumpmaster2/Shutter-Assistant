"""Shutter Assistant: sun protection, evening, ventilation and vacation for covers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SHOW_PANEL, DEFAULTS, DOMAIN, PLATFORMS, STORAGE_VERSION
from .engine import ShutterConfigEntry, ShutterEngine
from .entity import global_device_info
from .panel import async_register_panel, async_set_card_resource, async_unregister_panel
from .services import async_register_services
from .websocket import async_register_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services (they work on the loaded entry)."""
    async_register_services(hass)
    return True


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
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        # do not leave listeners and timers behind
        await engine.async_shutdown()
        raise
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    async_register_websocket(hass)
    show = bool(entry.options.get(CONF_SHOW_PANEL, DEFAULTS[CONF_SHOW_PANEL]))
    await async_register_panel(hass, entry.entry_id, show)
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
    """Delete the stored state, the panel and the repair issues when the integration is removed."""
    async_unregister_panel(hass)
    await async_set_card_resource(hass, None)
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
