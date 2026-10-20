"""Temperature units of the instance and the kinds of forecast."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.shutter_assistant.const import DOMAIN

from .conftest import OUTDOOR, SUMMER_NOON, WINDOW_ID, advance, make_entry, setup_entry

TEMPERATURE_KEYS = ("summer_threshold", "night_threshold")


def _forecasts(hass: HomeAssistant, features: int, answer: dict | None = None) -> list[str]:
    """Weather entity with ``features``; returns the requested kinds."""
    kinds: list[str] = []

    async def get_forecasts(call: ServiceCall) -> dict:
        kinds.append(call.data["type"])
        if answer is None:
            raise TimeoutError
        return {"weather.home": {"forecast": (answer or {}).get(call.data["type"], [])}}

    hass.states.async_set("weather.home", "sunny", {"supported_features": features})
    hass.services.async_register(
        "weather", "get_forecasts", get_forecasts, supports_response=SupportsResponse.ONLY
    )
    return kinds


async def test_fahrenheit_defaults_and_sensor_unit(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    freezer.move_to(SUMMER_NOON)
    # an entry without stored temperatures uses the defaults in °F
    entry = make_entry()
    entry.add_to_hass(hass)
    options = {k: v for k, v in entry.options.items() if k not in TEMPERATURE_KEYS}
    hass.config_entries.async_update_entry(entry, options=options)
    hass.states.async_set(OUTDOOR, "60", {"unit_of_measurement": "°F"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    engine = entry.runtime_data
    assert engine.opt("summer_threshold") == 73.0
    assert engine.windows[WINDOW_ID].conf["temperature_threshold"] == 66.0
    state = hass.states.get("sensor.shutter_assistant_forecast_high")
    assert state.attributes["unit_of_measurement"] == "°F"
    # 60 °F is no summer day, 77 °F is
    assert not engine.summer
    hass.states.async_set(OUTDOOR, "77", {"unit_of_measurement": "°F"})
    await hass.async_block_till_done()
    assert engine.summer
    await advance(hass, freezer, 15 * 60)
    assert len(calls["set_cover_position"]) == 1


async def test_fahrenheit_in_the_setup(hass: HomeAssistant, base_states) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"outdoor_temperature": OUTDOOR, "language": "auto"}
    )
    assert result["step_id"] == "summer"
    schema = {str(k): k for k in result["data_schema"].schema}
    assert schema["summer_threshold"].default() == 73.0
    assert schema["night_threshold"].default() == 57.0
    selector = result["data_schema"].schema[schema["summer_threshold"]]
    assert selector.config["unit_of_measurement"] == "°F"


async def test_setup_needs_a_temperature_source(hass: HomeAssistant, base_states) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"language": "auto"})
    assert result["errors"] == {"outdoor_temperature": "need_temperature_source"}
    hass.states.async_set("sensor.text", "hello")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"outdoor_temperature": "sensor.text", "language": "auto"}
    )
    assert result["errors"] == {"outdoor_temperature": "not_numeric"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"outdoor_temperature": OUTDOOR, "language": "auto", "notify_services": ["light.x"]},
    )
    assert result["errors"] == {"notify_services": "invalid_notify_service"}


async def test_hourly_forecast_when_daily_is_missing(
    hass: HomeAssistant, base_states, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-07-01 02:00:00+02:00")
    hourly = [
        {"datetime": "2026-07-01T14:00:00+02:00", "temperature": 28.0},
        {"datetime": "2026-07-01T23:00:00+02:00", "temperature": 17.0},
    ]
    kinds = _forecasts(hass, 2, {"hourly": hourly})
    await setup_entry(hass, make_entry(weather="weather.home"))
    engine = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert kinds == ["hourly"]
    assert (engine.forecast_max, engine.forecast_night_low) == (28.0, 17.0)
    assert engine.summer


async def test_forecast_kind_chosen_by_hand(hass: HomeAssistant, base_states) -> None:
    kinds = _forecasts(hass, 1 | 2, {"twice_daily": []})
    await setup_entry(hass, make_entry(weather="weather.home", forecast_type="twice_daily"))
    assert kinds == ["twice_daily"]


async def test_weather_without_forecast_raises_an_issue(hass: HomeAssistant, base_states) -> None:
    kinds = _forecasts(hass, 0, {})
    await setup_entry(hass, make_entry(weather="weather.home"))
    assert kinds == []
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "forecast_unsupported")
    assert issue is not None
    assert issue.translation_placeholders == {"weather": "weather.home"}


async def test_forecast_timeout_retries(hass: HomeAssistant, base_states) -> None:
    kinds = _forecasts(hass, 1)  # the request times out
    await setup_entry(hass, make_entry(weather="weather.home"))
    engine = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert kinds == ["daily"]
    assert "forecast_retry" in engine._timers
