"""Constants for Shutter Assistant."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "shutter_assistant"
NAME: Final = "Shutter Assistant"
LOGGER = logging.getLogger(__package__)

PLATFORMS: Final = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

SUBENTRY_GROUP: Final = "group"
SUBENTRY_WINDOW: Final = "window"
STORAGE_VERSION: Final = 1
EVENT_LOGBOOK: Final = f"{DOMAIN}_logbook"
# Events for own automations
EVENT_COVER_MOVED: Final = f"{DOMAIN}_cover_moved"
EVENT_COVER_FAILED: Final = f"{DOMAIN}_cover_failed"
EVENT_PROTECTION: Final = f"{DOMAIN}_protection"

# Window contacts are debounced before they count as closed (default, seconds).
CONF_WINDOW_DEBOUNCE = "window_closed_delay"
# Show the panel in the sidebar (it stays reachable from the integration page).
CONF_SHOW_PANEL = "show_panel"

# ---------- global options ----------
CONF_WEATHER = "weather"
CONF_OUTDOOR_TEMP = "outdoor_temperature"
CONF_LANGUAGE = "language"
CONF_NOTIFY = "notify_services"
CONF_WORKDAY = "workday_entity"
# Days without work when there is no workday sensor.
CONF_WEEKEND_DAYS = "weekend_days"
WEEKDAYS: Final = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

CONF_SUMMER_THRESHOLD = "summer_threshold"
# A summer day only by the outdoor temperature needs a forecast low of the
# coming night of at least this value.
CONF_NIGHT_THRESHOLD = "night_threshold"
# On while heating is wanted (e.g. the heating day of AI Heating Assistant):
# then the warmth of the sun is welcome unless a room is too warm.
CONF_HEATING_ENTITY = "heating_entity"
CONF_DAY_CHANGE = "day_change_time"
# Kind of forecast: "auto" takes the first the weather entity supports.
CONF_FORECAST_TYPE = "forecast_type"
FORECAST_AUTO = "auto"
FORECAST_DAILY = "daily"
FORECAST_TWICE_DAILY = "twice_daily"
FORECAST_HOURLY = "hourly"
FORECAST_TYPES: Final = [FORECAST_AUTO, FORECAST_DAILY, FORECAST_TWICE_DAILY, FORECAST_HOURLY]

CONF_EVENING_EARLIEST = "evening_earliest"
CONF_EVENING_ELEVATION = "evening_elevation"
CONF_EVENING_LATEST = "evening_latest"
CONF_NIGHT_END = "night_end"
CONF_FOLLOW_UP_EARLIEST = "follow_up_earliest"

CONF_VACATION_ENTITIES = "vacation_entities"
CONF_VAC_MORNING = "vacation_morning_start"
CONF_VAC_MORNING_WINDOW = "vacation_morning_window"
CONF_VAC_POS_MIN = "vacation_position_min"
CONF_VAC_POS_MAX = "vacation_position_max"
CONF_VAC_EVENING = "vacation_evening_start"
CONF_VAC_EVENING_WINDOW = "vacation_evening_window"

CONF_STARTUP_DELAY = "startup_delay"
CONF_CATCH_UP_AFTER = "catch_up_after"

# When a manual command starts an override: only after a real movement, or
# with every command (also when the cover is already at its target).
CONF_OVERRIDE_TRIGGER = "override_trigger"
TRIGGER_MOVEMENT = "movement"
TRIGGER_COMMAND = "command"
OVERRIDE_TRIGGERS: Final = [TRIGGER_MOVEMENT, TRIGGER_COMMAND]

# Weather protection: wind and rain move covers to a protection position, frost
# keeps a gap when closing. Each ends only after the release time.
CONF_WIND_ENTITY = "wind_entity"
CONF_WIND_THRESHOLD = "wind_threshold"
CONF_RAIN_ENTITY = "rain_entity"
CONF_RAIN_THRESHOLD = "rain_threshold"
CONF_FROST_THRESHOLD = "frost_threshold"
CONF_PROTECTION_RELEASE = "protection_release"
# Spacing between two cover commands (s, 0 = off) and the check whether a
# cover reached its target (s after the command, 0 = off).
CONF_COMMAND_INTERVAL = "command_interval"
CONF_VERIFY_AFTER = "verify_after"

LANGUAGE_OPTIONS: Final = ["auto", "de", "en"]

DEFAULTS: Final[dict[str, object]] = {
    CONF_LANGUAGE: "auto",
    CONF_NOTIFY: [],
    CONF_WEEKEND_DAYS: ["sat", "sun"],
    CONF_SUMMER_THRESHOLD: 23.0,
    CONF_NIGHT_THRESHOLD: 14.0,
    CONF_DAY_CHANGE: "01:00:00",
    CONF_FORECAST_TYPE: FORECAST_AUTO,
    CONF_EVENING_EARLIEST: "17:00:00",
    CONF_EVENING_ELEVATION: -4.0,
    CONF_EVENING_LATEST: "21:00:00",
    CONF_NIGHT_END: "03:30:00",
    CONF_FOLLOW_UP_EARLIEST: "16:00:00",
    CONF_VACATION_ENTITIES: [],
    CONF_VAC_MORNING: "07:00:00",
    CONF_VAC_MORNING_WINDOW: 60,
    CONF_VAC_POS_MIN: 60,
    CONF_VAC_POS_MAX: 100,
    CONF_VAC_EVENING: "19:00:00",
    CONF_VAC_EVENING_WINDOW: 90,
    CONF_STARTUP_DELAY: 5,
    CONF_CATCH_UP_AFTER: "12:00:00",
    CONF_OVERRIDE_TRIGGER: TRIGGER_MOVEMENT,
    CONF_WINDOW_DEBOUNCE: 5,
    CONF_SHOW_PANEL: True,
    CONF_WIND_THRESHOLD: 50.0,
    CONF_RAIN_THRESHOLD: 0.0,
    CONF_FROST_THRESHOLD: 1.0,
    CONF_PROTECTION_RELEASE: 15,
    CONF_COMMAND_INTERVAL: 0,
    CONF_VERIFY_AFTER: 90,
}

# ---------- house (only in the panel: drawn in the sun compass) ----------
CONF_HOUSE_AZIMUTH = "house_azimuth"
CONF_HOUSE_WIDTH = "house_width"
CONF_HOUSE_DEPTH = "house_depth"
# Wall of the house a group or window belongs to, by its angle to the front
# (right and left as seen from inside, looking out of the front).
CONF_WALL = "wall"
WALLS: Final = {"front": 0, "right": 90, "back": 180, "left": 270}
# Order of the windows on their wall, 1 = left as seen from inside.
CONF_WALL_POSITION = "wall_position"

# ---------- group (subentry) ----------
CONF_NAME = "name"
CONF_AZIMUTH_FROM = "azimuth_from"
CONF_AZIMUTH_TO = "azimuth_to"
CONF_PV_SENSORS = "pv_sensors"
CONF_LUX_SENSORS = "lux_sensors"
CONF_RADIATION_SENSORS = "radiation_sensors"

KIND_PV = "pv"
KIND_LUX = "lux"
KIND_RADIATION = "radiation"
SENSOR_KINDS: Final = {
    KIND_PV: CONF_PV_SENSORS,
    KIND_LUX: CONF_LUX_SENSORS,
    KIND_RADIATION: CONF_RADIATION_SENSORS,
}

GROUP_DEFAULTS: Final[dict[str, object]] = {
    CONF_AZIMUTH_FROM: 90,
    CONF_AZIMUTH_TO: 270,
    CONF_PV_SENSORS: [],
    CONF_LUX_SENSORS: [],
    CONF_RADIATION_SENSORS: [],
}

# ---------- window (subentry) ----------
CONF_COVER = "cover"
CONF_WINDOW_SENSORS = "window_sensors"
CONF_GROUP = "group"
# Contacts that mean "tilted" (window handles with open/tilted/closed also work
# as window contacts) and the lockout protection of doors.
CONF_TILT_SENSORS = "tilt_sensors"
CONF_LOCKOUT = "lockout_protection"
# Weather protection per window (empty = not affected / off).
CONF_WIND_POSITION = "wind_position"
CONF_RAIN_POSITION = "rain_position"
CONF_FROST_POSITION = "frost_position"

CONF_PV_THRESHOLD = "pv_threshold"
CONF_LUX_THRESHOLD = "lux_threshold"
CONF_RADIATION_THRESHOLD = "radiation_threshold"
CONF_TEMP_THRESHOLD = "temperature_threshold"
CONF_TEMP_HOLD = "temperature_hold"
CONF_SUN_HOLD = "sun_hold"
# Room temperature: a thermostat (climate, too warm from setpoint + margin) or a
# temperature sensor (too warm from the threshold).
CONF_ROOM_ENTITY = "room_entity"
CONF_ROOM_MARGIN = "room_margin"
CONF_ROOM_THRESHOLD = "room_threshold"
# Air conditioner: while it cools, the room counts as too warm.
CONF_COOLING_ENTITY = "cooling_entity"
CONF_SUN_POSITION = "sun_position"
CONF_TOLERANCE = "position_tolerance"
CONF_AUTO_UP = "auto_up"
CONF_NOTIFY_OPEN = "notify_open_window"
CONF_MANUAL_MAX = "manual_max_position"
CONF_MANUAL_WINDOW = "manual_detection_window"
CONF_MANUAL_FOLLOW_UP = "manual_follow_up"
CONF_MANUAL_AT_SUN = "manual_at_sun_position"

THRESHOLD_KEYS: Final = {
    KIND_PV: CONF_PV_THRESHOLD,
    KIND_LUX: CONF_LUX_THRESHOLD,
    KIND_RADIATION: CONF_RADIATION_THRESHOLD,
}

CONF_OVERRIDE_DURATION = "override_duration"
CONF_OVERRIDE_SUNRISE = "override_sunrise_reset"
CONF_OVERRIDE_IGNORE_EVENING = "override_ignore_evening"

CONF_OPEN_BLOCK = "open_block_entity"
CONF_OPEN_BLOCK_FREE = "open_block_free_states"
CONF_TRIGGER_ENTITIES = "close_trigger_entities"
CONF_TRIGGER_ACTIVE = "close_trigger_active_states"
CONF_TRIGGER_ON_DELAY = "close_trigger_on_delay"
CONF_TRIGGER_OFF_DELAY = "close_trigger_off_delay"
CONF_TRIGGER_MIN_POSITION = "close_trigger_min_position"
CONF_TRIGGER_MAX_LOCK = "close_trigger_max_lock"
CONF_WINDOW_EXCEPTION = "window_exception_entity"

CONF_EVENING_CUSTOM = "evening_custom"
CONF_EVENING_CLOSE = "evening_close"
# Target of the evening run and of closing after the window was closed (0 = closed).
CONF_EVENING_POSITION = "evening_position"
CONF_FOLLOW_UP_CLOSE = "follow_up_close"
CONF_VENTILATION = "ventilation"
CONF_VENT_POSITION = "ventilation_position"
CONF_CLOSED_POSITION = "closed_position"
CONF_VENT_DELAY_EVENING = "ventilation_delay_evening"
CONF_VENT_DELAY_DAY = "ventilation_delay_day"
CONF_VACATION = "vacation"

CONF_MORNING = "morning_enabled"
CONF_MORNING_MODE = "morning_mode"
CONF_MORNING_EARLIEST = "morning_earliest"
CONF_MORNING_LATEST = "morning_latest"
CONF_MORNING_POSITION = "morning_position"
CONF_MORNING_SUN_POSITION = "morning_sun_position"
CONF_MORNING_WORKDAY = "morning_time_workday"
CONF_MORNING_WEEKEND = "morning_time_weekend"
CONF_MORNING_SUN_EVENT = "morning_sun_event"
CONF_MORNING_SUN_ELEVATION = "morning_sun_elevation"
CONF_MORNING_SUN_OFFSET = "morning_sun_offset"
CONF_MORNING_LUX = "morning_lux_threshold"
CONF_MORNING_LUX_HOLD = "morning_lux_hold"
CONF_MORNING_TRIGGER = "morning_trigger_entity"
CONF_MORNING_TRIGGER_OFFSET = "morning_trigger_offset"

FREE_STATES_DEFAULT: Final = ["off", "unavailable", "unknown", "standby"]
ACTIVE_STATES_DEFAULT: Final = ["on", "idle", "paused", "playing"]

WINDOW_DEFAULTS: Final[dict[str, object]] = {
    CONF_WINDOW_SENSORS: [],
    CONF_TILT_SENSORS: [],
    CONF_LOCKOUT: False,
    CONF_PV_THRESHOLD: 130.0,
    CONF_LUX_THRESHOLD: 14500.0,
    CONF_RADIATION_THRESHOLD: 150.0,
    CONF_TEMP_THRESHOLD: 19.0,
    CONF_TEMP_HOLD: 10,
    CONF_SUN_HOLD: 5,
    CONF_ROOM_MARGIN: 2.0,
    CONF_ROOM_THRESHOLD: 24.0,
    CONF_SUN_POSITION: 10,
    CONF_TOLERANCE: 5,
    CONF_AUTO_UP: True,
    CONF_NOTIFY_OPEN: True,
    CONF_MANUAL_MAX: 25,
    CONF_MANUAL_WINDOW: 5,
    CONF_MANUAL_FOLLOW_UP: 5,
    CONF_MANUAL_AT_SUN: False,
    CONF_OVERRIDE_DURATION: 60,
    CONF_OVERRIDE_SUNRISE: False,
    CONF_OVERRIDE_IGNORE_EVENING: False,
    CONF_OPEN_BLOCK_FREE: FREE_STATES_DEFAULT,
    CONF_TRIGGER_ENTITIES: [],
    CONF_TRIGGER_ACTIVE: ACTIVE_STATES_DEFAULT,
    CONF_TRIGGER_ON_DELAY: 8,
    CONF_TRIGGER_OFF_DELAY: 15,
    CONF_TRIGGER_MIN_POSITION: 20,
    CONF_TRIGGER_MAX_LOCK: 12,
    CONF_EVENING_CUSTOM: False,
    CONF_EVENING_CLOSE: True,
    CONF_EVENING_POSITION: 0,
    CONF_FOLLOW_UP_CLOSE: True,
    CONF_VENTILATION: True,
    CONF_VENT_POSITION: 30,
    CONF_CLOSED_POSITION: 5,
    CONF_VENT_DELAY_EVENING: 3,
    CONF_VENT_DELAY_DAY: 60,
    CONF_VACATION: True,
    CONF_MORNING: False,
    CONF_MORNING_MODE: "time",
    CONF_MORNING_EARLIEST: "06:00:00",
    CONF_MORNING_LATEST: "09:00:00",
    CONF_MORNING_POSITION: 100,
    CONF_MORNING_SUN_POSITION: True,
    CONF_MORNING_WORKDAY: "06:30:00",
    CONF_MORNING_WEEKEND: "08:00:00",
    CONF_MORNING_SUN_EVENT: "sunrise",
    CONF_MORNING_SUN_ELEVATION: 0.0,
    CONF_MORNING_SUN_OFFSET: 0,
    CONF_MORNING_LUX: 1000.0,
    CONF_MORNING_LUX_HOLD: 5,
    CONF_MORNING_TRIGGER_OFFSET: 0,
}

SECTION_OVERRIDE = "override"
SECTION_CONDITIONS = "conditions"
SECTION_EVENING = "evening"
SECTION_VENTILATION = "ventilation_settings"
SECTION_PROTECTION = "protection"
