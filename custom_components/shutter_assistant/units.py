"""Temperature unit of the Home Assistant instance and the defaults in that unit.

Home Assistant reports temperatures (sensors and forecasts) in the unit of its
unit system. The thresholds are entered in that unit, so the defaults (chosen
in °C) are converted for systems in °F.
"""

from __future__ import annotations

from typing import Any

from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    CONF_FROST_THRESHOLD,
    CONF_NIGHT_THRESHOLD,
    CONF_ROOM_MARGIN,
    CONF_ROOM_THRESHOLD,
    CONF_SUMMER_THRESHOLD,
    CONF_TEMP_THRESHOLD,
    DEFAULTS,
    WINDOW_DEFAULTS,
)

CELSIUS = UnitOfTemperature.CELSIUS
# Thresholds (absolute temperatures) and margins (temperature differences)
GLOBAL_TEMPERATURES = (CONF_SUMMER_THRESHOLD, CONF_NIGHT_THRESHOLD, CONF_FROST_THRESHOLD)
WINDOW_TEMPERATURES = (CONF_TEMP_THRESHOLD, CONF_ROOM_THRESHOLD)
WINDOW_INTERVALS = (CONF_ROOM_MARGIN,)


def temperature_unit(hass: HomeAssistant) -> str:
    return str(hass.config.units.temperature_unit)


def interval_unit(unit: str) -> str:
    """Unit of a temperature difference: K for °C, otherwise the unit itself."""
    return "K" if unit == CELSIUS else unit


def _convert(value: Any, unit: str, interval: bool = False) -> float:
    if unit == CELSIUS:
        return float(value)
    if interval:
        result = TemperatureConverter.convert_interval(float(value), CELSIUS, unit)
    else:
        result = TemperatureConverter.convert(float(value), CELSIUS, unit)
    return float(round(result))


def defaults(unit: str) -> dict[str, Any]:
    """Global defaults with the temperatures in ``unit``."""
    return {**DEFAULTS, **{key: _convert(DEFAULTS[key], unit) for key in GLOBAL_TEMPERATURES}}


def window_defaults(unit: str) -> dict[str, Any]:
    """Window defaults with the temperatures in ``unit``."""
    return {
        **WINDOW_DEFAULTS,
        **{key: _convert(WINDOW_DEFAULTS[key], unit) for key in WINDOW_TEMPERATURES},
        **{key: _convert(WINDOW_DEFAULTS[key], unit, True) for key in WINDOW_INTERVALS},
    }


def temperature_range(unit: str, low: float, high: float) -> tuple[float, float]:
    """Selector range given in °C, in ``unit``."""
    return _convert(low, unit), _convert(high, unit)
