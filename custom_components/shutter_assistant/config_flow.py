"""Config flow, options flow and the subentry flows for groups and windows."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)

from .const import (
    ACTIVE_STATES_DEFAULT,
    CONF_AUTO_UP,
    CONF_AZIMUTH_FROM,
    CONF_AZIMUTH_TO,
    CONF_CATCH_UP_AFTER,
    CONF_CLOSED_POSITION,
    CONF_COMMAND_INTERVAL,
    CONF_COOLING_ENTITY,
    CONF_COVER,
    CONF_DAY_CHANGE,
    CONF_EVENING_CLOSE,
    CONF_EVENING_CUSTOM,
    CONF_EVENING_EARLIEST,
    CONF_EVENING_ELEVATION,
    CONF_EVENING_LATEST,
    CONF_EVENING_POSITION,
    CONF_FOLLOW_UP_CLOSE,
    CONF_FOLLOW_UP_EARLIEST,
    CONF_FORECAST_TYPE,
    CONF_FROST_POSITION,
    CONF_FROST_THRESHOLD,
    CONF_GROUP,
    CONF_HEATING_ENTITY,
    CONF_LANGUAGE,
    CONF_LOCKOUT,
    CONF_LUX_SENSORS,
    CONF_MANUAL_AT_SUN,
    CONF_MANUAL_FOLLOW_UP,
    CONF_MANUAL_MAX,
    CONF_MANUAL_WINDOW,
    CONF_MORNING,
    CONF_MORNING_EARLIEST,
    CONF_MORNING_LATEST,
    CONF_MORNING_LUX,
    CONF_MORNING_LUX_HOLD,
    CONF_MORNING_MODE,
    CONF_MORNING_POSITION,
    CONF_MORNING_SUN_ELEVATION,
    CONF_MORNING_SUN_EVENT,
    CONF_MORNING_SUN_OFFSET,
    CONF_MORNING_SUN_POSITION,
    CONF_MORNING_TRIGGER,
    CONF_MORNING_TRIGGER_OFFSET,
    CONF_MORNING_WEEKEND,
    CONF_MORNING_WORKDAY,
    CONF_NAME,
    CONF_NIGHT_END,
    CONF_NIGHT_THRESHOLD,
    CONF_NOTIFY,
    CONF_NOTIFY_OPEN,
    CONF_OPEN_BLOCK,
    CONF_OPEN_BLOCK_FREE,
    CONF_OUTDOOR_TEMP,
    CONF_OVERRIDE_DURATION,
    CONF_OVERRIDE_IGNORE_EVENING,
    CONF_OVERRIDE_SUNRISE,
    CONF_OVERRIDE_TRIGGER,
    CONF_PROTECTION_RELEASE,
    CONF_PV_SENSORS,
    CONF_RADIATION_SENSORS,
    CONF_RAIN_ENTITY,
    CONF_RAIN_POSITION,
    CONF_RAIN_THRESHOLD,
    CONF_ROOM_ENTITY,
    CONF_ROOM_MARGIN,
    CONF_ROOM_THRESHOLD,
    CONF_SHOW_PANEL,
    CONF_STARTUP_DELAY,
    CONF_SUMMER_THRESHOLD,
    CONF_SUN_HOLD,
    CONF_SUN_POSITION,
    CONF_TEMP_HOLD,
    CONF_TEMP_THRESHOLD,
    CONF_TILT_SENSORS,
    CONF_TOLERANCE,
    CONF_TRIGGER_ACTIVE,
    CONF_TRIGGER_ENTITIES,
    CONF_TRIGGER_MAX_LOCK,
    CONF_TRIGGER_MIN_POSITION,
    CONF_TRIGGER_OFF_DELAY,
    CONF_TRIGGER_ON_DELAY,
    CONF_VAC_EVENING,
    CONF_VAC_EVENING_WINDOW,
    CONF_VAC_MORNING,
    CONF_VAC_MORNING_WINDOW,
    CONF_VAC_POS_MAX,
    CONF_VAC_POS_MIN,
    CONF_VACATION,
    CONF_VACATION_ENTITIES,
    CONF_VENT_DELAY_DAY,
    CONF_VENT_DELAY_EVENING,
    CONF_VENT_POSITION,
    CONF_VENTILATION,
    CONF_VERIFY_AFTER,
    CONF_WEATHER,
    CONF_WEATHER_PROTECTION,
    CONF_WEEKEND_DAYS,
    CONF_WIND_ENTITY,
    CONF_WIND_POSITION,
    CONF_WIND_THRESHOLD,
    CONF_WINDOW_DEBOUNCE,
    CONF_WINDOW_EXCEPTION,
    CONF_WINDOW_SENSORS,
    CONF_WINDOW_WIND_THRESHOLD,
    CONF_WORKDAY,
    DEFAULTS,
    DOMAIN,
    FORECAST_TYPES,
    FREE_STATES_DEFAULT,
    GROUP_DEFAULTS,
    KIND_LUX,
    KIND_PV,
    KIND_RADIATION,
    LANGUAGE_OPTIONS,
    NAME,
    OVERRIDE_TRIGGERS,
    SECTION_CONDITIONS,
    SECTION_EVENING,
    SECTION_OVERRIDE,
    SECTION_PROTECTION,
    SECTION_VENTILATION,
    SENSOR_KINDS,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    THRESHOLD_KEYS,
    WEEKDAYS,
    WINDOW_DEFAULTS,
)
from .logic.morning import (
    MODE_BRIGHTNESS,
    MODE_SUN,
    MODE_TIME,
    MODE_TRIGGER,
    MODES,
    SUN_ELEVATION,
    SUN_SUNRISE,
)
from .units import (
    defaults,
    interval_unit,
    temperature_range,
    temperature_unit,
    window_defaults,
)

# binary contacts and window handles (open / tilted / closed)
CONTACT_DOMAINS = ["binary_sensor", "input_boolean", "sensor"]
PROTECTION_POSITIONS = (
    CONF_WIND_POSITION,
    CONF_WINDOW_WIND_THRESHOLD,
    CONF_RAIN_POSITION,
    CONF_FROST_POSITION,
)
STATE_SUGGESTIONS = ["off", "on", "unavailable", "unknown", "standby", "idle", "paused", "playing"]
MORNING_STEPS = {
    MODE_TIME: "morning_time",
    MODE_SUN: "morning_sun",
    MODE_BRIGHTNESS: "morning_brightness",
    MODE_TRIGGER: "morning_trigger",
}


def _number(minimum: float, maximum: float, step: float, unit: str | None = None) -> NumberSelector:
    config = NumberSelectorConfig(min=minimum, max=maximum, step=step, mode=NumberSelectorMode.BOX)
    if unit:
        config["unit_of_measurement"] = unit
    return NumberSelector(config)


def _entity(domains: list[str] | None = None, multiple: bool = False) -> EntitySelector:
    config = EntitySelectorConfig(multiple=multiple)
    if domains:
        config["domain"] = domains
    return EntitySelector(config)


def _states() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=STATE_SUGGESTIONS,
            multiple=True,
            custom_value=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _choice(options: list[str], key: str, multiple: bool = False) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options, translation_key=key, mode=SelectSelectorMode.LIST, multiple=multiple
        )
    )


def _temperature(unit: str, low: float, high: float) -> NumberSelector:
    """Temperature field; the range is given in °C and converted to ``unit``."""
    minimum, maximum = temperature_range(unit, low, high)
    return _number(minimum, maximum, 0.5, unit)


def _opt(key: str, values: dict[str, Any]) -> vol.Optional:
    """Optional field that can be cleared again."""
    return vol.Optional(key, description={"suggested_value": values.get(key)})


def _req(key: str, values: dict[str, Any], defaults: dict[str, Any] | None = None) -> vol.Required:
    defaults = defaults if defaults is not None else DEFAULTS
    return vol.Required(key, default=values.get(key, defaults.get(key)))


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    """Drop cleared optional values."""
    return {k: v for k, v in data.items() if v not in (None, "")}


def _notify_services(hass: HomeAssistant) -> list[str]:
    return sorted(f"notify.{name}" for name in hass.services.async_services_for_domain("notify"))


def _single_entity(hass: HomeAssistant, domain: str) -> str | None:
    """The entity of a domain if there is exactly one (suggestion for the setup)."""
    ids = hass.states.async_entity_ids(domain)
    return ids[0] if len(ids) == 1 else None


def _not_numeric(hass: HomeAssistant, entity_id: str | None) -> bool:
    """The entity reports a value that is not a number (unavailable is fine)."""
    state = hass.states.get(entity_id) if entity_id else None
    if state is None or state.state in ("unavailable", "unknown"):
        return False
    try:
        float(state.state)
    except ValueError:
        return True
    return False


def validate_general(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Temperature source, a numeric outdoor sensor and only notification services."""
    errors: dict[str, str] = {}
    outdoor = data.get(CONF_OUTDOOR_TEMP)
    if not outdoor and not data.get(CONF_WEATHER):
        errors[CONF_OUTDOOR_TEMP] = "need_temperature_source"
    elif _not_numeric(hass, outdoor):
        errors[CONF_OUTDOOR_TEMP] = "not_numeric"
    services = data.get(CONF_NOTIFY) or []
    if any(not str(s).startswith("notify.") or str(s) == "notify." for s in services):
        errors[CONF_NOTIFY] = "invalid_notify_service"
    return errors


def _time_key(value: Any) -> str:
    text = str(value or "")
    return text if text.count(":") == 2 else f"{text}:00"


# ---------------------------------------------------------------- global schemas


def _general_schema(hass: HomeAssistant, v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _opt(CONF_OUTDOOR_TEMP, v): _entity(["sensor"]),
            _opt(CONF_WEATHER, v): _entity(["weather"]),
            _req(CONF_LANGUAGE, v): _choice(LANGUAGE_OPTIONS, "language"),
            vol.Optional(CONF_NOTIFY, default=v.get(CONF_NOTIFY, [])): SelectSelector(
                SelectSelectorConfig(
                    options=_notify_services(hass),
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            _opt(CONF_WORKDAY, v): _entity(["binary_sensor"]),
            vol.Optional(
                CONF_WEEKEND_DAYS, default=v.get(CONF_WEEKEND_DAYS, DEFAULTS[CONF_WEEKEND_DAYS])
            ): _choice(WEEKDAYS, "weekday", multiple=True),
        }
    )


def _summer_schema(v: dict[str, Any], unit: str) -> vol.Schema:
    temps = defaults(unit)
    return vol.Schema(
        {
            _req(CONF_SUMMER_THRESHOLD, v, temps): _temperature(unit, 0, 45),
            _req(CONF_NIGHT_THRESHOLD, v, temps): _temperature(unit, -10, 30),
            _opt(CONF_HEATING_ENTITY, v): _entity(["binary_sensor", "input_boolean", "switch"]),
            _req(CONF_DAY_CHANGE, v): TimeSelector(),
            _req(CONF_FORECAST_TYPE, v): _choice(FORECAST_TYPES, "forecast_type"),
        }
    )


def _advanced_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _req(CONF_WINDOW_DEBOUNCE, v): _number(0, 120, 1, "s"),
            _req(CONF_COMMAND_INTERVAL, v): _number(0, 10, 0.5, "s"),
            _req(CONF_VERIFY_AFTER, v): _number(0, 600, 1, "s"),
            _req(CONF_SHOW_PANEL, v): BooleanSelector(),
        }
    )


def _protection_schema(v: dict[str, Any], unit: str) -> vol.Schema:
    temps = defaults(unit)
    return vol.Schema(
        {
            _opt(CONF_WIND_ENTITY, v): _entity(["sensor"]),
            _req(CONF_WIND_THRESHOLD, v): _number(0, 300, 0.5),
            _opt(CONF_RAIN_ENTITY, v): _entity(["binary_sensor", "sensor", "input_boolean"]),
            _req(CONF_RAIN_THRESHOLD, v): _number(0, 100, 0.1),
            _req(CONF_FROST_THRESHOLD, v, temps): _temperature(unit, -15, 10),
            _req(CONF_PROTECTION_RELEASE, v): _number(0, 240, 1, "min"),
        }
    )


def _evening_fields(v: dict[str, Any], defaults: dict[str, Any]) -> dict[Any, Any]:
    return {
        _req(CONF_EVENING_EARLIEST, v, defaults): TimeSelector(),
        _req(CONF_EVENING_ELEVATION, v, defaults): _number(-18, 10, 0.5, "°"),
        _req(CONF_EVENING_LATEST, v, defaults): TimeSelector(),
    }


def _evening_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            **_evening_fields(v, DEFAULTS),
            _req(CONF_NIGHT_END, v): TimeSelector(),
            _req(CONF_FOLLOW_UP_EARLIEST, v): TimeSelector(),
        }
    )


def _vacation_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_VACATION_ENTITIES, default=v.get(CONF_VACATION_ENTITIES, [])
            ): _entity(["input_boolean", "binary_sensor", "switch", "calendar", "schedule"], True),
            _req(CONF_VAC_MORNING, v): TimeSelector(),
            _req(CONF_VAC_MORNING_WINDOW, v): _number(0, 240, 1, "min"),
            _req(CONF_VAC_POS_MIN, v): _number(0, 100, 1, "%"),
            _req(CONF_VAC_POS_MAX, v): _number(0, 100, 1, "%"),
            _req(CONF_VAC_EVENING, v): TimeSelector(),
            _req(CONF_VAC_EVENING_WINDOW, v): _number(0, 240, 1, "min"),
        }
    )


def _override_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {_req(CONF_OVERRIDE_TRIGGER, v): _choice(OVERRIDE_TRIGGERS, "override_trigger")}
    )


def _startup_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _req(CONF_STARTUP_DELAY, v): _number(0, 60, 1, "min"),
            _req(CONF_CATCH_UP_AFTER, v): TimeSelector(),
        }
    )


def _validate_evening(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    earliest = _time_key(data.get(CONF_EVENING_EARLIEST))
    latest = _time_key(data.get(CONF_EVENING_LATEST))
    if earliest > latest:
        errors[CONF_EVENING_LATEST] = "latest_before_earliest"
    if CONF_NIGHT_END in data and _time_key(data[CONF_NIGHT_END]) >= earliest:
        errors[CONF_NIGHT_END] = "night_end_after_evening"
    return errors


def _validate_vacation(data: dict[str, Any]) -> dict[str, str]:
    if float(data.get(CONF_VAC_POS_MIN, 0)) > float(data.get(CONF_VAC_POS_MAX, 100)):
        return {CONF_VAC_POS_MAX: "min_above_max"}
    return {}


# ---------------------------------------------------------------- config flow


class ShutterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup: sensors, summer day and evening mode."""

    VERSION = 1

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ShutterOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_GROUP: GroupSubentryFlow, SUBENTRY_WINDOW: WindowSubentryFlow}

    @property
    def _unit(self) -> str:
        return temperature_unit(self.hass)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_general(self.hass, user_input)
            if not errors:
                self._options.update(_clean(user_input))
                return await self.async_step_summer()
        # suggest the only weather and workday entity
        values = user_input or {
            **DEFAULTS,
            CONF_WEATHER: _single_entity(self.hass, "weather"),
        }
        return self.async_show_form(
            step_id="user", data_schema=_general_schema(self.hass, values), errors=errors
        )

    async def async_step_summer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options.update(_clean(user_input))
            return await self.async_step_evening()
        return self.async_show_form(
            step_id="summer", data_schema=_summer_schema(defaults(self._unit), self._unit)
        )

    async def async_step_evening(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_evening(user_input)
            if not errors:
                options = {**defaults(self._unit), **self._options, **user_input}
                return self.async_create_entry(title=NAME, data={}, options=options)
        return self.async_show_form(
            step_id="evening", data_schema=_evening_schema(user_input or {}), errors=errors
        )


# ---------------------------------------------------------------- options flow


class ShutterOptionsFlow(OptionsFlow):
    """All global settings, grouped in a menu."""

    @property
    def _unit(self) -> str:
        return temperature_unit(self.hass)

    @property
    def _values(self) -> dict[str, Any]:
        return {**defaults(self._unit), **self.config_entry.options}

    def _save(self, updates: dict[str, Any], remove: tuple[str, ...] = ()) -> ConfigFlowResult:
        options = {**self.config_entry.options}
        for key in remove:
            options.pop(key, None)
        options.update(updates)
        return self.async_create_entry(data=options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "general",
                "override",
                "summer",
                "evening",
                "vacation",
                "protection",
                "startup",
                "advanced",
            ],
        )

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = validate_general(self.hass, user_input)
            if not errors:
                return self._save(
                    _clean(user_input), remove=(CONF_OUTDOOR_TEMP, CONF_WEATHER, CONF_WORKDAY)
                )
        return self.async_show_form(
            step_id="general",
            data_schema=_general_schema(self.hass, user_input or self._values),
            errors=errors,
        )

    async def async_step_summer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean(user_input), remove=(CONF_HEATING_ENTITY,))
        return self.async_show_form(
            step_id="summer", data_schema=_summer_schema(self._values, self._unit)
        )

    async def async_step_evening(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_evening(user_input)
            if not errors:
                return self._save(user_input)
        return self.async_show_form(
            step_id="evening",
            data_schema=_evening_schema(user_input or self._values),
            errors=errors,
        )

    async def async_step_vacation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_vacation(user_input)
            if not errors:
                return self._save(user_input)
        return self.async_show_form(
            step_id="vacation",
            data_schema=_vacation_schema(user_input or self._values),
            errors=errors,
        )

    async def async_step_protection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean(user_input), remove=(CONF_WIND_ENTITY, CONF_RAIN_ENTITY))
        return self.async_show_form(
            step_id="protection", data_schema=_protection_schema(self._values, self._unit)
        )

    async def async_step_override(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(step_id="override", data_schema=_override_schema(self._values))

    async def async_step_startup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(step_id="startup", data_schema=_startup_schema(self._values))

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema(self._values))


# ---------------------------------------------------------------- group subentry


def _group_schema(v: dict[str, Any]) -> vol.Schema:
    def sensors(key: str) -> tuple[vol.Optional, EntitySelector]:
        return vol.Optional(key, default=v.get(key, [])), _entity(["sensor"], True)

    fields: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=v.get(CONF_NAME, "")): TextSelector(),
        _req(CONF_AZIMUTH_FROM, v, GROUP_DEFAULTS): _number(0, 360, 1, "°"),
        _req(CONF_AZIMUTH_TO, v, GROUP_DEFAULTS): _number(0, 360, 1, "°"),
    }
    for key in (CONF_RADIATION_SENSORS, CONF_PV_SENSORS, CONF_LUX_SENSORS):
        field, selector = sensors(key)
        fields[field] = selector
    return vol.Schema(fields)


def _validate_group(data: dict[str, Any], hass: HomeAssistant | None = None) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not str(data.get(CONF_NAME, "")).strip():
        errors[CONF_NAME] = "name_required"
    if float(data.get(CONF_AZIMUTH_FROM, 0)) == float(data.get(CONF_AZIMUTH_TO, 0)):
        errors[CONF_AZIMUTH_TO] = "azimuth_equal"
    if hass is not None:
        for key in SENSOR_KINDS.values():
            if any(_not_numeric(hass, e) for e in data.get(key) or []):
                errors[key] = "not_numeric"
    return errors


class GroupSubentryFlow(ConfigSubentryFlow):
    """Add or change a group (direction of the sun with its sensors)."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_group(user_input, self.hass)
            if not errors:
                data = {**user_input, CONF_NAME: str(user_input[CONF_NAME]).strip()}
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="user", data_schema=_group_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        values = {CONF_NAME: subentry.title, **subentry.data}
        if user_input is not None:
            errors = _validate_group(user_input, self.hass)
            if not errors:
                # keep values only the panel sets (wall of the house)
                data = {
                    **subentry.data,
                    **user_input,
                    CONF_NAME: str(user_input[CONF_NAME]).strip(),
                }
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=data[CONF_NAME], data=data
                )
            values = user_input
        return self.async_show_form(
            step_id="reconfigure", data_schema=_group_schema(values), errors=errors
        )


# ---------------------------------------------------------------- window fields
# The fields are built by functions so the dialogs and the panel use the same
# selectors (ranges, units, domains) for showing and for checking values.

SENSOR_UNITS: dict[str, str] = {KIND_PV: "W", KIND_LUX: "lx", KIND_RADIATION: "W/m²"}
SENSOR_MAXIMA: dict[str, int] = {KIND_PV: 100000, KIND_LUX: 200000, KIND_RADIATION: 1500}


def _wreq(key: str, values: dict[str, Any], base: dict[str, Any] | None = None) -> vol.Required:
    base = base if base is not None else WINDOW_DEFAULTS
    return vol.Required(key, default=values.get(key, base.get(key)))


def cover_in_use(entry: ConfigEntry, cover: Any, own_id: str | None) -> str | None:
    """Title of another window that already controls ``cover``."""
    for sub_id, sub in entry.subentries.items():
        if (
            sub.subentry_type == SUBENTRY_WINDOW
            and sub_id != own_id
            and cover
            and sub.data.get(CONF_COVER) == cover
        ):
            return sub.title
    return None


def window_basics_fields(values: dict[str, Any], groups: dict[str, str]) -> dict[Any, Any]:
    """Name, cover, contacts and (if there are groups) the group."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=values.get(CONF_NAME, "")): TextSelector(),
        vol.Required(CONF_COVER, default=values.get(CONF_COVER)): _entity(["cover"]),
        vol.Optional(CONF_WINDOW_SENSORS, default=values.get(CONF_WINDOW_SENSORS, [])): _entity(
            CONTACT_DOMAINS, True
        ),
        vol.Optional(CONF_TILT_SENSORS, default=values.get(CONF_TILT_SENSORS, [])): _entity(
            CONTACT_DOMAINS, True
        ),
    }
    if groups:
        options = [SelectOptionDict(value=sub_id, label=title) for sub_id, title in groups.items()]
        fields[_opt(CONF_GROUP, values)] = SelectSelector(
            SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
        )
    return fields


def window_sun_fields(
    values: dict[str, Any], group_data: dict[str, Any], unit: str
) -> dict[Any, Any]:
    """Thresholds for the sensor types of the group, hold times, position, auto up."""
    temps = window_defaults(unit)
    fields: dict[Any, Any] = {}
    for kind, sensors_key in SENSOR_KINDS.items():
        if group_data.get(sensors_key):
            fields[_wreq(THRESHOLD_KEYS[kind], values)] = _number(
                0, SENSOR_MAXIMA[kind], 1, SENSOR_UNITS[kind]
            )
    fields.update(
        {
            _wreq(CONF_TEMP_THRESHOLD, values, temps): _temperature(unit, -20, 45),
            _wreq(CONF_TEMP_HOLD, values): _number(0, 120, 1, "min"),
            _opt(CONF_ROOM_ENTITY, values): _entity(["climate", "sensor"]),
            _wreq(CONF_ROOM_MARGIN, values, temps): _number(
                0, 10 if unit == "°C" else 18, 0.5, interval_unit(unit)
            ),
            _wreq(CONF_ROOM_THRESHOLD, values, temps): _temperature(unit, 10, 40),
            _opt(CONF_COOLING_ENTITY, values): _entity(["climate"]),
            _wreq(CONF_SUN_HOLD, values): _number(0, 120, 1, "min"),
            _wreq(CONF_SUN_POSITION, values): _number(0, 100, 1, "%"),
            _wreq(CONF_TOLERANCE, values): _number(0, 50, 1, "%"),
            _wreq(CONF_AUTO_UP, values): BooleanSelector(),
            _wreq(CONF_NOTIFY_OPEN, values): BooleanSelector(),
            _wreq(CONF_MANUAL_MAX, values): _number(0, 100, 1, "%"),
            _wreq(CONF_MANUAL_WINDOW, values): _number(0, 60, 1, "min"),
            _wreq(CONF_MANUAL_FOLLOW_UP, values): _number(0, 60, 1, "min"),
            _wreq(CONF_MANUAL_AT_SUN, values): BooleanSelector(),
        }
    )
    return fields


def window_override_fields(values: dict[str, Any]) -> dict[Any, Any]:
    return {
        _wreq(CONF_OVERRIDE_DURATION, values): _number(0, 1440, 1, "min"),
        _wreq(CONF_OVERRIDE_SUNRISE, values): BooleanSelector(),
        _wreq(CONF_OVERRIDE_IGNORE_EVENING, values): BooleanSelector(),
    }


def window_conditions_fields(values: dict[str, Any]) -> dict[Any, Any]:
    return {
        _opt(CONF_OPEN_BLOCK, values): _entity(),
        vol.Optional(
            CONF_OPEN_BLOCK_FREE, default=values.get(CONF_OPEN_BLOCK_FREE, FREE_STATES_DEFAULT)
        ): _states(),
        vol.Optional(CONF_TRIGGER_ENTITIES, default=values.get(CONF_TRIGGER_ENTITIES, [])): _entity(
            multiple=True
        ),
        vol.Optional(
            CONF_TRIGGER_ACTIVE, default=values.get(CONF_TRIGGER_ACTIVE, ACTIVE_STATES_DEFAULT)
        ): _states(),
        _wreq(CONF_TRIGGER_ON_DELAY, values): _number(0, 600, 1, "s"),
        _wreq(CONF_TRIGGER_OFF_DELAY, values): _number(0, 600, 1, "s"),
        _wreq(CONF_TRIGGER_MIN_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_TRIGGER_MAX_LOCK, values): _number(1, 48, 1, "h"),
        _opt(CONF_WINDOW_EXCEPTION, values): _entity(),
    }


def window_evening_fields(values: dict[str, Any], options: dict[str, Any]) -> dict[Any, Any]:
    """Evening run and own evening times (the global times are the defaults)."""
    return {
        _wreq(CONF_EVENING_CLOSE, values): BooleanSelector(),
        _wreq(CONF_EVENING_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_FOLLOW_UP_CLOSE, values): BooleanSelector(),
        _wreq(CONF_EVENING_CUSTOM, values): BooleanSelector(),
        **_evening_fields(values, {**DEFAULTS, **options}),
    }


def window_ventilation_fields(values: dict[str, Any]) -> dict[Any, Any]:
    return {
        _wreq(CONF_VENTILATION, values): BooleanSelector(),
        _wreq(CONF_VENT_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_CLOSED_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_VENT_DELAY_EVENING, values): _number(0, 600, 1, "s"),
        _wreq(CONF_VENT_DELAY_DAY, values): _number(0, 600, 1, "s"),
        _wreq(CONF_VACATION, values): BooleanSelector(),
    }


def window_protection_fields(values: dict[str, Any]) -> dict[Any, Any]:
    """Weather protection (switch, positions: empty = not affected) and the lockout protection."""
    return {
        _wreq(CONF_WEATHER_PROTECTION, values): BooleanSelector(),
        _opt(CONF_WIND_POSITION, values): _number(0, 100, 1, "%"),
        _opt(CONF_WINDOW_WIND_THRESHOLD, values): _number(0, 300, 0.5),
        _opt(CONF_RAIN_POSITION, values): _number(0, 100, 1, "%"),
        _opt(CONF_FROST_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_LOCKOUT, values): BooleanSelector(),
    }


def window_morning_fields(values: dict[str, Any]) -> dict[Any, Any]:
    return {
        _wreq(CONF_MORNING, values): BooleanSelector(),
        _wreq(CONF_MORNING_MODE, values): _choice(MODES, "morning_mode"),
        _wreq(CONF_MORNING_EARLIEST, values): TimeSelector(),
        _wreq(CONF_MORNING_LATEST, values): TimeSelector(),
        _wreq(CONF_MORNING_POSITION, values): _number(0, 100, 1, "%"),
        _wreq(CONF_MORNING_SUN_POSITION, values): BooleanSelector(),
    }


def window_morning_mode_fields(mode: str, values: dict[str, Any]) -> dict[Any, Any]:
    """Settings of one morning mode."""
    if mode == MODE_TIME:
        return {
            _wreq(CONF_MORNING_WORKDAY, values): TimeSelector(),
            _wreq(CONF_MORNING_WEEKEND, values): TimeSelector(),
        }
    if mode == MODE_SUN:
        return {
            _wreq(CONF_MORNING_SUN_EVENT, values): _choice(
                [SUN_SUNRISE, SUN_ELEVATION], "morning_sun_event"
            ),
            _wreq(CONF_MORNING_SUN_ELEVATION, values): _number(-18, 30, 0.5, "°"),
            _wreq(CONF_MORNING_SUN_OFFSET, values): _number(-180, 180, 1, "min"),
        }
    if mode == MODE_BRIGHTNESS:
        return {
            _wreq(CONF_MORNING_LUX, values): _number(0, 200000, 1, "lx"),
            _wreq(CONF_MORNING_LUX_HOLD, values): _number(0, 120, 1, "min"),
        }
    if mode == MODE_TRIGGER:
        return {
            vol.Required(CONF_MORNING_TRIGGER, default=values.get(CONF_MORNING_TRIGGER)): _entity(),
            _wreq(CONF_MORNING_TRIGGER_OFFSET, values): _number(-180, 180, 1, "min"),
        }
    return {}


def validate_morning(values: dict[str, Any], group_data: dict[str, Any] | None) -> dict[str, str]:
    """Time window of the morning opening and the brightness sensor for that mode."""
    if _time_key(values.get(CONF_MORNING_EARLIEST)) > _time_key(values.get(CONF_MORNING_LATEST)):
        return {CONF_MORNING_LATEST: "latest_before_earliest"}
    if (
        values.get(CONF_MORNING)
        and values.get(CONF_MORNING_MODE) == MODE_BRIGHTNESS
        and not (group_data or {}).get(CONF_LUX_SENSORS)
    ):
        return {CONF_MORNING_MODE: "no_lux_sensor"}
    return {}


# ---------------------------------------------------------------- window subentry


def _flatten(user_input: dict[str, Any], sections: tuple[str, ...]) -> dict[str, Any]:
    flat = {k: v for k, v in user_input.items() if k not in sections}
    for key in sections:
        flat.update(user_input.get(key) or {})
    return flat


class WindowSubentryFlow(ConfigSubentryFlow):
    """Add or change a window: basics, sun protection, behaviour, morning opening."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}
        self._reconfigure = False

    # ---- helpers

    def _groups(self) -> dict[str, Any]:
        return {
            sub_id: sub
            for sub_id, sub in self._get_entry().subentries.items()
            if sub.subentry_type == SUBENTRY_GROUP
        }

    @property
    def _unit(self) -> str:
        return temperature_unit(self.hass)

    def _finish(self) -> SubentryFlowResult:
        data = _clean({**window_defaults(self._unit), **self._values})
        title = str(data.get(CONF_NAME, "")).strip()
        if self._reconfigure:
            return self.async_update_and_abort(
                self._get_entry(), self._get_reconfigure_subentry(), title=title, data=data
            )
        return self.async_create_entry(title=title, data=data)

    # ---- entry points

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        return await self.async_step_basics(user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change a window: choose a category, each one is saved on its own."""
        subentry = self._get_reconfigure_subentry()
        self._reconfigure = True
        self._values = {CONF_NAME: subentry.title, **subentry.data}
        options = ["basics"]
        if self._values.get(CONF_GROUP) in self._groups():
            options.append("sun")
        options += ["behavior", "morning"]
        return self.async_show_menu(step_id="reconfigure", menu_options=options)

    # ---- steps

    async def async_step_basics(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input.get(CONF_NAME, "")).strip()
            own_id = self._get_reconfigure_subentry().subentry_id if self._reconfigure else None
            other = cover_in_use(self._get_entry(), user_input.get(CONF_COVER), own_id)
            if not name:
                errors[CONF_NAME] = "name_required"
            elif other is not None:
                errors[CONF_COVER] = "cover_in_use"
            else:
                self._values.pop(CONF_GROUP, None)
                self._values.update({**user_input, CONF_NAME: name})
                has_group = self._values.get(CONF_GROUP) in self._groups()
                if not has_group:
                    self._values.pop(CONF_GROUP, None)
                if self._reconfigure:
                    return self._finish()
                if has_group:
                    return await self.async_step_sun()
                return await self.async_step_behavior()
        groups = {sub_id: sub.title for sub_id, sub in self._groups().items()}
        return self.async_show_form(
            step_id="basics",
            data_schema=vol.Schema(
                window_basics_fields({**self._values, **(user_input or {})}, groups)
            ),
            errors=errors,
            last_step=self._reconfigure,
        )

    async def async_step_sun(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            # cleared optional entities are missing in the input
            for key in (CONF_ROOM_ENTITY, CONF_COOLING_ENTITY):
                self._values.pop(key, None)
            self._values.update(user_input)
            if self._reconfigure:
                return self._finish()
            return await self.async_step_behavior()
        group = self._groups().get(self._values.get(CONF_GROUP, ""))
        group_data = {**GROUP_DEFAULTS, **(group.data if group else {})}
        return self.async_show_form(
            step_id="sun",
            data_schema=vol.Schema(window_sun_fields(self._values, group_data, self._unit)),
            description_placeholders={"group": group.title if group else ""},
            last_step=self._reconfigure,
        )

    async def async_step_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        sections = (
            SECTION_OVERRIDE,
            SECTION_CONDITIONS,
            SECTION_EVENING,
            SECTION_VENTILATION,
            SECTION_PROTECTION,
        )
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = _flatten(user_input, sections)
            if flat.get(CONF_EVENING_CUSTOM):
                errors = _validate_evening(flat)
            if not errors:
                for key in (CONF_OPEN_BLOCK, CONF_WINDOW_EXCEPTION, *PROTECTION_POSITIONS):
                    self._values.pop(key, None)
                self._values.update(flat)
                if self._reconfigure:
                    return self._finish()
                return await self.async_step_morning()
            self._values.update(flat)
        v = self._values
        options = dict(self._get_entry().options)
        schema = vol.Schema(
            {
                vol.Required(SECTION_OVERRIDE): section(
                    vol.Schema(window_override_fields(v)), {"collapsed": False}
                ),
                vol.Required(SECTION_CONDITIONS): section(
                    vol.Schema(window_conditions_fields(v)), {"collapsed": True}
                ),
                vol.Required(SECTION_EVENING): section(
                    vol.Schema(window_evening_fields(v, options)), {"collapsed": True}
                ),
                vol.Required(SECTION_VENTILATION): section(
                    vol.Schema(window_ventilation_fields(v)), {"collapsed": True}
                ),
                vol.Required(SECTION_PROTECTION): section(
                    vol.Schema(window_protection_fields(v)), {"collapsed": True}
                ),
            }
        )
        return self.async_show_form(
            step_id="behavior", data_schema=schema, errors=errors, last_step=self._reconfigure
        )

    async def async_step_morning(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            group = self._groups().get(self._values.get(CONF_GROUP, ""))
            errors = validate_morning(user_input, dict(group.data) if group else None)
            if not errors:
                self._values.update(user_input)
                if not user_input.get(CONF_MORNING):
                    return self._finish()
                step = MORNING_STEPS[str(user_input[CONF_MORNING_MODE])]
                return await getattr(self, f"async_step_{step}")()
        return self.async_show_form(
            step_id="morning",
            data_schema=vol.Schema(window_morning_fields(self._values)),
            errors=errors,
        )

    async def _async_morning_mode(
        self, mode: str, user_input: dict[str, Any] | None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            return self._finish()
        return self.async_show_form(
            step_id=MORNING_STEPS[mode],
            data_schema=vol.Schema(window_morning_mode_fields(mode, self._values)),
            last_step=True,
        )

    async def async_step_morning_time(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_morning_mode(MODE_TIME, user_input)

    async def async_step_morning_sun(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_morning_mode(MODE_SUN, user_input)

    async def async_step_morning_brightness(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_morning_mode(MODE_BRIGHTNESS, user_input)

    async def async_step_morning_trigger(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        return await self._async_morning_mode(MODE_TRIGGER, user_input)
