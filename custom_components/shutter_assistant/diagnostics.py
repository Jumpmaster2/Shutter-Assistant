"""Diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_NOTIFY
from .engine import ShutterConfigEntry

# Notification services often contain the name of a person or phone.
TO_REDACT = {CONF_NOTIFY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ShutterConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (contains no secrets)."""
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "state": entry.runtime_data.diagnostics(),
    }
