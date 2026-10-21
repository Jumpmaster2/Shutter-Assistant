"""Event driven engine: listens to the configured entities and runs the window rules.

Nothing is polled. Every evaluation is caused by a state change of a configured
entity or by a calculated point in time (sun sector bounds, evening start, hold
times, override end, daily times, sunrise, random vacation times).
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

from astral import Observer
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_sunrise,
    async_track_time_change,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
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
    CONF_RAIN_ENTITY,
    CONF_RAIN_POSITION,
    CONF_RAIN_THRESHOLD,
    CONF_ROOM_ENTITY,
    CONF_ROOM_MARGIN,
    CONF_ROOM_THRESHOLD,
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
    CONF_WEEKEND_DAYS,
    CONF_WIND_ENTITY,
    CONF_WIND_POSITION,
    CONF_WIND_THRESHOLD,
    CONF_WINDOW_DEBOUNCE,
    CONF_WINDOW_EXCEPTION,
    CONF_WINDOW_SENSORS,
    CONF_WORKDAY,
    DOMAIN,
    EVENT_COVER_FAILED,
    EVENT_COVER_MOVED,
    EVENT_LOGBOOK,
    EVENT_PROTECTION,
    GROUP_DEFAULTS,
    LOGGER,
    NAME,
    SENSOR_KINDS,
    STORAGE_VERSION,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    THRESHOLD_KEYS,
    TRIGGER_COMMAND,
)
from .logic import forecast as fc
from .logic import morning as mo
from .logic import sun as sunlib
from .logic import window as rules
from .logic.conditions import (
    CONTACT_CLOSED,
    CONTACT_OPEN,
    CONTACT_TILTED,
    FollowUp,
    Hold,
    as_float,
    at_least,
    cooling_active,
    heat_need,
    reported_open,
    room_warm,
    sensors_ok,
    summer_day,
    window_contact,
)
from .logic.evening import EveningSettings, evening_day, evening_end, evening_start, is_evening
from .logic.override import (
    MOVING,
    CommandTracker,
    MovementWatch,
    is_manual,
    override_until,
    reached,
)
from .logic.protection import FROST, KINDS, RAIN, WIND, Guard, above, freezing, raining
from .logic.vacation import random_position, random_time
from .messages import resolve_language, text
from .units import defaults, temperature_unit, window_defaults

type ShutterConfigEntry = ConfigEntry[ShutterEngine]

INVALID = (STATE_UNAVAILABLE, STATE_UNKNOWN)
# A failed forecast is retried after this time (the last known value stays valid).
FORECAST_RETRY = timedelta(minutes=30)
# A forecast request that takes longer counts as failed (seconds).
FORECAST_TIMEOUT = 30
ISSUE_MISSING_GROUP = "missing_group_"
ISSUE_FORECAST = "forecast_unsupported"
# moves of the weather protection (frost and a tilted window do not limit them)
PROTECTIVE = (rules.R_PROTECT_WIND, rules.R_PROTECT_RAIN)


def parse_time(value: Any, fallback: str = "00:00:00") -> time:
    """Parse 'HH:MM[:SS]'."""
    for candidate in (value, fallback):
        try:
            parts = [int(p) for p in str(candidate).split(":")]
            while len(parts) < 3:
                parts.append(0)
            return time(parts[0], parts[1], parts[2])
        except (TypeError, ValueError, IndexError):
            continue
    return time(0, 0)


@dataclass
class Group:
    group_id: str
    name: str
    azimuth_from: float
    azimuth_to: float
    sensors: dict[str, list[str]]


@dataclass
class TriggerState:
    active: bool = False
    locked_until: datetime | None = None
    pending: bool = False


@dataclass
class Window:
    """One window with its configuration and runtime state."""

    window_id: str
    name: str
    cover: str
    sensors: list[str]
    group_id: str | None
    conf: dict[str, Any]
    rules: rules.WindowRules
    evening_settings: EveningSettings | None
    morning_settings: mo.MorningSettings | None
    temp_hold: Hold
    live_hold: Hold
    no_temp: FollowUp
    morning_hold: Hold
    window_open: bool = False
    flags: tuple[bool, ...] = ()
    trigger: TriggerState = field(default_factory=TriggerState)
    # persisted
    override_until: datetime | None = None
    override_since: datetime | None = None
    override_sunrise: bool = False
    sun_day: date | None = None
    notified_day: date | None = None
    evening_day: date | None = None
    morning_day: date | None = None
    last_manual: datetime | None = None
    last_reason: dict[str, Any] = field(default_factory=dict)
    morning_pending: bool = False
    # evening run skipped because the automatic was off (caught up when switched on)
    evening_missed: date | None = None
    tilt_sensors: list[str] = field(default_factory=list)
    window_tilted: bool = False
    # wind or rain protection running for this window
    protection: str | None = None
    # switches of the window (persisted)
    automatic: bool = True
    sun_enabled: bool = True
    # last command, checked after the verify time: target, reason, attempt
    verify: tuple[int, str, int] | None = None
    # the cover was still moving at the check: one more look later
    verify_waited: bool = False

    @property
    def override_active(self) -> bool:
        if self.override_until is None:
            return self.override_sunrise
        return dt_util.utcnow() < self.override_until


class ShutterEngine(DataUpdateCoordinator[None]):
    """The central engine of Shutter Assistant."""

    config_entry: ShutterConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ShutterConfigEntry) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=NAME)
        # Temperatures (sensors, forecast, thresholds) are in the unit of the instance.
        self.temperature_unit = temperature_unit(hass)
        self._defaults = defaults(self.temperature_unit)
        self._window_defaults = window_defaults(self.temperature_unit)
        self._shutdown = False
        self.global_device_id: str | None = None
        self.groups: dict[str, Group] = {}
        self.windows: dict[str, Window] = {}
        self.automatic = True
        self.forecast_day: date | None = None
        self.forecast_max: float | None = None
        self.forecast_night_low: float | None = None
        self.raised_day: date | None = None
        self.vacation_evening_day: date | None = None
        self.startup_until: datetime | None = None
        self.tracker = CommandTracker()
        self.movements = MovementWatch()
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._unsubs: list[CALLBACK_TYPE] = []
        self._timers: dict[str, CALLBACK_TYPE] = {}
        self._timer_due: dict[str, datetime] = {}
        self._evening_cache: dict[tuple[EveningSettings, date], tuple[datetime, datetime]] = {}
        self._rng = random.Random()
        # cover -> (window id, target, reason, attempt), sent with the command spacing
        self._queue: dict[str, tuple[str, int, str, int]] = {}
        self._outdoor_last: float | None = None
        release = float(self.opt(CONF_PROTECTION_RELEASE)) * 60
        self.guards: dict[str, Guard] = {kind: Guard(release) for kind in KINDS}
        self._build()

    # ------------------------------------------------------------------ config

    @property
    def opts(self) -> dict[str, Any]:
        return {**self._defaults, **self.config_entry.options}

    def opt(self, key: str) -> Any:
        return self.opts.get(key, self._defaults.get(key))

    @property
    def language(self) -> str:
        return resolve_language(self.opt(CONF_LANGUAGE), self.hass.config.language)

    @property
    def tz(self) -> tzinfo:
        return dt_util.get_default_time_zone()

    @property
    def observer(self) -> Observer:
        config = self.hass.config
        return Observer(config.latitude, config.longitude, config.elevation or 0)

    @property
    def global_evening(self) -> EveningSettings:
        return EveningSettings(
            parse_time(self.opt(CONF_EVENING_EARLIEST), "17:00"),
            float(self.opt(CONF_EVENING_ELEVATION)),
            parse_time(self.opt(CONF_EVENING_LATEST), "21:00"),
        )

    def _build(self) -> None:
        for sub_id, sub in self.config_entry.subentries.items():
            if sub.subentry_type != SUBENTRY_GROUP:
                continue
            data = {**GROUP_DEFAULTS, **sub.data}
            self.groups[sub_id] = Group(
                sub_id,
                sub.title,
                float(data[CONF_AZIMUTH_FROM]),
                float(data[CONF_AZIMUTH_TO]),
                {kind: list(data.get(key) or []) for kind, key in SENSOR_KINDS.items()},
            )
        for sub_id, sub in self.config_entry.subentries.items():
            if sub.subentry_type == SUBENTRY_WINDOW:
                self.windows[sub_id] = self._build_window(sub_id, sub.title, dict(sub.data))

    def _build_window(self, window_id: str, title: str, data: dict[str, Any]) -> Window:
        conf = {**self._window_defaults, **data}
        morning_settings = None
        if conf[CONF_MORNING]:
            morning_settings = mo.MorningSettings(
                mode=str(conf[CONF_MORNING_MODE]),
                earliest=parse_time(conf[CONF_MORNING_EARLIEST], "06:00"),
                latest=parse_time(conf[CONF_MORNING_LATEST], "09:00"),
                workday_time=parse_time(conf[CONF_MORNING_WORKDAY], "06:30"),
                weekend_time=parse_time(conf[CONF_MORNING_WEEKEND], "08:00"),
                sun_event=str(conf[CONF_MORNING_SUN_EVENT]),
                sun_elevation=float(conf[CONF_MORNING_SUN_ELEVATION]),
                sun_offset=float(conf[CONF_MORNING_SUN_OFFSET]),
                trigger_offset=float(conf[CONF_MORNING_TRIGGER_OFFSET]),
            )
        evening_settings = None
        if conf[CONF_EVENING_CUSTOM]:
            evening_settings = EveningSettings(
                parse_time(conf.get(CONF_EVENING_EARLIEST), str(self.opt(CONF_EVENING_EARLIEST))),
                float(conf.get(CONF_EVENING_ELEVATION, self.opt(CONF_EVENING_ELEVATION))),
                parse_time(conf.get(CONF_EVENING_LATEST), str(self.opt(CONF_EVENING_LATEST))),
            )
        group_id = conf.get(CONF_GROUP) or None
        return Window(
            window_id=window_id,
            name=title,
            cover=str(conf[CONF_COVER]),
            sensors=list(conf.get(CONF_WINDOW_SENSORS) or []),
            tilt_sensors=list(conf.get(CONF_TILT_SENSORS) or []),
            group_id=group_id,
            conf=conf,
            rules=rules.WindowRules(
                sun_position=int(conf[CONF_SUN_POSITION]),
                tolerance=int(conf[CONF_TOLERANCE]),
                auto_up=bool(conf[CONF_AUTO_UP]),
                notify_open=bool(conf[CONF_NOTIFY_OPEN]),
                manual_max_position=int(conf[CONF_MANUAL_MAX]),
                manual_at_sun_position=bool(conf[CONF_MANUAL_AT_SUN]),
                override_ignore_evening=bool(conf[CONF_OVERRIDE_IGNORE_EVENING]),
                evening_close=bool(conf[CONF_EVENING_CLOSE]),
                evening_position=int(conf[CONF_EVENING_POSITION]),
                follow_up_close=bool(conf[CONF_FOLLOW_UP_CLOSE]),
                ventilation=bool(conf[CONF_VENTILATION]),
                ventilation_position=int(conf[CONF_VENT_POSITION]),
                closed_position=int(conf[CONF_CLOSED_POSITION]),
                trigger_min_position=int(conf[CONF_TRIGGER_MIN_POSITION]),
                vacation=bool(conf[CONF_VACATION]),
                morning=bool(conf[CONF_MORNING]),
                morning_position=int(conf[CONF_MORNING_POSITION]),
                morning_sun_position=bool(conf[CONF_MORNING_SUN_POSITION]),
                wind_position=_int(conf.get(CONF_WIND_POSITION)),
                rain_position=_int(conf.get(CONF_RAIN_POSITION)),
                frost_position=_int(conf.get(CONF_FROST_POSITION)),
                lockout=bool(conf[CONF_LOCKOUT]),
            ),
            evening_settings=evening_settings,
            morning_settings=morning_settings,
            temp_hold=Hold(float(conf[CONF_TEMP_HOLD]) * 60),
            live_hold=Hold(float(conf[CONF_SUN_HOLD]) * 60),
            no_temp=FollowUp(float(conf[CONF_MANUAL_FOLLOW_UP]) * 60),
            morning_hold=Hold(float(conf[CONF_MORNING_LUX_HOLD]) * 60),
        )

    # ------------------------------------------------------------------ setup

    async def _async_update_data(self) -> None:
        return None

    async def async_setup(self) -> None:
        """Load stored state, register listeners and timers."""
        stored = await self._store.async_load() or {}
        self._restore(stored)
        now = dt_util.now()
        for win in self.windows.values():
            self._set_contact(win)
            win.trigger.active = self._trigger_active(win)
        self._update_issues()
        self._register_listeners()
        self._schedule_daily()
        if self.hass.state is not CoreState.running:
            delay = float(self.opt(CONF_STARTUP_DELAY))
            self.startup_until = now + timedelta(minutes=delay)
            self._schedule("startup", self.startup_until, self._startup_finished)
        self._unsubs.append(async_at_started(self.hass, self._async_started))
        for win in self.windows.values():
            self._refresh(win, now)
            self._schedule_window(win, now)
        for group in self.groups.values():
            self._schedule_sector(group, now)
        self._schedule_global_evening(now)
        self._update_protection(now)
        if self.startup_until is None:
            # reload while running: no restart protection, evaluate right away
            for win in self.windows.values():
                self._evaluate(win, now)

    async def _async_started(self, _hass: HomeAssistant) -> None:
        """Home Assistant is running: get the forecast if today's is missing.

        Also without a night low (e.g. stored by a version before 0.3.0), so the
        warm night check applies today and not only after the next day change.
        The restart protection counts from now on: devices report only after the start.
        """
        if self.startup_until is not None:
            delay = float(self.opt(CONF_STARTUP_DELAY))
            self.startup_until = dt_util.now() + timedelta(minutes=delay)
            self._schedule("startup", self.startup_until, self._startup_finished)
        if self.forecast_day != self._sun_day(dt_util.now()) or self.forecast_night_low is None:
            await self.async_update_forecast()

    def _restore(self, stored: dict[str, Any]) -> None:
        self.automatic = bool(stored.get("automatic", True))
        self.forecast_day = _to_date(stored.get("forecast_day"))
        self.forecast_max = as_float(stored.get("forecast_max"))
        self.forecast_night_low = as_float(stored.get("forecast_night_low"))
        self.raised_day = _to_date(stored.get("raised_day"))
        self.vacation_evening_day = _to_date(stored.get("vacation_evening_day"))
        for kind, data in (stored.get("protection") or {}).items():
            if (guard := self.guards.get(kind)) is not None and data.get("active"):
                guard.active = True
                guard.release_due = as_float(data.get("release_due"))
        windows = stored.get("windows") or {}
        now = dt_util.utcnow()
        for wid, win in self.windows.items():
            data = windows.get(wid) or {}
            until = _to_datetime(data.get("override_until"))
            sunrise_only = bool(data.get("override_sunrise"))
            if (until is not None and until > now) or (until is None and sunrise_only):
                win.override_until = until
                win.override_since = _to_datetime(data.get("override_since"))
                win.override_sunrise = sunrise_only
            win.sun_day = _to_date(data.get("sun_day"))
            win.notified_day = _to_date(data.get("notified_day"))
            win.evening_day = _to_date(data.get("evening_day"))
            win.morning_day = _to_date(data.get("morning_day"))
            win.last_manual = _to_datetime(data.get("last_manual"))
            win.last_reason = data.get("last_reason") or {}
            win.automatic = bool(data.get("automatic", True))
            win.sun_enabled = bool(data.get("sun_enabled", True))
            locked = _to_datetime(data.get("trigger_locked_until"))
            if locked is not None and locked > now:
                win.trigger.locked_until = locked
                win.trigger.pending = bool(data.get("trigger_pending"))

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "automatic": self.automatic,
            "forecast_day": _iso(self.forecast_day),
            "forecast_max": self.forecast_max,
            "forecast_night_low": self.forecast_night_low,
            "raised_day": _iso(self.raised_day),
            "vacation_evening_day": _iso(self.vacation_evening_day),
            "protection": {
                kind: {"active": guard.active, "release_due": guard.release_due}
                for kind, guard in self.guards.items()
            },
            "windows": {
                wid: {
                    "override_until": _iso(win.override_until),
                    "override_since": _iso(win.override_since),
                    "override_sunrise": win.override_sunrise if win.override_active else False,
                    "sun_day": _iso(win.sun_day),
                    "notified_day": _iso(win.notified_day),
                    "evening_day": _iso(win.evening_day),
                    "morning_day": _iso(win.morning_day),
                    "last_manual": _iso(win.last_manual),
                    "last_reason": win.last_reason,
                    "trigger_locked_until": _iso(win.trigger.locked_until),
                    "trigger_pending": win.trigger.pending,
                    "automatic": win.automatic,
                    "sun_enabled": win.sun_enabled,
                }
                for wid, win in self.windows.items()
            },
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 5)

    async def async_shutdown(self) -> None:
        self._shutdown = True
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for unsub in self._timers.values():
            unsub()
        self._timers.clear()
        await self._store.async_save(self._data_to_save())
        await super().async_shutdown()

    def _update_issues(self) -> None:
        wanted = {
            f"{ISSUE_MISSING_GROUP}{win.window_id}"
            for win in self.windows.values()
            if win.group_id and win.group_id not in self.groups
        }
        # also the issues of windows deleted in the meantime
        for domain, issue_id in list(ir.async_get(self.hass).issues):
            if (
                domain == DOMAIN
                and issue_id.startswith(ISSUE_MISSING_GROUP)
                and issue_id not in wanted
            ):
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        for win in self.windows.values():
            issue_id = f"{ISSUE_MISSING_GROUP}{win.window_id}"
            if issue_id in wanted:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_group",
                    translation_placeholders={"window": win.name},
                )

    # ------------------------------------------------------------------ listeners

    def _register_listeners(self) -> None:
        def track(entities: set[str], handler: Callable[[Event[EventStateChangedData]], None]):
            entities.discard("")
            if entities:
                self._unsubs.append(
                    async_track_state_change_event(self.hass, sorted(entities), handler)
                )

        outdoor = self._outdoor_entity
        self._outdoor_last = self.outdoor_temperature
        track({outdoor} if outdoor else set(), self._on_outdoor)
        sensors = {e for g in self.groups.values() for lst in g.sensors.values() for e in lst}
        track(sensors, self._on_sun_sensor)
        track(
            {e for w in self.windows.values() for e in (*w.sensors, *w.tilt_sensors)},
            self._on_window_sensor,
        )
        weather = {
            str(self.opt(key)) for key in (CONF_WIND_ENTITY, CONF_RAIN_ENTITY) if self.opt(key)
        }
        track(weather, self._on_weather)
        track({w.cover for w in self.windows.values()}, self._on_cover)
        blocks = {
            str(w.conf.get(e))
            for w in self.windows.values()
            for e in (CONF_OPEN_BLOCK, CONF_WINDOW_EXCEPTION)
            if w.conf.get(e)
        }
        track(blocks, self._on_block)
        track(
            {e for w in self.windows.values() for e in w.conf.get(CONF_TRIGGER_ENTITIES) or []},
            self._on_trigger,
        )
        morning = {
            str(w.conf.get(CONF_MORNING_TRIGGER))
            for w in self.windows.values()
            if w.morning_settings and w.conf.get(CONF_MORNING_TRIGGER)
        }
        workday = self.opt(CONF_WORKDAY)
        track(morning | ({workday} if workday else set()), self._on_morning_input)
        heat_inputs = {
            str(w.conf.get(key))
            for w in self.windows.values()
            for key in (CONF_ROOM_ENTITY, CONF_COOLING_ENTITY)
            if w.conf.get(key)
        }
        heating = self.opt(CONF_HEATING_ENTITY)
        track(heat_inputs | ({heating} if heating else set()), self._on_heat_input)

    def _schedule_daily(self) -> None:
        def daily(value: Any, fallback: str, handler: Callable[[datetime], None]) -> None:
            moment = parse_time(value, fallback)
            self._unsubs.append(
                async_track_time_change(
                    self.hass,
                    handler,
                    hour=moment.hour,
                    minute=moment.minute,
                    second=moment.second,
                )
            )

        daily(self.opt(CONF_DAY_CHANGE), "01:00", self._on_day_change)
        daily(self.opt(CONF_NIGHT_END), "03:30", self._on_night_end)
        daily(self.opt(CONF_VAC_MORNING), "07:00", self._on_vacation_morning)
        daily(self.opt(CONF_VAC_EVENING), "19:00", self._on_vacation_evening)
        self._unsubs.append(async_track_sunrise(self.hass, self._on_sunrise))

    def _schedule(
        self, key: str, when: datetime | None, handler: Callable[[datetime], Any]
    ) -> None:
        """Run ``handler`` at ``when`` (replaces a timer with the same key)."""
        if when is not None and key in self._timers and self._timer_due.get(key) == when:
            return
        self._cancel(key)
        if when is None or self._shutdown:
            return

        @callback
        def fire(now: datetime) -> None:
            self._timers.pop(key, None)
            self._timer_due.pop(key, None)
            handler(now)

        self._timers[key] = async_track_point_in_time(self.hass, fire, when)
        self._timer_due[key] = when

    def _cancel(self, key: str) -> None:
        self._timer_due.pop(key, None)
        if (old := self._timers.pop(key, None)) is not None:
            old()

    # ------------------------------------------------------------------ helpers

    def _state(self, entity_id: str | None) -> State | None:
        return self.hass.states.get(entity_id) if entity_id else None

    def _state_value(self, entity_id: str | None) -> str | None:
        state = self._state(entity_id)
        return state.state if state else None

    @property
    def _outdoor_entity(self) -> str | None:
        """Outdoor temperature sensor, or the weather entity without one."""
        return self.opt(CONF_OUTDOOR_TEMP) or self.opt(CONF_WEATHER) or None

    @property
    def outdoor_temperature(self) -> float | None:
        state = self._state(self._outdoor_entity)
        if state is None or state.state in INVALID:
            return None
        if state.domain == "weather":
            return as_float(state.attributes.get("temperature"))
        return as_float(state.state)

    def _position(self, win: Window) -> int | None:
        state = self._state(win.cover)
        if state is None or state.state in INVALID:
            return None
        position = as_float(state.attributes.get("current_position"))
        if position is not None:
            return round(position)
        if state.state == "open":
            return rules.OPEN
        if state.state == "closed":
            return rules.CLOSED
        return None

    def _contact(self, win: Window) -> str:
        """Open, tilted or closed. A contact not reporting closed counts as open
        (unknown is not safe), a tilt contact as tilted."""
        return window_contact(
            [self._state_value(e) for e in win.sensors],
            [self._state_value(e) for e in win.tilt_sensors],
        )

    def _window_open_now(self, win: Window) -> bool:
        return self._contact(win) == CONTACT_OPEN

    def _set_contact(self, win: Window) -> bool:
        """Store the contact state of the window. True if it changed."""
        contact = self._contact(win)
        state = (contact == CONTACT_OPEN, contact == CONTACT_TILTED)
        changed = state != (win.window_open, win.window_tilted)
        win.window_open, win.window_tilted = state
        return changed

    def _window_exception(self, win: Window) -> bool:
        entity = win.conf.get(CONF_WINDOW_EXCEPTION)
        state = self._state(entity)
        return bool(entity) and state is not None and state.state not in INVALID

    def _open_blocked(self, win: Window) -> bool:
        entity = win.conf.get(CONF_OPEN_BLOCK)
        if not entity:
            return False
        value = self._state_value(entity) or STATE_UNAVAILABLE
        return value not in (win.conf.get(CONF_OPEN_BLOCK_FREE) or [])

    def _trigger_active(self, win: Window) -> bool:
        active = win.conf.get(CONF_TRIGGER_ACTIVE) or []
        return any(
            self._state_value(e) in active for e in win.conf.get(CONF_TRIGGER_ENTITIES) or []
        )

    @property
    def vacation(self) -> bool:
        return any(self._state_value(e) == STATE_ON for e in self.opt(CONF_VACATION_ENTITIES) or [])

    def _sun_day(self, now: datetime) -> date:
        change = parse_time(self.opt(CONF_DAY_CHANGE), "01:00")
        local = dt_util.as_local(now)
        if local.time() < change:
            return local.date() - timedelta(days=1)
        return local.date()

    def _evening_day(self, now: datetime) -> date:
        return evening_day(dt_util.as_local(now), parse_time(self.opt(CONF_NIGHT_END), "03:30"))

    @property
    def summer(self) -> bool:
        today = self._sun_day(dt_util.now())
        # Without today's forecast the last known value counts (as before) until the
        # retry succeeds.
        return summer_day(
            self.forecast_max,
            float(self.opt(CONF_SUMMER_THRESHOLD)),
            self.raised_day == today,
            self.forecast_night_low,
            self._night_threshold,
        )

    @property
    def _night_threshold(self) -> float | None:
        return as_float(self.opt(CONF_NIGHT_THRESHOLD))

    @property
    def heating_day(self) -> bool:
        """The heating entity is on: the warmth of the sun is welcome."""
        return self._state_value(self.opt(CONF_HEATING_ENTITY)) == STATE_ON

    def _evening_window(self, settings: EveningSettings, day: date) -> tuple[datetime, datetime]:
        """Start and end of the evening of ``day`` (cached, the sun is the same all day)."""
        if (cached := self._evening_cache.get((settings, day))) is not None:
            return cached
        tz = self.tz
        below = sunlib.time_at_elevation(self.observer, day, settings.elevation, False, tz)
        start = evening_start(day, tz, settings, below)
        rise = sunlib.sunrise(self.observer, day + timedelta(days=1), tz)
        end = evening_end(day, tz, parse_time(self.opt(CONF_NIGHT_END), "03:30"), rise)
        if len(self._evening_cache) > 64:
            self._evening_cache.clear()
        self._evening_cache[(settings, day)] = (start, end)
        return start, end

    def evening_active(self, settings: EveningSettings, now: datetime) -> bool:
        start, end = self._evening_window(settings, self._evening_day(now))
        return is_evening(dt_util.as_local(now), start, end)

    def _evening(self, win: Window, now: datetime) -> bool:
        if self.evening_active(win.evening_settings or self.global_evening, now):
            return True
        return win.rules.vacation and self.vacation_evening_day == self._evening_day(now)

    @property
    def global_evening_active(self) -> bool:
        now = dt_util.now()
        return self.evening_active(self.global_evening, now) or (
            self.vacation_evening_day == self._evening_day(now)
        )

    def global_evening_times(self) -> tuple[datetime, datetime]:
        """Start and end of the current (or next) evening with the global settings."""
        return self._evening_window(self.global_evening, self._evening_day(dt_util.now()))

    def _startup(self, now: datetime) -> bool:
        return self.startup_until is not None and now < self.startup_until

    # ------------------------------------------------------------------ state of a window

    def _sector(self, win: Window, now: datetime) -> tuple[bool, bool]:
        group = self.groups.get(win.group_id or "")
        if group is None:
            return False, False
        az = sunlib.azimuth(self.observer, now)
        return (
            sunlib.in_sector(az, group.azimuth_from, group.azimuth_to),
            sunlib.past_sector_end(az, group.azimuth_from, group.azimuth_to),
        )

    def _sensor_values(self, group: Group) -> dict[str, list[str | None]]:
        return {
            kind: [self._state_value(e) for e in entities]
            for kind, entities in group.sensors.items()
            if entities
        }

    def _thresholds(self, win: Window) -> dict[str, float]:
        return {kind: float(win.conf[key]) for kind, key in THRESHOLD_KEYS.items()}

    def _refresh(self, win: Window, now: datetime) -> bool:
        """Update the time based conditions of a window. True if a condition changed."""
        ts = now.timestamp()
        group = self.groups.get(win.group_id or "")
        outdoor = self.outdoor_temperature
        win.temp_hold.update(at_least(outdoor, float(win.conf[CONF_TEMP_THRESHOLD])), ts)
        temp_ok = win.temp_hold.state(ts)
        sens = group is not None and sensors_ok(self._sensor_values(group), self._thresholds(win))
        in_sector, past_end = self._sector(win, now)
        summer = self.summer
        heat = self._heat_need(win)
        win.live_hold.update(group is not None and summer and temp_ok and sens and heat, ts)
        win.no_temp.update(group is not None and summer and in_sector and sens, ts)
        live = win.live_hold.state(ts)
        no_temp = win.no_temp.state(ts)
        morning_ok = False
        if win.morning_settings and win.morning_settings.mode == mo.MODE_BRIGHTNESS and group:
            lux = {"lux": [self._state_value(e) for e in group.sensors.get("lux", [])]}
            win.morning_hold.update(
                bool(lux["lux"]) and sensors_ok(lux, {"lux": float(win.conf[CONF_MORNING_LUX])}),
                ts,
            )
            morning_ok = win.morning_hold.state(ts)
        dues = [
            d
            for d in (
                win.temp_hold.due(ts),
                win.live_hold.due(ts),
                win.no_temp.due(ts),
                win.morning_hold.due(ts) if win.morning_settings else None,
            )
            if d is not None
        ]
        self._schedule(
            f"{win.window_id}:hold",
            dt_util.utc_from_timestamp(min(dues)) if dues else None,
            lambda now, wid=win.window_id: self._on_hold_due(wid, now),
        )
        flags = (temp_ok, sens, live, no_temp, in_sector, past_end, morning_ok, heat)
        changed = flags != win.flags
        win.flags = flags
        return changed

    def _room(self, win: Window) -> tuple[float | None, float | None]:
        """Room temperature and setpoint (setpoint only from a thermostat)."""
        state = self._state(win.conf.get(CONF_ROOM_ENTITY))
        if state is None or state.state in INVALID:
            return None, None
        if state.domain == "climate":
            return (
                as_float(state.attributes.get("current_temperature")),
                as_float(state.attributes.get("temperature")),
            )
        return as_float(state.state), None

    def room_warm(self, win: Window) -> bool | None:
        """Is the room too warm? None without a room entity or value."""
        current, setpoint = self._room(win)
        return room_warm(
            current,
            setpoint,
            float(win.conf[CONF_ROOM_MARGIN]),
            float(win.conf[CONF_ROOM_THRESHOLD]),
        )

    def cooling(self, win: Window) -> bool:
        """The air conditioner of the window cools."""
        state = self._state(win.conf.get(CONF_COOLING_ENTITY))
        if state is None:
            return False
        return cooling_active(
            state.state,
            state.attributes.get("hvac_action"),
            as_float(state.attributes.get("current_temperature")),
            as_float(state.attributes.get("temperature")),
        )

    def _heat_need(self, win: Window) -> bool:
        return heat_need(self.room_warm(win), self.cooling(win), self.heating_day)

    def heat_ok(self, win: Window) -> bool:
        return bool(len(win.flags) > 7 and win.flags[7])

    @property
    def _now_ts(self) -> float:
        return dt_util.utcnow().timestamp()

    def temp_ok(self, win: Window) -> bool:
        return bool(win.flags and win.flags[0])

    def sensors_ok(self, win: Window) -> bool:
        return bool(win.flags and win.flags[1])

    def live(self, win: Window) -> bool:
        return bool(win.flags and win.flags[2])

    def in_sector(self, win: Window) -> bool:
        return bool(win.flags and win.flags[4])

    def sun_marker(self, win: Window, now: datetime | None = None) -> bool:
        return win.sun_day is not None and win.sun_day == self._sun_day(now or dt_util.now())

    def evening_marker(self, win: Window, now: datetime | None = None) -> bool:
        return win.evening_day is not None and win.evening_day == self._evening_day(
            now or dt_util.now()
        )

    def _notified(self, win: Window, now: datetime) -> bool:
        return win.notified_day == self._sun_day(now)

    def _situation(self, win: Window, now: datetime) -> rules.Situation:
        flags = win.flags or (False,) * 8
        return rules.Situation(
            automatic=self.automatic and win.automatic,
            startup=self._startup(now),
            position=self._position(win),
            window_open=win.window_open,
            window_on=reported_open([self._state_value(e) for e in win.sensors]),
            window_exception=self._window_exception(win),
            override=win.override_active,
            sun_marker=self.sun_marker(win, now),
            evening_marker=self.evening_marker(win, now),
            notified=self._notified(win, now),
            live=flags[2],
            no_temp=flags[3],
            in_sector=flags[4],
            past_sector_end=flags[5],
            evening=self._evening(win, now),
            open_blocked=self._open_blocked(win),
            vacation=self.vacation,
            protection=win.protection,
            frost=self.guards[FROST].active,
            window_tilted=win.window_tilted,
            sun_enabled=win.sun_enabled,
        )

    def status(self, win: Window) -> str:
        return rules.status(win.rules, self._situation(win, dt_util.now()))

    def sun_details(self, win: Window) -> dict[str, Any]:
        """Thresholds, sensors and pending hold times of the sun condition (read only)."""
        ts = dt_util.utcnow().timestamp()

        def at(due: float | None) -> str | None:
            return dt_util.as_local(dt_util.utc_from_timestamp(due)).isoformat() if due else None

        room, setpoint = self._room(win)
        details: dict[str, Any] = {
            "summer_day": self.summer,
            "forecast_max": self.forecast_max,
            "summer_threshold": float(self.opt(CONF_SUMMER_THRESHOLD)),
            "raised_by_outdoor_temperature": self.raised_day == self._sun_day(dt_util.now()),
            "night_low": self.forecast_night_low,
            "night_threshold": self._night_threshold,
            "heat_need": self.heat_ok(win),
            "room_entity": win.conf.get(CONF_ROOM_ENTITY),
            "room_temperature": room,
            "room_setpoint": setpoint,
            "room_limit": (
                setpoint + float(win.conf[CONF_ROOM_MARGIN])
                if setpoint is not None
                else float(win.conf[CONF_ROOM_THRESHOLD])
            ),
            "room_warm": self.room_warm(win),
            "cooling_entity": win.conf.get(CONF_COOLING_ENTITY),
            "cooling": self.cooling(win),
            "heating_entity": self.opt(CONF_HEATING_ENTITY),
            "heating_day": self.heating_day,
            "temperature_sensor": self._outdoor_entity,
            "outdoor_temperature": self.outdoor_temperature,
            "temperature_unit": self.temperature_unit,
            "temperature_threshold": float(win.conf[CONF_TEMP_THRESHOLD]),
            "temperature_hold": float(win.conf[CONF_TEMP_HOLD]),
            "temperature_ok": self.temp_ok(win),
            "temperature_ok_at": at(win.temp_hold.due(ts)),
            "sensors_ok": self.sensors_ok(win),
            "sun_hold": float(win.conf[CONF_SUN_HOLD]),
            "condition_on_at": at(win.live_hold.due(ts)),
            "in_sector": self.in_sector(win),
            "sun_position": win.rules.sun_position,
            "position_tolerance": win.rules.tolerance,
            "auto_up": win.rules.auto_up,
        }
        if (group := self.groups.get(win.group_id or "")) is not None:
            details["group"] = group.name
            details["azimuth_from"] = group.azimuth_from
            details["azimuth_to"] = group.azimuth_to
            details["sensors"] = {
                kind: {"entities": entities, "threshold": float(win.conf[THRESHOLD_KEYS[kind]])}
                for kind, entities in group.sensors.items()
                if entities
            }
        return details

    def window_details(self, win: Window) -> dict[str, Any]:
        """Cover, contacts, evening and override of a window (read only)."""
        now = dt_util.now()
        settings = win.evening_settings or self.global_evening
        start, end = self._evening_window(settings, self._evening_day(now))
        return {
            "cover": win.cover,
            "window_sensors": win.sensors,
            "window_open": win.window_open,
            "window_tilted": win.window_tilted,
            "protection": win.protection,
            "frost": self.guards[FROST].active,
            "evening": self._evening(win, now),
            "evening_start": start.isoformat(),
            "evening_end": end.isoformat(),
            "override_until": _iso(win.override_until) if win.override_active else None,
            "open_block_entity": win.conf.get(CONF_OPEN_BLOCK),
            "open_blocked": self._open_blocked(win),
        }

    # ------------------------------------------------------------------ actions

    def _apply(self, win: Window, actions: list[rules.Action], now: datetime) -> None:
        """Execute actions: markers synchronously, movements and pushes as a task."""
        if not actions:
            return
        moves: list[tuple[int, str]] = []
        notify = False
        situation: rules.Situation | None = None
        for action in actions:
            if action.kind == rules.POSITION and action.position is not None:
                situation = situation or self._situation(win, now)
                target = rules.limit_target(
                    win.rules, situation, action.position, action.reason in PROTECTIVE
                )
                if target is not None:
                    moves.append((target, action.reason))
            elif action.kind == rules.MARK_SUN:
                win.sun_day = self._sun_day(now)
            elif action.kind == rules.CLEAR_SUN:
                win.sun_day = None
            elif action.kind == rules.MARK_EVENING:
                win.evening_day = self._evening_day(now)
            elif action.kind == rules.CLEAR_EVENING:
                win.evening_day = None
            elif action.kind == rules.NOTIFY:
                win.notified_day = self._sun_day(now)
                notify = True
        reason = actions[0].reason
        position = moves[-1][0] if moves else None
        self._set_reason(win, reason, position, now)
        for target, move_reason in moves:
            self._start_move(win, target, move_reason)
        if notify:
            self._notify_window_open(win)
        self._save()
        self.async_update_listeners()

    def _set_reason(self, win: Window, reason: str, position: int | None, now: datetime) -> None:
        key = reason
        if position and text(self.language, f"{reason}_partial") != f"{reason}_partial":
            key = f"{reason}_partial"
        message = text(self.language, key, position=position, name=win.name)
        win.last_reason = {
            "code": reason,
            "message": message,
            "position": position,
            "time": now.isoformat(),
        }
        self.hass.bus.async_fire(
            EVENT_LOGBOOK, {"name": win.name, "message": message, ATTR_ENTITY_ID: win.cover}
        )

    def _start_move(self, win: Window, target: int, reason: str, attempt: int = 0) -> None:
        """Queue a command; the queue keeps the spacing between commands."""
        state = self._state(win.cover)
        if state is None or state.state in INVALID:
            return
        if self._position(win) == target and state.state not in MOVING:
            win.verify = None
            return
        # only the latest command per cover counts
        self._queue.pop(win.cover, None)
        self._queue[win.cover] = (win.window_id, target, reason, attempt)
        self._drain()

    @callback
    def _drain(self, _now: datetime | None = None) -> None:
        """Send queued commands, one per command spacing (all at once without)."""
        interval = float(self.opt(CONF_COMMAND_INTERVAL))
        while self._queue and "queue" not in self._timers:
            cover = next(iter(self._queue))
            window_id, target, reason, attempt = self._queue.pop(cover)
            win = self.windows.get(window_id)
            if win is None or not self._send(win, target, reason, attempt):
                continue
            if interval > 0:
                self._schedule("queue", dt_util.utcnow() + timedelta(seconds=interval), self._drain)

    def _send(self, win: Window, target: int, reason: str, attempt: int) -> bool:
        """Call the cover service. False if nothing was sent."""
        state = self._state(win.cover)
        if state is None or state.state in INVALID:
            return False
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES) or 0)
        data: dict[str, Any] = {ATTR_ENTITY_ID: win.cover}
        if target >= rules.OPEN:
            service = "open_cover"
        elif target <= rules.CLOSED:
            service = "close_cover"
        elif features & CoverEntityFeature.SET_POSITION:
            service = "set_cover_position"
            data["position"] = target
        else:
            LOGGER.warning("%s cannot move to %s %% (no position support)", win.cover, target)
            return False
        context = Context()
        self.tracker.register(win.cover, target, context.id, self._now_ts)
        self._create_task(self._async_call("cover", service, data, context), "cover")
        self.hass.bus.async_fire(
            EVENT_COVER_MOVED,
            {
                "window": win.name,
                "window_id": win.window_id,
                ATTR_ENTITY_ID: win.cover,
                "position": target,
                "reason": reason,
            },
            context=context,
        )
        verify_after = float(self.opt(CONF_VERIFY_AFTER))
        if verify_after > 0:
            win.verify = (target, reason, attempt)
            win.verify_waited = False
            self._schedule(
                f"{win.window_id}:verify",
                dt_util.utcnow() + timedelta(seconds=verify_after),
                lambda now, wid=win.window_id: self._on_verify(wid, now),
            )
        return True

    @callback
    def _on_verify(self, window_id: str, now: datetime) -> None:
        """Repeat a command once if the cover did not reach its target, then report."""
        win = self.windows.get(window_id)
        if win is None or win.verify is None:
            return
        target, reason, attempt = win.verify
        state = self._state(win.cover)
        if state is not None and state.state in MOVING and not win.verify_waited:
            # still moving: look once more later
            win.verify_waited = True
            self._schedule(
                f"{win.window_id}:verify",
                now + timedelta(seconds=float(self.opt(CONF_VERIFY_AFTER))),
                lambda now, wid=window_id: self._on_verify(wid, now),
            )
            return
        win.verify = None
        current = self._position(win)
        if reached(target, current, state.state if state else None):
            return
        if attempt == 0:
            self._set_reason(win, "cover_retry", target, now)
            self._start_move(win, target, reason, attempt=1)
            return
        self._set_reason(win, "cover_failed", target, now)
        self.hass.bus.async_fire(
            EVENT_COVER_FAILED,
            {
                "window": win.name,
                "window_id": win.window_id,
                ATTR_ENTITY_ID: win.cover,
                "position": target,
                "current_position": current,
                "reason": reason,
            },
        )
        self._create_task(
            self._async_notify(
                text(self.language, "notify_failed_title"),
                text(self.language, "notify_cover_failed", name=win.name, position=target),
            ),
            "notify",
        )
        self.async_update_listeners()

    def _create_task(self, coro: Any, name: str) -> None:
        """Task bound to the config entry (waited for when the entry unloads)."""
        if self._shutdown:
            coro.close()
            return
        self.config_entry.async_create_task(self.hass, coro, f"{DOMAIN} {name}")

    async def _async_call(
        self, domain: str, service: str, data: dict[str, Any], context: Context | None = None
    ) -> None:
        try:
            await self.hass.services.async_call(domain, service, data, context=context)
        except (HomeAssistantError, ValueError) as err:
            LOGGER.warning("%s.%s failed: %s", domain, service, err)

    def _notify_window_open(self, win: Window) -> None:
        title = text(self.language, "notify_title")
        message = text(self.language, "notify_window_open", name=win.name)
        self._create_task(self._async_notify(title, message), "notify")

    async def _async_notify(self, title: str, message: str) -> None:
        for target in self.opt(CONF_NOTIFY) or []:
            domain, _, service = str(target).partition(".")
            if not service:
                domain, service = "notify", domain
            if domain != "notify":
                # only notification services (others are refused when saving)
                LOGGER.warning("%s is not a notification service, skipped", target)
                continue
            await self._async_call(domain, service, {"title": title, "message": message})

    # ------------------------------------------------------------------ evaluation

    def _evaluate(self, win: Window, now: datetime) -> None:
        """State based rules: sun protection, push, auto up."""
        self._apply(win, rules.sun(win.rules, self._situation(win, now)), now)

    def _evaluate_all(self, now: datetime) -> None:
        for win in self.windows.values():
            self._refresh(win, now)
            self._evaluate(win, now)
        self.async_update_listeners()

    @callback
    def _on_hold_due(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None:
            return
        if self._refresh(win, now):
            self._evaluate(win, now)
            self._check_morning_brightness(win, now)
            self.async_update_listeners()

    @callback
    def _on_outdoor(self, _event: Event[EventStateChangedData]) -> None:
        now = dt_util.now()
        # sensor state or the temperature attribute of the weather entity
        value = self.outdoor_temperature
        threshold = float(self.opt(CONF_SUMMER_THRESHOLD))
        previous = self._outdoor_last
        self._outdoor_last = value
        # Rising above the threshold during the day makes it a summer day.
        crossed = value is not None and value > threshold
        today = self._sun_day(now)
        if crossed and (previous is None or previous <= threshold) and self.raised_day != today:
            self.raised_day = today
            self._save()
        changed = False
        for win in self.windows.values():
            if self._refresh(win, now):
                changed = True
                self._evaluate(win, now)
        if self._update_protection(now) or changed:
            self.async_update_listeners()

    # ------------------------------------------------------------------ weather protection

    def protection_enabled(self, kind: str) -> bool:
        """Wind and rain need their sensor, frost a window with a frost position."""
        if kind == FROST:
            return any(win.rules.frost_position is not None for win in self.windows.values())
        return bool(self.opt(CONF_WIND_ENTITY if kind == WIND else CONF_RAIN_ENTITY))

    def _protection_values(self) -> dict[str, bool | None]:
        """Is each value on the dangerous side? None = invalid (keeps the state)."""
        values: dict[str, bool | None] = dict.fromkeys(KINDS, False)
        if self.protection_enabled(WIND):
            wind = self._state_value(self.opt(CONF_WIND_ENTITY))
            values[WIND] = above(wind, float(self.opt(CONF_WIND_THRESHOLD)))
        if self.protection_enabled(RAIN):
            rain = self._state_value(self.opt(CONF_RAIN_ENTITY))
            values[RAIN] = raining(rain, float(self.opt(CONF_RAIN_THRESHOLD)))
        if self.protection_enabled(FROST):
            threshold = float(self.opt(CONF_FROST_THRESHOLD))
            values[FROST] = freezing(self.outdoor_temperature, threshold)
        return values

    @property
    def active_protections(self) -> frozenset[str]:
        return frozenset(kind for kind, guard in self.guards.items() if guard.active)

    def _update_protection(self, now: datetime) -> bool:
        """Update wind, rain and frost and act on the windows. True if one changed."""
        ts = now.timestamp()
        values = self._protection_values()
        changed = False
        for kind, guard in self.guards.items():
            if guard.update(values[kind], ts):
                changed = True
                name = text(self.language, f"kind_{kind}")
                self.hass.bus.async_fire(EVENT_PROTECTION, {"kind": kind, "active": guard.active})
                self.hass.bus.async_fire(
                    EVENT_LOGBOOK,
                    {
                        "name": NAME,
                        "message": text(
                            self.language,
                            "protection_on" if guard.active else "protection_off",
                            kind=name,
                        ),
                    },
                )
            due = guard.due()
            self._schedule(
                f"protection:{kind}",
                dt_util.utc_from_timestamp(due) if due is not None else None,
                self._on_protection_due,
            )
        if changed:
            self._save()
        active = self.active_protections
        for win in self.windows.values():
            kind = rules.protection_kind(win.rules, active)
            if kind == win.protection:
                continue
            changed = True
            win.protection = kind
            if kind is not None:
                self._protect(win, now)
            else:
                self._after_protection(win, now)
        return changed

    def _protect(self, win: Window, now: datetime) -> None:
        self._apply(win, rules.protect(win.rules, self._situation(win, now)), now)

    def _after_protection(self, win: Window, now: datetime) -> None:
        """Protection ended: no old position is restored, the rules decide again."""
        self._set_reason(win, "protection_end", None, now)
        self._refresh(win, now)
        if self._evening(win, now):
            self._run_evening(win, now)
        self._evaluate(win, now)

    @callback
    def _on_weather(self, _event: Event[EventStateChangedData]) -> None:
        if self._update_protection(dt_util.now()):
            self.async_update_listeners()

    @callback
    def _on_protection_due(self, now: datetime) -> None:
        if self._update_protection(now):
            self.async_update_listeners()

    @callback
    def _on_heat_input(self, _event: Event[EventStateChangedData]) -> None:
        """Room temperature, air conditioner or heating changed."""
        now = dt_util.now()
        for win in self.windows.values():
            if self._refresh(win, now):
                self._evaluate(win, now)
        # The sun condition check shows the room values, keep it current.
        self.async_update_listeners()

    @callback
    def _on_sun_sensor(self, event: Event[EventStateChangedData]) -> None:
        now = dt_util.now()
        entity_id = event.data["entity_id"]
        changed = False
        for win in self.windows.values():
            group = self.groups.get(win.group_id or "")
            if group is None or not any(entity_id in lst for lst in group.sensors.values()):
                continue
            if self._refresh(win, now):
                changed = True
                self._evaluate(win, now)
                self._check_morning_brightness(win, now)
        if changed:
            self.async_update_listeners()

    def _schedule_sector(self, group: Group, now: datetime) -> None:
        crossings = [
            sunlib.next_azimuth_crossing(self.observer, now + timedelta(seconds=1), angle)
            for angle in (group.azimuth_from, group.azimuth_to)
        ]
        upcoming = [c for c in crossings if c is not None]
        self._schedule(
            f"sector:{group.group_id}",
            min(upcoming) + timedelta(seconds=1) if upcoming else None,
            lambda now, gid=group.group_id: self._on_sector(gid, now),
        )

    @callback
    def _on_sector(self, group_id: str, now: datetime) -> None:
        group = self.groups.get(group_id)
        if group is None:
            return
        for win in self.windows.values():
            if win.group_id == group_id:
                self._refresh(win, now)
                self._evaluate(win, now)
        self._schedule_sector(group, now)
        self.async_update_listeners()

    # ------------------------------------------------------------------ window contacts

    @callback
    def _on_window_sensor(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old = event.data["old_state"]
        new = event.data["new_state"]
        now = dt_util.now()
        for win in self.windows.values():
            if entity_id not in win.sensors and entity_id not in win.tilt_sensors:
                continue
            tilt = entity_id in win.tilt_sensors
            contact = self._contact(win)
            old_contact = window_contact(*_split(old.state if old else None, tilt))
            new_contact = window_contact(*_split(new.state if new else None, tilt))
            really_opened = (
                old is not None
                and new is not None
                and old.state not in INVALID
                and new.state not in INVALID
                and old_contact == CONTACT_CLOSED
                and new_contact != CONTACT_CLOSED
            )
            opening = contact == CONTACT_OPEN or (contact == CONTACT_TILTED and not win.window_open)
            if opening:
                self._cancel(f"{win.window_id}:close")
                if self._set_contact(win):
                    self.async_update_listeners()
                if really_opened:
                    self._window_opened(win, now)
            elif win.window_open or win.window_tilted:
                # closed (or only tilted after open): counts after the debounce time
                real = old is not None and old.state not in INVALID
                self._schedule(
                    f"{win.window_id}:close",
                    now + timedelta(seconds=float(self.opt(CONF_WINDOW_DEBOUNCE))),
                    lambda now, wid=win.window_id, r=real: self._window_closed(wid, r, now),
                )

    def _window_opened(self, win: Window, now: datetime) -> None:
        """Ventilation position: immediately in the evening, after a delay during the day."""
        evening = self._evening(win, now)
        delay = float(win.conf[CONF_VENT_DELAY_EVENING if evening else CONF_VENT_DELAY_DAY])
        self._schedule(
            f"{win.window_id}:vent",
            now + timedelta(seconds=delay),
            lambda now, wid=win.window_id: self._ventilate(wid, now),
        )

    @callback
    def _ventilate(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or self._contact(win) == CONTACT_CLOSED:
            return
        self._apply(win, rules.ventilation(win.rules, self._situation(win, now)), now)

    @callback
    def _window_closed(self, window_id: str, real: bool, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or self._window_open_now(win):
            return
        self._set_contact(win)
        situation = self._situation(win, now)
        if real:
            after = dt_util.as_local(now).time() >= parse_time(
                self.opt(CONF_FOLLOW_UP_EARLIEST), "16:00"
            )
            self._apply(win, rules.follow_up(win.rules, situation, after), now)
            situation = self._situation(win, now)
        self._apply(win, rules.manual_sun(win.rules, situation, self._recent(win, now)), now)
        self._refresh(win, now)
        self._evaluate(win, now)
        self._protect(win, now)
        if win.trigger.pending:
            self._try_trigger_close(win, now)
        self.async_update_listeners()

    # ------------------------------------------------------------------ covers and overrides

    @property
    def _next_sunrise(self) -> datetime | None:
        today = dt_util.now().date()
        for day in (today, today + timedelta(days=1), today + timedelta(days=2)):
            rise = sunlib.sunrise(self.observer, day, self.tz)
            if rise is not None and rise > dt_util.now():
                return rise
        return None

    def _recent(self, win: Window, now: datetime) -> bool:
        window = timedelta(minutes=float(win.conf[CONF_MANUAL_WINDOW]))
        state = self._state(win.cover)
        cover_changed = state.last_changed if state else None
        return any(t is not None and now - t < window for t in (win.override_since, cover_changed))

    @callback
    def _on_cover(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old = event.data["old_state"]
        new = event.data["new_state"]
        if new is None:
            return
        now = dt_util.now()
        new_pos = as_float(new.attributes.get("current_position"))
        own = self.tracker.explains(
            entity_id,
            new.context.id,
            new.state,
            round(new_pos) if new_pos is not None else None,
            now.timestamp(),
        )
        old_pos = as_float(old.attributes.get("current_position")) if old else None
        started = self.automatic and is_manual(
            own=own,
            parent_id=new.context.parent_id,
            old_state=old.state if old else None,
            new_state=new.state,
            old_position=old_pos,
            new_position=new_pos,
        )
        if self.opt(CONF_OVERRIDE_TRIGGER) == TRIGGER_COMMAND:
            manual = started
        else:
            manual = self.movements.update(
                entity_id,
                started=started,
                own=own,
                old_state=old.state if old else None,
                old_position=old_pos,
                new_state=new.state,
                new_position=new_pos,
                now=now.timestamp(),
            )
        for win in self.windows.values():
            if win.cover != entity_id:
                continue
            if manual:
                self._start_override(win, now)
            if new.state not in MOVING and new.state not in INVALID:
                situation = self._situation(win, now)
                if not own:
                    self._apply(
                        win, rules.manual_sun(win.rules, situation, self._recent(win, now)), now
                    )
                    situation = self._situation(win, now)
                self._apply(win, rules.sun_position_reached(win.rules, situation), now)
                self._evaluate(win, now)
        self.async_update_listeners()

    def _start_override(self, win: Window, now: datetime) -> None:
        duration = float(win.conf[CONF_OVERRIDE_DURATION])
        if not win.override_active:
            win.override_since = now
        win.last_manual = now
        # moved by hand: the last command no longer needs to be checked
        win.verify = None
        self._cancel(f"{win.window_id}:verify")
        win.override_until = override_until(now, duration, self._next_sunrise)
        win.override_sunrise = bool(win.conf[CONF_OVERRIDE_SUNRISE]) or duration <= 0
        until = (
            dt_util.as_local(win.override_until).strftime("%H:%M")
            if win.override_until
            else text(self.language, "until_sunrise")
        )
        self.hass.bus.async_fire(
            EVENT_LOGBOOK,
            {
                "name": win.name,
                "message": text(self.language, "override_on", until=until),
                ATTR_ENTITY_ID: win.cover,
            },
        )
        self._schedule(
            f"{win.window_id}:override",
            win.override_until,
            lambda now, wid=win.window_id: self._end_override(wid, now),
        )
        self._save()

    @callback
    def _end_override(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        # At the end time the override already counts as inactive; clean up anyway.
        if win is None or (win.override_until is None and not win.override_sunrise):
            return
        win.override_until = None
        win.override_since = None
        win.override_sunrise = False
        self._cancel(f"{win.window_id}:override")
        self.hass.bus.async_fire(
            EVENT_LOGBOOK,
            {
                "name": win.name,
                "message": text(self.language, "override_off"),
                ATTR_ENTITY_ID: win.cover,
            },
        )
        self._save()
        self._refresh(win, now)
        self._evaluate(win, now)
        self.async_update_listeners()

    @callback
    def end_override(self, window_id: str) -> bool:
        """End a running override by hand (panel). False if none is running."""
        win = self.windows.get(window_id)
        if win is None or not win.override_active:
            return False
        self._end_override(window_id, dt_util.now())
        return True

    # ------------------------------------------------------------------ open block and exception

    @callback
    def _on_block(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        now = dt_util.now()
        for win in self.windows.values():
            if entity_id not in (
                win.conf.get(CONF_OPEN_BLOCK),
                win.conf.get(CONF_WINDOW_EXCEPTION),
            ):
                continue
            self._evaluate(win, now)
            if not self._open_blocked(win):
                self._retry_morning(win, now)
        self.async_update_listeners()

    # ------------------------------------------------------------------ close trigger (e.g. TV)

    @callback
    def _on_trigger(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old = event.data["old_state"]
        new = event.data["new_state"]
        now = dt_util.now()
        for win in self.windows.values():
            if entity_id not in (win.conf.get(CONF_TRIGGER_ENTITIES) or []):
                continue
            states = win.conf.get(CONF_TRIGGER_ACTIVE) or []
            was_on = old is not None and old.state in states
            is_on = new is not None and new.state in states
            key = f"{win.window_id}:trigger_on:{entity_id}"
            if is_on and not was_on:
                # every device switching on gets its own attempt (once per cycle)
                self._schedule(
                    key,
                    now + timedelta(seconds=float(win.conf[CONF_TRIGGER_ON_DELAY])),
                    lambda now, wid=win.window_id, eid=entity_id: self._trigger_on(wid, eid, now),
                )
            elif not is_on:
                self._cancel(key)
            active = self._trigger_active(win)
            if active == win.trigger.active:
                continue
            win.trigger.active = active
            if active:
                self._cancel(f"{win.window_id}:trigger_off")
            else:
                self._schedule(
                    f"{win.window_id}:trigger_off",
                    now + timedelta(seconds=float(win.conf[CONF_TRIGGER_OFF_DELAY])),
                    lambda now, wid=win.window_id: self._trigger_off(wid, now),
                )

    def _trigger_locked(self, win: Window, now: datetime) -> bool:
        return win.trigger.locked_until is not None and now < win.trigger.locked_until

    @callback
    def _trigger_on(self, window_id: str, entity_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or self._trigger_locked(win, now):
            return
        if self._state_value(entity_id) not in (win.conf.get(CONF_TRIGGER_ACTIVE) or []):
            return
        self._try_trigger_close(win, now)

    def _try_trigger_close(self, win: Window, now: datetime) -> None:
        if not self._trigger_active(win) or self._trigger_locked(win, now):
            win.trigger.pending = False
            return
        situation = self._situation(win, now)
        actions = rules.trigger_close(win.rules, situation)
        if actions:
            win.trigger.pending = False
            win.trigger.locked_until = now + timedelta(hours=float(win.conf[CONF_TRIGGER_MAX_LOCK]))
            self._apply(win, actions, now)
        else:
            # Window open: close as soon as it is closed again (once per cycle).
            win.trigger.pending = situation.active and situation.window_blocks
        self._save()

    @callback
    def _trigger_off(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or self._trigger_active(win):
            return
        win.trigger.locked_until = None
        win.trigger.pending = False
        self._save()

    # ------------------------------------------------------------------ daily events

    @callback
    def _on_day_change(self, now: datetime) -> None:
        self._create_task(self.async_update_forecast(), "forecast")

    def forecast_kind(self) -> str | None:
        """Kind of forecast to request (None: the weather entity has none)."""
        state = self._state(self.opt(CONF_WEATHER))
        features = None
        if state is not None and ATTR_SUPPORTED_FEATURES in state.attributes:
            features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES) or 0)
        return fc.choose(str(self.opt(CONF_FORECAST_TYPE)), features)

    def _forecast_issue(self, weather: str, unsupported: bool) -> None:
        if unsupported:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                ISSUE_FORECAST,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_FORECAST,
                translation_placeholders={"weather": weather},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_FORECAST)

    async def async_update_forecast(self) -> None:
        """Forecast: today's high decides about the summer day."""
        weather = self.opt(CONF_WEATHER)
        now = dt_util.now()
        if not weather or self._shutdown:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_FORECAST)
            return
        value = None
        night_low = None
        kind = self.forecast_kind() if self._state(weather) is not None else None
        if self._state(weather) is not None:
            self._forecast_issue(weather, kind is None)
        if kind is not None:
            try:
                async with asyncio.timeout(FORECAST_TIMEOUT):
                    response = await self.hass.services.async_call(
                        "weather",
                        "get_forecasts",
                        {ATTR_ENTITY_ID: weather, "type": kind},
                        blocking=True,
                        return_response=True,
                    )
                forecast = (response or {}).get(weather, {}).get("forecast") or []
                value, night_low = fc.summarize(forecast, kind, self._sun_day(now), self.tz)
                LOGGER.debug(
                    "Forecast %s of %s: high %s, night low %s", kind, weather, value, night_low
                )
            except TimeoutError:
                LOGGER.warning("Forecast of %s timed out", weather)
            except (HomeAssistantError, ValueError, AttributeError) as err:
                LOGGER.warning("Forecast of %s not available: %s", weather, err)
        if self._shutdown:
            return
        if value is None:
            LOGGER.info("No forecast from %s, keeping the last value and retrying", weather)
            self._schedule(
                "forecast_retry",
                now + FORECAST_RETRY,
                lambda _now: self._create_task(self.async_update_forecast(), "forecast"),
            )
        else:
            # A later fetch on the same day only adds the night low: during the day
            # some services report only the high of the remaining hours.
            if self.forecast_day != self._sun_day(now) or self.forecast_max is None:
                self.forecast_max = value
            self.forecast_night_low = night_low
            self.forecast_day = self._sun_day(now)
            self._cancel("forecast_retry")
        self._save()
        self._evaluate_all(dt_util.now())

    @callback
    def _on_night_end(self, now: datetime) -> None:
        for win in self.windows.values():
            self._schedule_window(win, now)
        self._schedule_global_evening(now)
        self._evaluate_all(now)

    def _schedule_global_evening(self, now: datetime) -> None:
        """Update the global evening entity when the evening starts."""
        day = self._evening_day(now)
        start, _end = self._evening_window(self.global_evening, day)
        if start <= now:
            start, _end = self._evening_window(self.global_evening, day + timedelta(days=1))
        self._schedule("global:evening", start, self._on_global_evening)

    @callback
    def _on_global_evening(self, now: datetime) -> None:
        self.async_update_listeners()
        self._schedule_global_evening(now + timedelta(seconds=1))

    @callback
    def _on_sunrise(self) -> None:
        now = dt_util.now()
        for win in self.windows.values():
            if win.override_active and (
                win.override_sunrise or (win.override_until and win.override_until <= now)
            ):
                self._end_override(win.window_id, now)
        self._evaluate_all(now)

    def _schedule_window(self, win: Window, now: datetime) -> None:
        """Evening start, override end and the morning opening of a window."""
        settings = win.evening_settings or self.global_evening
        day = self._evening_day(now)
        start, _end = self._evening_window(settings, day)
        if start <= now:
            start, _end = self._evening_window(settings, day + timedelta(days=1))
        self._schedule(
            f"{win.window_id}:evening",
            start,
            lambda now, wid=win.window_id: self._on_evening(wid, now),
        )
        if win.override_active and win.override_until is not None:
            self._schedule(
                f"{win.window_id}:override",
                win.override_until,
                lambda now, wid=win.window_id: self._end_override(wid, now),
            )
        self._plan_morning(win, now)

    @callback
    def _on_evening(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None:
            return
        self._run_evening(win, now)
        self._schedule_window(win, now + timedelta(seconds=1))
        self.async_update_listeners()

    def _run_evening(self, win: Window, now: datetime) -> None:
        """Evening run; remembered if the automatic is off (as the old evening mode
        only started with the automatic on)."""
        if not self.automatic:
            win.evening_missed = self._evening_day(now)
            return
        win.evening_missed = None
        self._apply(win, rules.evening(win.rules, self._situation(win, now)), now)

    @callback
    def _startup_finished(self, now: datetime) -> None:
        """End of the restart protection: evaluate and catch up the evening run."""
        self.startup_until = None
        catch_up = dt_util.as_local(now).time() >= parse_time(
            self.opt(CONF_CATCH_UP_AFTER), "12:00"
        )
        for win in self.windows.values():
            self._refresh(win, now)
            self._protect(win, now)
            if catch_up and self._evening(win, now):
                self._run_evening(win, now)
            self._evaluate(win, now)
        self.async_update_listeners()

    # ------------------------------------------------------------------ vacation

    @callback
    def _on_vacation_morning(self, now: datetime) -> None:
        if not (self.vacation and self.automatic and not self._startup(now)):
            return
        window = float(self.opt(CONF_VAC_MORNING_WINDOW))
        for win in self.windows.values():
            if not win.rules.vacation:
                continue
            position = random_position(
                int(self.opt(CONF_VAC_POS_MIN)), int(self.opt(CONF_VAC_POS_MAX)), self._rng
            )
            self._schedule(
                f"{win.window_id}:vacation",
                random_time(now, window, self._rng),
                lambda now, wid=win.window_id, pos=position: self._vacation_open(wid, pos, now),
            )

    @callback
    def _vacation_open(self, window_id: str, position: int, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is not None:
            self._apply(
                win, rules.vacation_open(win.rules, self._situation(win, now), position), now
            )

    @callback
    def _on_vacation_evening(self, now: datetime) -> None:
        if not (self.vacation and self.automatic and not self._startup(now)):
            return
        self.vacation_evening_day = self._evening_day(now)
        self._save()
        window = float(self.opt(CONF_VAC_EVENING_WINDOW))
        for win in self.windows.values():
            if not win.rules.vacation:
                continue
            self._schedule(
                f"{win.window_id}:vacation",
                random_time(now, window, self._rng),
                lambda now, wid=win.window_id: self._vacation_close(wid, now),
            )
        self.async_update_listeners()

    @callback
    def _vacation_close(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is not None:
            self._apply(win, rules.vacation_close(win.rules, self._situation(win, now)), now)

    # ------------------------------------------------------------------ morning opening

    def _morning_trigger_time(self, win: Window) -> datetime | None:
        value = self._state_value(win.conf.get(CONF_MORNING_TRIGGER))
        if value is None or value in INVALID:
            return None
        return dt_util.parse_datetime(value)

    def _plan_morning(self, win: Window, now: datetime) -> None:
        settings = win.morning_settings
        key = f"{win.window_id}:morning"
        if settings is None:
            self._cancel(key)
            return
        local = dt_util.as_local(now)
        day = local.date()
        _low, high = mo.bounds(day, self.tz, settings)
        planned = self._planned_morning(win, settings, day)
        if win.morning_day == day or local >= high or planned <= local:
            # done today or already past: plan tomorrow (no late opening)
            day = day + timedelta(days=1)
            planned = self._planned_morning(win, settings, day)
        self._schedule(key, planned, lambda now, wid=win.window_id: self._on_morning(wid, now))
        if settings.mode == mo.MODE_BRIGHTNESS:
            # bright already before the earliest time: check at the earliest time
            earliest, _high = mo.bounds(day, self.tz, settings)
            self._schedule(
                f"{win.window_id}:morning_start",
                earliest,
                lambda now, wid=win.window_id: self._on_morning_start(wid, now),
            )

    def _planned_morning(self, win: Window, settings: mo.MorningSettings, day: date) -> datetime:
        return mo.planned_time(
            day,
            self.tz,
            settings,
            workday=mo.is_workday(
                day,
                self._state_value(self.opt(CONF_WORKDAY)),
                self.opt(CONF_WEEKEND_DAYS) or (),
            ),
            sunrise=sunlib.sunrise(self.observer, day, self.tz),
            elevation_time=sunlib.time_at_elevation(
                self.observer, day, settings.sun_elevation, True, self.tz
            ),
            trigger_time=self._morning_trigger_time(win),
        )

    def _in_morning_window(self, win: Window, now: datetime) -> bool:
        settings = win.morning_settings
        if settings is None:
            return False
        local = dt_util.as_local(now)
        low, high = mo.bounds(local.date(), self.tz, settings)
        return low <= local <= high and win.morning_day != local.date()

    def _manual_since_evening(self, win: Window, now: datetime) -> bool:
        if win.last_manual is None:
            return False
        settings = win.evening_settings or self.global_evening
        start, _end = self._evening_window(
            settings, dt_util.as_local(now).date() - timedelta(days=1)
        )
        return win.last_manual >= start

    @callback
    def _on_morning(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or not self._in_morning_window(win, now):
            if win is not None:
                self._plan_morning(win, now + timedelta(seconds=1))
            return
        self._open_morning(win, now)
        self._plan_morning(win, now + timedelta(seconds=1))

    def _open_morning(self, win: Window, now: datetime) -> None:
        situation = self._situation(win, now)
        if situation.open_blocked and situation.active:
            # retried when the block ends (until the latest time)
            win.morning_pending = True
            return
        win.morning_pending = False
        actions = rules.morning(win.rules, situation, self._manual_since_evening(win, now))
        win.morning_day = dt_util.as_local(now).date()
        self._apply(win, actions, now)
        self._save()

    def _retry_morning(self, win: Window, now: datetime) -> None:
        if win.morning_pending and self._in_morning_window(win, now):
            self._open_morning(win, now)

    @callback
    def _on_morning_start(self, window_id: str, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is not None:
            self._refresh(win, now)
            self._check_morning_brightness(win, now)

    def _check_morning_brightness(self, win: Window, now: datetime) -> None:
        settings = win.morning_settings
        if (
            settings is not None
            and settings.mode == mo.MODE_BRIGHTNESS
            and win.flags
            and win.flags[6]
            and self._in_morning_window(win, now)
        ):
            self._open_morning(win, now)

    @callback
    def _on_morning_input(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        new = event.data["new_state"]
        old = event.data["old_state"]
        now = dt_util.now()
        for win in self.windows.values():
            if win.morning_settings is None:
                continue
            # A trigger without a time (motion, switch) opens when it turns on.
            turned_on = (
                entity_id == win.conf.get(CONF_MORNING_TRIGGER)
                and self._morning_trigger_time(win) is None
                and new is not None
                and new.state == STATE_ON
                and (old is None or old.state != STATE_ON)
            )
            if turned_on and self._in_morning_window(win, now):
                self._open_morning(win, now)
                continue
            self._plan_morning(win, now)

    # ------------------------------------------------------------------ switch

    async def async_set_automatic(self, enabled: bool) -> None:
        self.automatic = enabled
        self._save()
        if enabled:
            now = dt_util.now()
            day = self._evening_day(now)
            for win in self.windows.values():
                if win.evening_missed == day and self._evening(win, now):
                    self._run_evening(win, now)
                win.evening_missed = None
            self._evaluate_all(now)
        self.async_update_listeners()

    # ------------------------------------------------------------------ diagnostics

    def diagnostics(self) -> dict[str, Any]:
        now = dt_util.now()
        return {
            "automatic": self.automatic,
            "summer_day": self.summer,
            "forecast_max": self.forecast_max,
            "forecast_night_low": self.forecast_night_low,
            "forecast_day": _iso(self.forecast_day),
            "heating_day": self.heating_day,
            "evening": self.global_evening_active,
            "vacation": self.vacation,
            "startup_until": _iso(self.startup_until),
            "protection": {
                kind: {"active": guard.active, "release_due": guard.release_due}
                for kind, guard in self.guards.items()
            },
            "queued_commands": len(self._queue),
            "groups": {gid: g.name for gid, g in self.groups.items()},
            "windows": {
                wid: {
                    "status": self.status(win),
                    "situation": self._situation(win, now).__dict__,
                    "last_reason": win.last_reason,
                    "override_until": _iso(win.override_until),
                    "automatic": win.automatic,
                    "sun_enabled": win.sun_enabled,
                    "verify": win.verify,
                    "timers": sorted(k for k in self._timers if k.startswith(wid)),
                }
                for wid, win in self.windows.items()
            },
        }


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _split(state: str | None, tilt: bool) -> tuple[list[str | None], list[str | None]]:
    """One contact state as the arguments of ``window_contact``."""
    return ([], [state]) if tilt else ([state], [])


def _int(value: Any) -> int | None:
    """Optional position (empty = not set)."""
    number = as_float(value)
    return None if number is None else round(number)


def _to_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _to_datetime(value: Any) -> datetime | None:
    return dt_util.parse_datetime(str(value)) if value else None
