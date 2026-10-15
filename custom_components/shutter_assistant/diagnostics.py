"""Diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .engine import ShutterConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ShutterConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (contains no secrets)."""
    return {"entry": entry.as_dict(), "state": entry.runtime_data.diagnostics()}
