"""Event driven engine: listens to the configured entities and runs the window rules.

Nothing is polled. Every evaluation is caused by a state change of a configured
entity or by a calculated point in time (sun sector bounds, evening start, hold
times, override end, daily times, sunrise, random vacation times).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from typing import Any

from astral import Observer
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
    CONF_NOTIFY,
    CONF_NOTIFY_OPEN,
    CONF_OPEN_BLOCK,
    CONF_OPEN_BLOCK_FREE,
    CONF_OUTDOOR_TEMP,
    CONF_OVERRIDE_DURATION,
    CONF_OVERRIDE_IGNORE_EVENING,
    CONF_OVERRIDE_SUNRISE,
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
    EVENT_LOGBOOK,
    GROUP_DEFAULTS,
    LOGGER,
    NAME,
    SENSOR_KINDS,
    STORAGE_VERSION,
    SUBENTRY_GROUP,
    SUBENTRY_WINDOW,
    THRESHOLD_KEYS,
    WINDOW_CLOSED_DEBOUNCE,
    WINDOW_DEFAULTS,
)
from .logic import morning as mo
from .logic import sun as sunlib
from .logic import window as rules
from .logic.conditions import FollowUp, Hold, as_float, at_least, sensors_ok, summer_day
from .logic.evening import EveningSettings, evening_day, evening_end, evening_start, is_evening
from .logic.override import MOVING, CommandTracker, is_manual, override_until
from .logic.vacation import random_position, random_time
from .messages import resolve_language, text

type ShutterConfigEntry = ConfigEntry[ShutterEngine]

INVALID = (STATE_UNAVAILABLE, STATE_UNKNOWN)
# A failed forecast is retried after this time (the last known value stays valid).
FORECAST_RETRY = timedelta(minutes=30)
# CoverEntityFeature.SET_POSITION (not imported to keep the integration free of
# platform dependencies)
SET_POSITION = 4


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
        self.global_device_id: str | None = None
        self.groups: dict[str, Group] = {}
        self.windows: dict[str, Window] = {}
        self.automatic = True
        self.forecast_day: date | None = None
        self.forecast_max: float | None = None
        self.raised_day: date | None = None
        self.vacation_evening_day: date | None = None
        self.startup_until: datetime | None = None
        self.tracker = CommandTracker()
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._unsubs: list[CALLBACK_TYPE] = []
        self._timers: dict[str, CALLBACK_TYPE] = {}
        self._timer_due: dict[str, datetime] = {}
        self._evening_cache: dict[tuple[EveningSettings, date], tuple[datetime, datetime]] = {}
        self._rng = random.Random()
        self._outdoor_last: float | None = None
        self._build()

    # ------------------------------------------------------------------ config

    @property
    def opts(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.config_entry.options}

    def opt(self, key: str) -> Any:
        return self.opts.get(key, DEFAULTS.get(key))

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
        conf = {**WINDOW_DEFAULTS, **data}
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
                follow_up_close=bool(conf[CONF_FOLLOW_UP_CLOSE]),
                ventilation=bool(conf[CONF_VENTILATION]),
                ventilation_position=int(conf[CONF_VENT_POSITION]),
                closed_position=int(conf[CONF_CLOSED_POSITION]),
                trigger_min_position=int(conf[CONF_TRIGGER_MIN_POSITION]),
                vacation=bool(conf[CONF_VACATION]),
                morning=bool(conf[CONF_MORNING]),
                morning_position=int(conf[CONF_MORNING_POSITION]),
                morning_sun_position=bool(conf[CONF_MORNING_SUN_POSITION]),
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
            win.window_open = self._window_open_now(win)
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
        if self.startup_until is None:
            # reload while running: no restart protection, evaluate right away
            for win in self.windows.values():
                self._evaluate(win, now)

    async def _async_started(self, _hass: HomeAssistant) -> None:
        """Home Assistant is running: get the forecast if today's is missing."""
        if self.forecast_day != self._sun_day(dt_util.now()):
            await self.async_update_forecast()

    def _restore(self, stored: dict[str, Any]) -> None:
        self.automatic = bool(stored.get("automatic", True))
        self.forecast_day = _to_date(stored.get("forecast_day"))
        self.forecast_max = as_float(stored.get("forecast_max"))
        self.raised_day = _to_date(stored.get("raised_day"))
        self.vacation_evening_day = _to_date(stored.get("vacation_evening_day"))
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
            locked = _to_datetime(data.get("trigger_locked_until"))
            if locked is not None and locked > now:
                win.trigger.locked_until = locked
                win.trigger.pending = bool(data.get("trigger_pending"))

    def _data_to_save(self) -> dict[str, Any]:
        return {
            "automatic": self.automatic,
            "forecast_day": _iso(self.forecast_day),
            "forecast_max": self.forecast_max,
            "raised_day": _iso(self.raised_day),
            "vacation_evening_day": _iso(self.vacation_evening_day),
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
                }
                for wid, win in self.windows.items()
            },
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 5)

    async def async_shutdown(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        for unsub in self._timers.values():
            unsub()
        self._timers.clear()
        await self._store.async_save(self._data_to_save())
        await super().async_shutdown()

    def _update_issues(self) -> None:
        for win in self.windows.values():
            issue_id = f"missing_group_{win.window_id}"
            if win.group_id and win.group_id not in self.groups:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_group",
                    translation_placeholders={"window": win.name},
                )
            else:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    # ------------------------------------------------------------------ listeners

    def _register_listeners(self) -> None:
        def track(entities: set[str], handler: Callable[[Event[EventStateChangedData]], None]):
            entities.discard("")
            if entities:
                self._unsubs.append(
                    async_track_state_change_event(self.hass, sorted(entities), handler)
                )

        outdoor = self.opt(CONF_OUTDOOR_TEMP)
        self._outdoor_last = as_float(self._state_value(outdoor))
        track({outdoor} if outdoor else set(), self._on_outdoor)
        sensors = {e for g in self.groups.values() for lst in g.sensors.values() for e in lst}
        track(sensors, self._on_sun_sensor)
        track({e for w in self.windows.values() for e in w.sensors}, self._on_window_sensor)
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
        if when is None:
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

    def _window_open_now(self, win: Window) -> bool:
        """Any contact not reporting closed counts as open (unknown is not safe)."""
        return any(self._state_value(e) != "off" for e in win.sensors)

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
            self.forecast_max, float(self.opt(CONF_SUMMER_THRESHOLD)), self.raised_day == today
        )

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
        outdoor = self._state_value(self.opt(CONF_OUTDOOR_TEMP))
        win.temp_hold.update(at_least(outdoor, float(win.conf[CONF_TEMP_THRESHOLD])), ts)
        temp_ok = win.temp_hold.state(ts)
        sens = group is not None and sensors_ok(self._sensor_values(group), self._thresholds(win))
        in_sector, past_end = self._sector(win, now)
        summer = self.summer
        win.live_hold.update(group is not None and summer and temp_ok and sens, ts)
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
        flags = (temp_ok, sens, live, no_temp, in_sector, past_end, morning_ok)
        changed = flags != win.flags
        win.flags = flags
        return changed

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
        flags = win.flags or (False,) * 7
        return rules.Situation(
            automatic=self.automatic,
            startup=self._startup(now),
            position=self._position(win),
            window_open=win.window_open,
            window_on=any(self._state_value(e) == STATE_ON for e in win.sensors),
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
        )

    def status(self, win: Window) -> str:
        return rules.status(win.rules, self._situation(win, dt_util.now()))

    def sun_details(self, win: Window) -> dict[str, Any]:
        """Thresholds, sensors and pending hold times of the sun condition (read only)."""
        ts = dt_util.utcnow().timestamp()

        def at(due: float | None) -> str | None:
            return dt_util.as_local(dt_util.utc_from_timestamp(due)).isoformat() if due else None

        details: dict[str, Any] = {
            "summer_day": self.summer,
            "forecast_max": self.forecast_max,
            "summer_threshold": float(self.opt(CONF_SUMMER_THRESHOLD)),
            "temperature_sensor": self.opt(CONF_OUTDOOR_TEMP),
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
        for action in actions:
            if action.kind == rules.POSITION and action.position is not None:
                moves.append((action.position, action.reason))
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
        for target, _reason in moves:
            self._start_move(win, target)
        if notify:
            self.hass.async_create_task(self._async_notify(win))
        self._save()
        self.async_update_listeners()

    def _set_reason(self, win: Window, reason: str, position: int | None, now: datetime) -> None:
        message = text(self.language, reason, position=position, name=win.name)
        win.last_reason = {
            "code": reason,
            "message": message,
            "position": position,
            "time": now.isoformat(),
        }
        self.hass.bus.async_fire(
            EVENT_LOGBOOK, {"name": win.name, "message": message, ATTR_ENTITY_ID: win.cover}
        )

    def _start_move(self, win: Window, target: int) -> None:
        state = self._state(win.cover)
        if state is None or state.state in INVALID:
            return
        if self._position(win) == target and state.state not in MOVING:
            return
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES) or 0)
        data: dict[str, Any] = {ATTR_ENTITY_ID: win.cover}
        if target >= rules.OPEN:
            service = "open_cover"
        elif target <= rules.CLOSED:
            service = "close_cover"
        elif features & SET_POSITION:
            service = "set_cover_position"
            data["position"] = target
        else:
            LOGGER.warning("%s cannot move to %s %% (no position support)", win.cover, target)
            return
        context = Context()
        self.tracker.register(win.cover, target, context.id, self._now_ts)
        self.hass.async_create_task(self._async_call("cover", service, data, context))

    async def _async_call(
        self, domain: str, service: str, data: dict[str, Any], context: Context | None = None
    ) -> None:
        try:
            await self.hass.services.async_call(domain, service, data, context=context)
        except (HomeAssistantError, ValueError) as err:
            LOGGER.warning("%s.%s failed: %s", domain, service, err)

    async def _async_notify(self, win: Window) -> None:
        title = text(self.language, "notify_title")
        message = text(self.language, "notify_window_open", name=win.name)
        for target in self.opt(CONF_NOTIFY) or []:
            domain, _, service = str(target).partition(".")
            if not service:
                domain, service = "notify", domain
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
    def _on_outdoor(self, event: Event[EventStateChangedData]) -> None:
        now = dt_util.now()
        new_state = event.data["new_state"]
        value = as_float(new_state.state) if new_state else None
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
        if changed:
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
            if entity_id not in win.sensors:
                continue
            open_now = self._window_open_now(win)
            really_opened = (
                new is not None and new.state == STATE_ON and old is not None and old.state == "off"
            )
            if open_now:
                self._cancel(f"{win.window_id}:close")
                was_open = win.window_open
                win.window_open = True
                if really_opened:
                    self._window_opened(win, now)
                if not was_open:
                    self.async_update_listeners()
            elif win.window_open:
                # closed: counts after the debounce time
                real = old is not None and old.state not in INVALID
                self._schedule(
                    f"{win.window_id}:close",
                    now + timedelta(seconds=WINDOW_CLOSED_DEBOUNCE),
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
        if win is None or not self._window_open_now(win):
            return
        self._apply(win, rules.ventilation(win.rules, self._situation(win, now)), now)

    @callback
    def _window_closed(self, window_id: str, real: bool, now: datetime) -> None:
        win = self.windows.get(window_id)
        if win is None or self._window_open_now(win):
            return
        win.window_open = False
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
        manual = self.automatic and is_manual(
            own=own,
            parent_id=new.context.parent_id,
            old_state=old.state if old else None,
            new_state=new.state,
            old_position=old_pos,
            new_position=new_pos,
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
        self.hass.async_create_task(self.async_update_forecast())

    async def async_update_forecast(self) -> None:
        """Daily forecast: today's high decides about the summer day."""
        weather = self.opt(CONF_WEATHER)
        now = dt_util.now()
        if not weather:
            return
        value = None
        if self._state(weather) is not None:
            try:
                response = await self.hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {ATTR_ENTITY_ID: weather, "type": "daily"},
                    blocking=True,
                    return_response=True,
                )
                forecast = (response or {}).get(weather, {}).get("forecast") or []
                if forecast:
                    value = as_float(forecast[0].get("temperature"))
            except (HomeAssistantError, ValueError, AttributeError) as err:
                LOGGER.warning("Forecast of %s not available: %s", weather, err)
        if value is None:
            LOGGER.info("No forecast from %s, keeping the last value and retrying", weather)
            self._schedule(
                "forecast_retry",
                now + FORECAST_RETRY,
                lambda _now: self.hass.async_create_task(self.async_update_forecast()),
            )
        else:
            self.forecast_max = value
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
            workday=mo.is_workday(day, self._state_value(self.opt(CONF_WORKDAY))),
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
            "forecast_day": _iso(self.forecast_day),
            "evening": self.global_evening_active,
            "vacation": self.vacation,
            "startup_until": _iso(self.startup_until),
            "groups": {gid: g.name for gid, g in self.groups.items()},
            "windows": {
                wid: {
                    "status": self.status(win),
                    "situation": self._situation(win, now).__dict__,
                    "last_reason": win.last_reason,
                    "override_until": _iso(win.override_until),
                    "timers": sorted(k for k in self._timers if k.startswith(wid)),
                }
                for wid, win in self.windows.items()
            },
        }


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _to_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _to_datetime(value: Any) -> datetime | None:
    return dt_util.parse_datetime(str(value)) if value else None
