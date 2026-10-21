"""Services: move windows, start or end an override, resume the automatic.

The services act on the covers of configured windows (no cover = all windows).
They start no override; moves by service are remembered like the automatic's
own movements.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .engine import ShutterEngine, Window

ATTR_ACTION = "action"
ATTR_POSITION = "position"
ATTR_DURATION = "duration"
ACTIONS = ["open", "close", "evening", "sun_protection", "ventilation", "position"]

COVERS = {vol.Optional(ATTR_ENTITY_ID): cv.entity_ids}
MOVE_SCHEMA = vol.Schema(
    {
        **COVERS,
        vol.Required(ATTR_ACTION): vol.In(ACTIONS),
        vol.Optional(ATTR_POSITION): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)
OVERRIDE_SCHEMA = vol.Schema(
    {**COVERS, vol.Optional(ATTR_DURATION): vol.All(vol.Coerce(float), vol.Range(min=0))}
)
COVERS_SCHEMA = vol.Schema(COVERS)


def _engine(hass: HomeAssistant) -> ShutterEngine:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise ServiceValidationError(
        translation_domain=DOMAIN, translation_key="not_loaded", translation_placeholders={}
    )


def _windows(hass: HomeAssistant, call: ServiceCall) -> tuple[ShutterEngine, list[Window]]:
    """The windows of the given covers (or of their own entities), all without any."""
    engine = _engine(hass)
    ids = call.data.get(ATTR_ENTITY_ID) or []
    if not ids:
        return engine, list(engine.windows.values())
    registry = er.async_get(hass)
    found: list[Window] = []
    for entity_id in ids:
        win = engine.window_by_cover(entity_id)
        if win is None and (entry := registry.async_get(entity_id)) is not None:
            # also an entity of the window itself (status, switches, ...)
            win = engine.windows.get(entry.config_subentry_id or "")
        if win is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_cover",
                translation_placeholders={"entity_id": entity_id},
            )
        if win not in found:
            found.append(win)
    return engine, found


@callback
def async_register_services(hass: HomeAssistant) -> None:
    @callback
    def move(call: ServiceCall) -> None:
        action = call.data[ATTR_ACTION]
        position = call.data.get(ATTR_POSITION)
        if action == "position" and position is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="position_required"
            )
        engine, windows = _windows(hass, call)
        for win in windows:
            engine.service_move(win.window_id, action, position)

    @callback
    def start_override(call: ServiceCall) -> None:
        engine, windows = _windows(hass, call)
        for win in windows:
            engine.start_override(win.window_id, call.data.get(ATTR_DURATION))

    @callback
    def end_override(call: ServiceCall) -> None:
        engine, windows = _windows(hass, call)
        for win in windows:
            engine.end_override(win.window_id)

    @callback
    def resume(call: ServiceCall) -> None:
        engine, windows = _windows(hass, call)
        for win in windows:
            engine.resume(win.window_id)

    hass.services.async_register(DOMAIN, "move", move, schema=MOVE_SCHEMA)
    hass.services.async_register(DOMAIN, "start_override", start_override, schema=OVERRIDE_SCHEMA)
    hass.services.async_register(DOMAIN, "end_override", end_override, schema=COVERS_SCHEMA)
    hass.services.async_register(DOMAIN, "resume", resume, schema=COVERS_SCHEMA)
