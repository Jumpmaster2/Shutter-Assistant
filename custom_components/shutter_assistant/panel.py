"""Sidebar panel (overview and all settings) and the dashboard card."""

from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER, NAME

PANEL_URL_PATH = "shutter-assistant"
PANEL_COMPONENT = "shutter-assistant-panel"
STATIC_URL = "/shutter_assistant_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
DATA_STATIC = f"{DOMAIN}_static_registered"
DATA_SIDEBAR = f"{DOMAIN}_panel_in_sidebar"
# url of the dashboard card module (loaded on every dashboard, for every user)
DATA_CARD = f"{DOMAIN}_card_url"
CARD_PATH = f"{STATIC_URL}/card.js"


async def async_register_panel(hass: HomeAssistant, entry_id: str, sidebar: bool = True) -> None:
    """Register the panel (only when the frontend runs, not in tests).

    ``config_panel_domain`` makes the configure button of the integration open
    the panel instead of the options dialog. Without ``sidebar`` the panel has
    no entry in the sidebar but stays reachable from the integration page.
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
    version = await hass.async_add_executor_job(_version)
    card = f"{CARD_PATH}?v={version}"
    if hass.data.get(DATA_CARD) != card:
        if old := hass.data.get(DATA_CARD):
            frontend.remove_extra_js_url(hass, old)
        frontend.add_extra_js_url(hass, card)
        hass.data[DATA_CARD] = card
        await async_set_card_resource(hass, card)
    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        if hass.data.get(DATA_SIDEBAR) == sidebar:
            return
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        module_url=f"{STATIC_URL}/panel.js?v={version}",
        sidebar_title=NAME if sidebar else None,
        sidebar_icon="mdi:window-shutter-auto" if sidebar else None,
        require_admin=True,
        config={"entry_id": entry_id, "version": version},
        config_panel_domain=DOMAIN,
    )
    hass.data[DATA_SIDEBAR] = sidebar


def async_unregister_panel(hass: HomeAssistant) -> None:
    if "frontend" not in hass.config.components:
        return
    from homeassistant.components import frontend

    if frontend.async_panel_exists(hass, PANEL_URL_PATH):
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    hass.data.pop(DATA_SIDEBAR, None)
    if card := hass.data.pop(DATA_CARD, None):
        frontend.remove_extra_js_url(hass, card)


def _version() -> str:
    try:
        stamp = max(int(p.stat().st_mtime) for p in FRONTEND_DIR.iterdir())
    except (OSError, ValueError):
        LOGGER.debug("Frontend files not found")
        stamp = 0
    return str(stamp)


async def async_set_card_resource(hass: HomeAssistant, url: str | None) -> None:
    """Keep the card and the tiles as a dashboard resource (None removes it).

    The companion app does not always load the extra modules of the start page,
    then the tiles show a configuration error. Its resources it loads with every
    dashboard. Only for resources managed in the UI (storage mode).
    """
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
    except ImportError:
        return
    data = hass.data.get(LOVELACE_DATA)
    if data is None or getattr(data, "resource_mode", None) != "storage":
        return
    resources = data.resources
    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        ours = [i for i in resources.async_items() if i.get("url", "").split("?")[0] == CARD_PATH]
        for item in ours[1:] if url else ours:
            await resources.async_delete_item(item["id"])
        if not url:
            return
        if not ours:
            await resources.async_create_item({"res_type": "module", "url": url})
        elif ours[0].get("url") != url:
            await resources.async_update_item(ours[0]["id"], {"res_type": "module", "url": url})
    except Exception:  # the card is optional, the control must not fail
        LOGGER.warning("Could not register the dashboard card as a dashboard resource")
