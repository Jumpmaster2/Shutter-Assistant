"""Registration of the sidebar panel."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant

from custom_components.shutter_assistant.const import DOMAIN

from .conftest import make_entry, setup_entry


async def test_panel_registered_as_configure_page(hass: HomeAssistant, base_states) -> None:
    hass.config.components.add("frontend")
    hass.http = Mock(async_register_static_paths=AsyncMock())
    with (
        patch("homeassistant.components.frontend.async_panel_exists", return_value=False),
        patch("homeassistant.components.panel_custom.async_register_panel") as register,
    ):
        await setup_entry(hass, make_entry())

    kwargs = register.call_args.kwargs
    # the configure button of the integration opens the panel
    assert kwargs["config_panel_domain"] == DOMAIN
    assert kwargs["frontend_url_path"] == "shutter-assistant"
    assert kwargs["webcomponent_name"] == "shutter-assistant-panel"
    assert kwargs["require_admin"] is True
    assert kwargs["sidebar_title"] == "Shutter Assistant"
    assert kwargs["module_url"].startswith("/shutter_assistant_static/panel.js?v=")
    static = hass.http.async_register_static_paths.call_args.args[0][0]
    assert static.url_path == "/shutter_assistant_static"
    assert (Path(static.path) / "panel.js").is_file()
    assert (Path(static.path) / "labels.js").is_file()


async def test_no_panel_without_frontend(hass: HomeAssistant, base_states) -> None:
    with patch("homeassistant.components.panel_custom.async_register_panel") as register:
        await setup_entry(hass, make_entry())
    register.assert_not_called()
