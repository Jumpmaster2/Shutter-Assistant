"""WebSocket API for the panel: read the configuration, change options, groups and windows."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigSubentry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    Selector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TimeSelector,
)

from .config_flow import (
    _advanced_schema,
    _evening_schema,
    _general_schema,
    _group_schema,
    _notify_services,
    _number,
    _override_schema,
    _protection_schema,
    _startup_schema,
    _summer_schema,
    _time_key,
    _vacation_schema,
    _validate_evening,
    _validate_group,
    _validate_vacation,
    cover_in_use,
    validate_general,
    validate_morning,
    window_basics_fields,
    window_conditions_fields,
    window_evening_fields,
    window_morning_fields,
    window_morning_mode_fields,
    window_override_fields,
    window_protection_fields,
    window_sun_fields,
    window_ventilation_fields,
)
from .const import (
    CONF_COOLING_ENTITY,
    CONF_COVER,
    CONF_EVENING_CUSTOM,
    CONF_EVENING_EARLIEST,
    CONF_EVENING_ELEVATION,
    CONF_EVENING_LATEST,
    CONF_FROST_POSITION,
    CONF_GROUP,
    CONF_HEATING_ENTITY,
    CONF_HOUSE_AZIMUTH,
    CONF_HOUSE_DEPTH,
    CONF_HOUSE_WIDTH,
    CONF_MORNING,
    CONF_MORNING_MODE,
    CONF_MORNING_TRIGGER,
    CONF_NAME,
    CONF_OPEN_BLOCK,
    CONF_OUTDOOR_TEMP,
    CONF_RAIN_ENTITY,
    CONF_RAIN_POSITION,
    CONF_ROOM_ENTITY,
    CONF_WALL,
    CONF_WALL_POSITION,
    CONF_WEATHER,
    CONF_WIND_ENTITY,
    CONF_WIND_POSITION,
    CONF_WINDOW_EXCEPTION,
    CONF_WORKDAY,
    DEFAULTS,
    DOMAIN,
    GROUP_DEFAULTS,
    SENSOR_KINDS,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    WALLS,
    WINDOW_DEFAULTS,
)
from .logic.morning import MODES
from .units import defaults, interval_unit, temperature_unit, window_defaults

DATA_WS = f"{DOMAIN}_ws_registered"

# entities of the integration (unique id suffix) for the panel
GLOBAL_ENTITIES = {
    "automatic": "switch",
    "summer_day": "binary_sensor",
    "evening_mode": "binary_sensor",
    "forecast_max": "sensor",
    "wind_protection": "binary_sensor",
    "rain_protection": "binary_sensor",
    "frost_protection": "binary_sensor",
}
WINDOW_ENTITIES = {
    "status": "sensor",
    "last_reason": "sensor",
    "override": "binary_sensor",
    "sun_condition": "binary_sensor",
    "sun_protection_today": "binary_sensor",
    "evening_closed": "binary_sensor",
    "next_action": "sensor",
    "window_automatic": "switch",
    "window_sun_protection": "switch",
}

# Settings only the panel has: the house in the sun compass (shown when all
# three are set) and the wall of a group or window.
HOUSE_FIELDS: dict[Any, Any] = {
    vol.Optional(CONF_HOUSE_AZIMUTH): _number(0, 360, 1, "°"),
    vol.Optional(CONF_HOUSE_WIDTH): _number(1, 500, 0.1, "m"),
    vol.Optional(CONF_HOUSE_DEPTH): _number(1, 500, 0.1, "m"),
}
WALL_FIELD: dict[Any, Any] = {
    vol.Optional(CONF_WALL): SelectSelector(
        SelectSelectorConfig(options=list(WALLS), mode=SelectSelectorMode.DROPDOWN)
    )
}
WINDOW_WALL_FIELDS: dict[Any, Any] = {
    **WALL_FIELD,
    vol.Optional(CONF_WALL_POSITION): _number(1, 50, 1),
}

OPTION_KEYS = {
    *DEFAULTS,
    CONF_OUTDOOR_TEMP,
    CONF_WEATHER,
    CONF_WORKDAY,
    CONF_HEATING_ENTITY,
    CONF_WIND_ENTITY,
    CONF_RAIN_ENTITY,
    CONF_HOUSE_AZIMUTH,
    CONF_HOUSE_WIDTH,
    CONF_HOUSE_DEPTH,
}
WINDOW_KEYS = {
    *WINDOW_DEFAULTS,
    CONF_NAME,
    CONF_COVER,
    CONF_GROUP,
    CONF_OPEN_BLOCK,
    CONF_WINDOW_EXCEPTION,
    CONF_MORNING_TRIGGER,
    CONF_ROOM_ENTITY,
    CONF_COOLING_ENTITY,
    CONF_EVENING_EARLIEST,
    CONF_EVENING_ELEVATION,
    CONF_EVENING_LATEST,
    CONF_WALL,
    CONF_WALL_POSITION,
    CONF_WIND_POSITION,
    CONF_RAIN_POSITION,
    CONF_FROST_POSITION,
}
GROUP_KEYS = {*GROUP_DEFAULTS, CONF_NAME, CONF_WALL}


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    if hass.data.get(DATA_WS):
        return
    hass.data[DATA_WS] = True
    websocket_api.async_register_command(hass, ws_config)
    websocket_api.async_register_command(hass, ws_save_options)
    websocket_api.async_register_command(hass, ws_save_subentry)
    websocket_api.async_register_command(hass, ws_delete_subentry)
    websocket_api.async_register_command(hass, ws_end_override)


def _entry(hass: HomeAssistant) -> ConfigEntry | None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _empty(value: Any) -> bool:
    return value is None or value == ""


# ---------------------------------------------------------------- fields


def _key(marker: Any) -> str:
    return str(marker.schema)


def _check(
    fields: dict[Any, Any], values: dict[str, Any], require: bool = True
) -> tuple[dict[str, Any], dict[str, str]]:
    """Check the values with the selectors of the dialogs, field by field."""
    result: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for marker, validator in fields.items():
        key = _key(marker)
        value = values.get(key)
        if _empty(value):
            if require and isinstance(marker, vol.Required):
                errors[key] = "required"
            continue
        try:
            checked = validator(value)
        except (vol.Invalid, ValueError, TypeError):
            errors[key] = "invalid_value"
            continue
        if isinstance(validator, TimeSelector):
            checked = _time_key(checked)
        result[key] = checked
    return result, errors


def _option_fields(hass: HomeAssistant, values: dict[str, Any]) -> dict[Any, Any]:
    fields: dict[Any, Any] = {}
    for schema in (
        _general_schema(hass, values),
        _override_schema(values),
        _summer_schema(values, temperature_unit(hass)),
        _evening_schema(values),
        _vacation_schema(values),
        _protection_schema(values, temperature_unit(hass)),
        _startup_schema(values),
        _advanced_schema(values),
    ):
        fields.update(schema.schema)
    fields.update(HOUSE_FIELDS)
    return fields


def _groups(entry: ConfigEntry) -> dict[str, ConfigSubentry]:
    return {
        sub_id: sub
        for sub_id, sub in entry.subentries.items()
        if sub.subentry_type == SUBENTRY_GROUP
    }


def _window_fields(
    entry: ConfigEntry, values: dict[str, Any], group_data: dict[str, Any] | None, unit: str
) -> dict[Any, Any]:
    """The fields that apply to a window with these values."""
    groups = {sub_id: sub.title for sub_id, sub in _groups(entry).items()}
    fields = {**window_basics_fields(values, groups), **WINDOW_WALL_FIELDS}
    if group_data is not None:
        fields.update(window_sun_fields(values, group_data, unit))
    options = dict(entry.options)
    for build in (
        window_override_fields(values),
        window_conditions_fields(values),
        window_evening_fields(values, options),
        window_ventilation_fields(values),
        window_protection_fields(values),
        window_morning_fields(values),
    ):
        fields.update(build)
    if values.get(CONF_MORNING):
        fields.update(window_morning_mode_fields(str(values.get(CONF_MORNING_MODE)), values))
    return fields


def _all_window_fields(entry: ConfigEntry, values: dict[str, Any], unit: str) -> dict[Any, Any]:
    """Every window field, also the ones that do not apply right now."""
    all_sensors = {key: ["sensor.any"] for key in SENSOR_KINDS.values()}
    fields = _window_fields(entry, {**values, CONF_MORNING: False}, all_sensors, unit)
    for mode in MODES:
        fields.update(window_morning_mode_fields(mode, values))
    return fields


def _field_info(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Selector of every field (type, range, unit, domains) for the panel."""
    unit = temperature_unit(hass)
    fields: dict[Any, Any] = {
        **_option_fields(hass, defaults(unit)),
        **_group_schema({}).schema,
        **WALL_FIELD,
        **_all_window_fields(entry, window_defaults(unit), unit),
    }
    return {
        _key(marker): validator.serialize()["selector"]
        for marker, validator in fields.items()
        if isinstance(validator, Selector)
    }


# ---------------------------------------------------------------- payload


def config_payload(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    registry = er.async_get(hass)
    unit = temperature_unit(hass)

    def entity_ids(prefix: str, keys: dict[str, str]) -> dict[str, str]:
        found = {}
        for key, domain in keys.items():
            if entity_id := registry.async_get_entity_id(domain, DOMAIN, f"{prefix}_{key}"):
                found[key] = entity_id
        return found

    def item(sub_id: str, sub: ConfigSubentry) -> dict[str, Any]:
        return {"id": sub_id, "title": sub.title, "data": dict(sub.data)}

    return {
        "entry_id": entry.entry_id,
        "loaded": entry.state is ConfigEntryState.LOADED,
        "options": {**defaults(unit), **entry.options},
        "groups": [item(sub_id, sub) for sub_id, sub in _groups(entry).items()],
        "windows": [
            {**item(sub_id, sub), "entities": entity_ids(sub_id, WINDOW_ENTITIES)}
            for sub_id, sub in entry.subentries.items()
            if sub.subentry_type == SUBENTRY_WINDOW
        ],
        "entities": entity_ids(entry.entry_id, GLOBAL_ENTITIES),
        "notify_services": _notify_services(hass),
        "defaults": {"window": window_defaults(unit), "group": GROUP_DEFAULTS},
        "fields": _field_info(hass, entry),
        "temperature_unit": unit,
        "interval_unit": interval_unit(unit),
    }


# ---------------------------------------------------------------- commands


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/config"})
@websocket_api.require_admin
@callback
def ws_config(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Shutter Assistant is not set up")
        return
    connection.send_result(msg["id"], config_payload(hass, entry))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/save_options", vol.Required("options"): dict}
)
@websocket_api.require_admin
@callback
def ws_save_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Shutter Assistant is not set up")
        return
    if unknown := sorted(set(msg["options"]) - OPTION_KEYS):
        connection.send_error(msg["id"], "invalid", f"unknown option {', '.join(unknown)}")
        return
    values = {**defaults(temperature_unit(hass)), **entry.options, **msg["options"]}
    checked, errors = _check(_option_fields(hass, values), values)
    if not errors:
        errors = {
            **validate_general(hass, checked),
            **_validate_evening(checked),
            **_validate_vacation(checked),
        }
    if errors:
        connection.send_result(msg["id"], {"errors": errors})
        return
    # cleared optional entities are left out of ``checked``
    others = {k: v for k, v in entry.options.items() if k not in OPTION_KEYS}
    hass.config_entries.async_update_entry(entry, options={**others, **checked})
    connection.send_result(msg["id"], {"config": config_payload(hass, entry)})


def _save_group(
    hass: HomeAssistant,
    entry: ConfigEntry,
    sub_id: str | None,
    current: dict[str, Any],
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    values = {**GROUP_DEFAULTS, **current, **incoming}
    values[CONF_NAME] = str(values.get(CONF_NAME) or "").strip()
    checked, errors = _check({**_group_schema(values).schema, **WALL_FIELD}, values)
    if errors:
        if errors.get(CONF_NAME) == "required":
            errors[CONF_NAME] = "name_required"
        return {}, errors
    return checked, _validate_group(checked, hass)


def _save_window(
    hass: HomeAssistant,
    entry: ConfigEntry,
    sub_id: str | None,
    current: dict[str, Any],
    incoming: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    unit = temperature_unit(hass)
    values = {**window_defaults(unit), **current, **incoming}
    for key in (CONF_EVENING_EARLIEST, CONF_EVENING_ELEVATION, CONF_EVENING_LATEST):
        if _empty(values.get(key)):
            values[key] = entry.options.get(key, DEFAULTS[key])
    values[CONF_NAME] = str(values.get(CONF_NAME) or "").strip()
    values = {k: v for k, v in values.items() if not _empty(v)}
    group = _groups(entry).get(str(values.get(CONF_GROUP, "")))
    group_data = {**GROUP_DEFAULTS, **group.data} if group else None
    fields = _window_fields(entry, values, group_data, unit)
    checked, errors = _check(fields, values)
    # fields that do not apply right now keep their value, but it must be valid
    shown = {_key(marker) for marker in fields}
    hidden = {
        m: v for m, v in _all_window_fields(entry, values, unit).items() if _key(m) not in shown
    }
    hidden_checked, hidden_errors = _check(hidden, values, require=False)
    checked.update(hidden_checked)
    errors.update(hidden_errors)
    if errors:
        if errors.get(CONF_NAME) == "required":
            errors[CONF_NAME] = "name_required"
        return {}, errors
    data = {**values, **checked, CONF_NAME: str(checked[CONF_NAME]).strip()}
    if CONF_GROUP not in checked:
        data.pop(CONF_GROUP, None)
    if data.get(CONF_EVENING_CUSTOM):
        errors.update(_validate_evening(data))
    errors.update(validate_morning(data, group_data))
    if cover_in_use(entry, data.get(CONF_COVER), sub_id) is not None:
        errors[CONF_COVER] = "cover_in_use"
    return data, errors


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_subentry",
        vol.Optional("subentry_id"): str,
        vol.Required("subentry_type"): vol.In([SUBENTRY_GROUP, SUBENTRY_WINDOW]),
        vol.Required("data"): dict,
    }
)
@websocket_api.require_admin
@callback
def ws_save_subentry(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Shutter Assistant is not set up")
        return
    subentry_type = msg["subentry_type"]
    subentry: ConfigSubentry | None = None
    if sub_id := msg.get("subentry_id"):
        subentry = entry.subentries.get(sub_id)
        if subentry is None or subentry.subentry_type != subentry_type:
            connection.send_error(msg["id"], "not_found", "sub item not found")
            return
    allowed = GROUP_KEYS if subentry_type == SUBENTRY_GROUP else WINDOW_KEYS
    incoming = {k: v for k, v in msg["data"].items() if k in allowed}
    current = dict(subentry.data) if subentry else {}
    save = _save_group if subentry_type == SUBENTRY_GROUP else _save_window
    data, errors = save(hass, entry, sub_id, current, incoming)
    if errors:
        connection.send_result(msg["id"], {"errors": errors})
        return
    title = str(data[CONF_NAME])
    if subentry is not None:
        hass.config_entries.async_update_subentry(entry, subentry, data=data, title=title)
    else:
        subentry = ConfigSubentry(
            data=MappingProxyType(data), subentry_type=subentry_type, title=title, unique_id=None
        )
        hass.config_entries.async_add_subentry(entry, subentry)
    connection.send_result(
        msg["id"],
        {"subentry_id": subentry.subentry_id, "config": config_payload(hass, entry)},
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/delete_subentry", vol.Required("subentry_id"): str}
)
@websocket_api.require_admin
@callback
def ws_delete_subentry(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    entry = _entry(hass)
    if entry is None or msg["subentry_id"] not in entry.subentries:
        connection.send_error(msg["id"], "not_found", "sub item not found")
        return
    hass.config_entries.async_remove_subentry(entry, msg["subentry_id"])
    connection.send_result(msg["id"], {"config": config_payload(hass, entry)})


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/end_override", vol.Required("window_id"): str}
)
@websocket_api.require_admin
@callback
def ws_end_override(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """End the manual override of a window right away."""
    entry = _entry(hass)
    engine = getattr(entry, "runtime_data", None) if entry else None
    if engine is None or msg["window_id"] not in engine.windows:
        connection.send_error(msg["id"], "not_found", "window not found")
        return
    connection.send_result(msg["id"], {"ended": engine.end_override(msg["window_id"])})
