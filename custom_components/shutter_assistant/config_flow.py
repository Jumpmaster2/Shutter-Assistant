"""Config flow, options flow and the subentry flows for groups and windows."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    FlowType,
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
    CONF_COVER,
    CONF_DAY_CHANGE,
    CONF_EVENING_CLOSE,
    CONF_EVENING_CUSTOM,
    CONF_EVENING_EARLIEST,
    CONF_EVENING_ELEVATION,
    CONF_EVENING_LATEST,
    CONF_FOLLOW_UP_CLOSE,
    CONF_FOLLOW_UP_EARLIEST,
    CONF_GROUP,
    CONF_LANGUAGE,
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
    CONF_NOTIFY,
    CONF_NOTIFY_OPEN,
    CONF_OPEN_BLOCK,
    CONF_OPEN_BLOCK_FREE,
    CONF_OUTDOOR_TEMP,
    CONF_OVERRIDE_DURATION,
    CONF_OVERRIDE_IGNORE_EVENING,
    CONF_OVERRIDE_SUNRISE,
    CONF_PV_SENSORS,
    CONF_RADIATION_SENSORS,
    CONF_STARTUP_DELAY,
    CONF_SUMMER_THRESHOLD,
    CONF_SUN_HOLD,
    CONF_SUN_POSITION,
    CONF_TEMP_HOLD,
    CONF_TEMP_THRESHOLD,
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
    CONF_WEATHER,
    CONF_WINDOW_EXCEPTION,
    CONF_WINDOW_SENSORS,
    CONF_WORKDAY,
    DEFAULTS,
    DOMAIN,
    FREE_STATES_DEFAULT,
    GROUP_DEFAULTS,
    LANGUAGE_OPTIONS,
    NAME,
    SECTION_CONDITIONS,
    SECTION_EVENING,
    SECTION_OVERRIDE,
    SECTION_VENTILATION,
    SENSOR_KINDS,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    THRESHOLD_KEYS,
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


def _choice(options: list[str], key: str) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, translation_key=key, mode=SelectSelectorMode.LIST)
    )


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


def _time_key(value: Any) -> str:
    text = str(value or "")
    return text if text.count(":") == 2 else f"{text}:00"


# ---------------------------------------------------------------- global schemas


def _general_schema(hass: HomeAssistant, v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_OUTDOOR_TEMP, default=v.get(CONF_OUTDOOR_TEMP)): _entity(["sensor"]),
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
        }
    )


def _summer_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            _req(CONF_SUMMER_THRESHOLD, v): _number(0, 45, 0.5, "°C"),
            _req(CONF_DAY_CHANGE, v): TimeSelector(),
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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options.update(_clean(user_input))
            return await self.async_step_summer()
        return self.async_show_form(
            step_id="user", data_schema=_general_schema(self.hass, {**DEFAULTS})
        )

    async def async_step_summer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_evening()
        return self.async_show_form(step_id="summer", data_schema=_summer_schema({}))

    async def async_step_evening(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_evening(user_input)
            if not errors:
                options = {**DEFAULTS, **self._options, **user_input}
                return self.async_create_entry(title=NAME, data={}, options=options)
        return self.async_show_form(
            step_id="evening", data_schema=_evening_schema(user_input or {}), errors=errors
        )

    async def async_on_create_entry(self, result: ConfigFlowResult) -> ConfigFlowResult:
        """Directly continue with the first group."""
        entry = result.get("result")
        if entry is None:
            return result
        sub = await self.hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_GROUP), context={"source": SOURCE_USER}
        )
        result["next_flow"] = (FlowType.CONFIG_SUBENTRIES_FLOW, sub["flow_id"])
        return result


# ---------------------------------------------------------------- options flow


class ShutterOptionsFlow(OptionsFlow):
    """All global settings, grouped in a menu."""

    @property
    def _values(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.config_entry.options}

    def _save(self, updates: dict[str, Any], remove: tuple[str, ...] = ()) -> ConfigFlowResult:
        options = {**self.config_entry.options}
        for key in remove:
            options.pop(key, None)
        options.update(updates)
        return self.async_create_entry(data=options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init", menu_options=["general", "summer", "evening", "vacation", "startup"]
        )

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(_clean(user_input), remove=(CONF_WEATHER, CONF_WORKDAY))
        return self.async_show_form(
            step_id="general", data_schema=_general_schema(self.hass, self._values)
        )

    async def async_step_summer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(step_id="summer", data_schema=_summer_schema(self._values))

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

    async def async_step_startup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self._save(user_input)
        return self.async_show_form(step_id="startup", data_schema=_startup_schema(self._values))


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


def _validate_group(data: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not str(data.get(CONF_NAME, "")).strip():
        errors[CONF_NAME] = "name_required"
    if float(data.get(CONF_AZIMUTH_FROM, 0)) == float(data.get(CONF_AZIMUTH_TO, 0)):
        errors[CONF_AZIMUTH_TO] = "azimuth_equal"
    return errors


class GroupSubentryFlow(ConfigSubentryFlow):
    """Add or change a group (direction of the sun with its sensors)."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate_group(user_input)
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
            errors = _validate_group(user_input)
            if not errors:
                data = {**user_input, CONF_NAME: str(user_input[CONF_NAME]).strip()}
                return self.async_update_and_abort(
                    self._get_entry(), subentry, title=data[CONF_NAME], data=data
                )
            values = user_input
        return self.async_show_form(
            step_id="reconfigure", data_schema=_group_schema(values), errors=errors
        )


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

    def _v(self, key: str) -> Any:
        return self._values.get(key, WINDOW_DEFAULTS.get(key))

    def _req(self, key: str) -> vol.Required:
        return vol.Required(key, default=self._v(key))

    def _finish(self) -> SubentryFlowResult:
        data = _clean({**WINDOW_DEFAULTS, **self._values})
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
            if not name:
                errors[CONF_NAME] = "name_required"
            else:
                for key in (CONF_GROUP,):
                    self._values.pop(key, None)
                self._values.update({**user_input, CONF_NAME: name})
                has_group = self._values.get(CONF_GROUP) in self._groups()
                if not has_group:
                    self._values.pop(CONF_GROUP, None)
                if self._reconfigure:
                    return self._finish()
                if has_group:
                    return await self.async_step_sun()
                return await self.async_step_behavior()
        groups = [
            SelectOptionDict(value=sub_id, label=sub.title)
            for sub_id, sub in self._groups().items()
        ]
        schema: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=self._values.get(CONF_NAME, "")): TextSelector(),
            vol.Required(CONF_COVER, default=self._values.get(CONF_COVER)): _entity(["cover"]),
            vol.Optional(
                CONF_WINDOW_SENSORS, default=self._values.get(CONF_WINDOW_SENSORS, [])
            ): _entity(["binary_sensor", "input_boolean"], True),
        }
        if groups:
            schema[_opt(CONF_GROUP, self._values)] = SelectSelector(
                SelectSelectorConfig(options=groups, mode=SelectSelectorMode.DROPDOWN)
            )
        return self.async_show_form(
            step_id="basics",
            data_schema=vol.Schema(schema),
            errors=errors,
            last_step=self._reconfigure,
        )

    async def async_step_sun(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            if self._reconfigure:
                return self._finish()
            return await self.async_step_behavior()
        group = self._groups().get(self._values.get(CONF_GROUP, ""))
        group_data = {**GROUP_DEFAULTS, **(group.data if group else {})}
        units = {"pv": "W", "lux": "lx", "radiation": "W/m²"}
        maxima = {"pv": 100000, "lux": 200000, "radiation": 1500}
        fields: dict[Any, Any] = {}
        for kind, sensors_key in SENSOR_KINDS.items():
            if group_data.get(sensors_key):
                fields[self._req(THRESHOLD_KEYS[kind])] = _number(0, maxima[kind], 1, units[kind])
        fields.update(
            {
                self._req(CONF_TEMP_THRESHOLD): _number(-20, 45, 0.5, "°C"),
                self._req(CONF_TEMP_HOLD): _number(0, 120, 1, "min"),
                self._req(CONF_SUN_HOLD): _number(0, 120, 1, "min"),
                self._req(CONF_SUN_POSITION): _number(0, 100, 1, "%"),
                self._req(CONF_TOLERANCE): _number(0, 50, 1, "%"),
                self._req(CONF_AUTO_UP): BooleanSelector(),
                self._req(CONF_NOTIFY_OPEN): BooleanSelector(),
                self._req(CONF_MANUAL_MAX): _number(0, 100, 1, "%"),
                self._req(CONF_MANUAL_WINDOW): _number(0, 60, 1, "min"),
                self._req(CONF_MANUAL_FOLLOW_UP): _number(0, 60, 1, "min"),
                self._req(CONF_MANUAL_AT_SUN): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="sun",
            data_schema=vol.Schema(fields),
            description_placeholders={"group": group.title if group else ""},
            last_step=self._reconfigure,
        )

    async def async_step_behavior(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        sections = (SECTION_OVERRIDE, SECTION_CONDITIONS, SECTION_EVENING, SECTION_VENTILATION)
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = _flatten(user_input, sections)
            if flat.get(CONF_EVENING_CUSTOM):
                errors = _validate_evening(flat)
            if not errors:
                for key in (CONF_OPEN_BLOCK, CONF_WINDOW_EXCEPTION):
                    self._values.pop(key, None)
                self._values.update(flat)
                if self._reconfigure:
                    return self._finish()
                return await self.async_step_morning()
            self._values.update(flat)
        v = self._values
        schema = vol.Schema(
            {
                vol.Required(SECTION_OVERRIDE): section(
                    vol.Schema(
                        {
                            self._req(CONF_OVERRIDE_DURATION): _number(0, 1440, 1, "min"),
                            self._req(CONF_OVERRIDE_SUNRISE): BooleanSelector(),
                            self._req(CONF_OVERRIDE_IGNORE_EVENING): BooleanSelector(),
                        }
                    ),
                    {"collapsed": False},
                ),
                vol.Required(SECTION_CONDITIONS): section(
                    vol.Schema(
                        {
                            _opt(CONF_OPEN_BLOCK, v): _entity(),
                            vol.Optional(
                                CONF_OPEN_BLOCK_FREE,
                                default=v.get(CONF_OPEN_BLOCK_FREE, FREE_STATES_DEFAULT),
                            ): _states(),
                            vol.Optional(
                                CONF_TRIGGER_ENTITIES, default=v.get(CONF_TRIGGER_ENTITIES, [])
                            ): _entity(multiple=True),
                            vol.Optional(
                                CONF_TRIGGER_ACTIVE,
                                default=v.get(CONF_TRIGGER_ACTIVE, ACTIVE_STATES_DEFAULT),
                            ): _states(),
                            self._req(CONF_TRIGGER_ON_DELAY): _number(0, 600, 1, "s"),
                            self._req(CONF_TRIGGER_OFF_DELAY): _number(0, 600, 1, "s"),
                            self._req(CONF_TRIGGER_MIN_POSITION): _number(0, 100, 1, "%"),
                            self._req(CONF_TRIGGER_MAX_LOCK): _number(1, 48, 1, "h"),
                            _opt(CONF_WINDOW_EXCEPTION, v): _entity(),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(SECTION_EVENING): section(
                    vol.Schema(
                        {
                            self._req(CONF_EVENING_CLOSE): BooleanSelector(),
                            self._req(CONF_FOLLOW_UP_CLOSE): BooleanSelector(),
                            self._req(CONF_EVENING_CUSTOM): BooleanSelector(),
                            **_evening_fields(v, {**DEFAULTS, **self._get_entry().options}),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Required(SECTION_VENTILATION): section(
                    vol.Schema(
                        {
                            self._req(CONF_VENTILATION): BooleanSelector(),
                            self._req(CONF_VENT_POSITION): _number(0, 100, 1, "%"),
                            self._req(CONF_CLOSED_POSITION): _number(0, 100, 1, "%"),
                            self._req(CONF_VENT_DELAY_EVENING): _number(0, 600, 1, "s"),
                            self._req(CONF_VENT_DELAY_DAY): _number(0, 600, 1, "s"),
                            self._req(CONF_VACATION): BooleanSelector(),
                        }
                    ),
                    {"collapsed": True},
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
            if _time_key(user_input.get(CONF_MORNING_EARLIEST)) > _time_key(
                user_input.get(CONF_MORNING_LATEST)
            ):
                errors[CONF_MORNING_LATEST] = "latest_before_earliest"
            elif (
                user_input.get(CONF_MORNING)
                and user_input.get(CONF_MORNING_MODE) == MODE_BRIGHTNESS
                and (group is None or not group.data.get(CONF_LUX_SENSORS))
            ):
                errors[CONF_MORNING_MODE] = "no_lux_sensor"
            else:
                self._values.update(user_input)
                if not user_input.get(CONF_MORNING):
                    return self._finish()
                step = MORNING_STEPS[str(user_input[CONF_MORNING_MODE])]
                return await getattr(self, f"async_step_{step}")()
        schema = vol.Schema(
            {
                self._req(CONF_MORNING): BooleanSelector(),
                self._req(CONF_MORNING_MODE): _choice(MODES, "morning_mode"),
                self._req(CONF_MORNING_EARLIEST): TimeSelector(),
                self._req(CONF_MORNING_LATEST): TimeSelector(),
                self._req(CONF_MORNING_POSITION): _number(0, 100, 1, "%"),
                self._req(CONF_MORNING_SUN_POSITION): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="morning", data_schema=schema, errors=errors)

    async def async_step_morning_time(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            return self._finish()
        schema = vol.Schema(
            {
                self._req(CONF_MORNING_WORKDAY): TimeSelector(),
                self._req(CONF_MORNING_WEEKEND): TimeSelector(),
            }
        )
        return self.async_show_form(step_id="morning_time", data_schema=schema, last_step=True)

    async def async_step_morning_sun(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            return self._finish()
        schema = vol.Schema(
            {
                self._req(CONF_MORNING_SUN_EVENT): _choice(
                    [SUN_SUNRISE, SUN_ELEVATION], "morning_sun_event"
                ),
                self._req(CONF_MORNING_SUN_ELEVATION): _number(-18, 30, 0.5, "°"),
                self._req(CONF_MORNING_SUN_OFFSET): _number(-180, 180, 1, "min"),
            }
        )
        return self.async_show_form(step_id="morning_sun", data_schema=schema, last_step=True)

    async def async_step_morning_brightness(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            return self._finish()
        schema = vol.Schema(
            {
                self._req(CONF_MORNING_LUX): _number(0, 200000, 1, "lx"),
                self._req(CONF_MORNING_LUX_HOLD): _number(0, 120, 1, "min"),
            }
        )
        return self.async_show_form(
            step_id="morning_brightness", data_schema=schema, last_step=True
        )

    async def async_step_morning_trigger(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            self._values.update(user_input)
            return self._finish()
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MORNING_TRIGGER, default=self._values.get(CONF_MORNING_TRIGGER)
                ): _entity(),
                self._req(CONF_MORNING_TRIGGER_OFFSET): _number(-180, 180, 1, "min"),
            }
        )
        return self.async_show_form(step_id="morning_trigger", data_schema=schema, last_step=True)
