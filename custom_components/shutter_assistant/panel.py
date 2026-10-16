"""Sidebar panel: an overview and all settings on one page."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER, NAME

PANEL_URL_PATH = "shutter-assistant"
PANEL_COMPONENT = "shutter-assistant-panel"
STATIC_URL = "/shutter_assistant_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
DATA_STATIC = f"{DOMAIN}_static_registered"


async def async_register_panel(hass: HomeAssistant, entry_id: str) -> None:
    """Register the panel (only when the frontend runs, not in tests).

    ``config_panel_domain`` makes the configure button of the integration open
    the panel instead of the options dialog.
    """
    if "frontend" not in hass.config.components or hass.http is None:
        return
    from homeassistant.components import frontend, panel_custom
    from homeassistant.components.http import StaticPathConfig

    if not hass.data.get(DATA_STATIC):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[DATA_STATIC] = True
    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        return
    version = await hass.async_add_executor_job(_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        module_url=f"{STATIC_URL}/panel.js?v={version}",
        sidebar_title=NAME,
        sidebar_icon="mdi:window-shutter-auto",
        require_admin=True,
        config={"entry_id": entry_id, "version": version},
        config_panel_domain=DOMAIN,
    )


def async_unregister_panel(hass: HomeAssistant) -> None:
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components import frontend

    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)


def _version() -> str:
    try:
        stamp = max(int(p.stat().st_mtime) for p in FRONTEND_DIR.iterdir())
    except (OSError, ValueError):
        LOGGER.debug("Frontend files not found")
        stamp = 0
    return str(stamp)
