"""Setup, unload, removal, diagnostics, repairs and robustness."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.shutter_assistant.const import DOMAIN
from custom_components.shutter_assistant.diagnostics import async_get_config_entry_diagnostics

from .conftest import (
    CONTACT,
    COVER,
    SUMMER_NOON,
    WINDOW_ID,
    advance,
    make_entry,
    set_cover,
    setup_entry,
)

OUTDOOR = "sensor.outdoor_temperature"


async def test_unload_removes_listeners_and_timers(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    engine = entry.runtime_data
    assert engine._timers and engine._unsubs
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert engine._timers == {}
    assert engine._unsubs == []
    # nothing is scheduled any more after the shutdown
    engine._schedule("late", engine.startup_until, lambda now: None)
    assert engine._timers == {}


async def test_remove_entry_deletes_store_and_issues(
    hass: HomeAssistant, base_states, hass_storage
) -> None:
    entry = make_entry(window={"group": "deleted_group"})
    await setup_entry(hass, entry)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"missing_group_{WINDOW_ID}") is not None
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, f"missing_group_{WINDOW_ID}") is None
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage


async def test_issue_of_a_deleted_window_disappears(hass: HomeAssistant, base_states) -> None:
    entry = make_entry(window={"group": "deleted_group"})
    await setup_entry(hass, entry)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"missing_group_{WINDOW_ID}") is not None
    hass.config_entries.async_remove_subentry(entry, WINDOW_ID)
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, f"missing_group_{WINDOW_ID}") is None


async def test_diagnostics_redact_notification_services(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["entry"]["options"]["notify_services"] == "**REDACTED**"
    assert result["entry"]["options"]["outdoor_temperature"] == OUTDOOR
    assert WINDOW_ID in result["state"]["windows"]


async def test_setup_failure_leaves_nothing_behind(hass: HomeAssistant, base_states) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch.object(
        hass.config_entries, "async_forward_entry_setups", side_effect=RuntimeError("boom")
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unavailable_cover_is_not_moved(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(SUMMER_NOON)
    hass.states.async_set(COVER, "unavailable")
    await setup_entry(hass, make_entry())
    hass.states.async_set(OUTDOOR, "25.0")
    await hass.async_block_till_done()
    await advance(hass, freezer, 20 * 60)
    assert calls["set_cover_position"] == []


async def test_cover_without_position_support(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory, caplog
) -> None:
    freezer.move_to(SUMMER_NOON)
    hass.states.async_set(COVER, "open", {"supported_features": 3})  # open and close only
    await setup_entry(hass, make_entry())
    hass.states.async_set(OUTDOOR, "25.0")
    await hass.async_block_till_done()
    await advance(hass, freezer, 15 * 60)
    assert calls["set_cover_position"] == []
    assert "no position support" in caplog.text


async def test_notification_only_to_notify_services(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    """A service of another domain (stored by an older version) is not called."""
    freezer.move_to(SUMMER_NOON)
    hass.states.async_set(CONTACT, "on")
    called = []
    hass.services.async_register("script", "danger", lambda call: called.append(call))
    await setup_entry(hass, make_entry(notify_services=["script.danger", "notify.phone"]))
    hass.states.async_set(OUTDOOR, "25.0")
    await hass.async_block_till_done()
    await advance(hass, freezer, 15 * 60)
    assert called == []
    assert len(calls["notify"]) == 1


async def test_window_closed_delay_is_an_option(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-07-01 20:50:00+02:00")
    hass.states.async_set(CONTACT, "on")
    await setup_entry(hass, make_entry(window_closed_delay=30))
    await advance(hass, freezer, 11 * 60)  # evening at 21:00
    hass.states.async_set(CONTACT, "off")
    await hass.async_block_till_done()
    await advance(hass, freezer, 20, step=1)
    assert calls["close_cover"] == []
    await advance(hass, freezer, 11, step=1)
    assert len(calls["close_cover"]) == 1


async def test_outdoor_temperature_from_the_weather_entity(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(SUMMER_NOON)
    hass.states.async_set("weather.home", "sunny", {"temperature": 15.0})
    await setup_entry(hass, make_entry(outdoor_temperature=None, weather="weather.home"))
    engine = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    assert engine.outdoor_temperature == 15.0
    hass.states.async_set("weather.home", "sunny", {"temperature": 25.0})
    await hass.async_block_till_done()
    assert engine.summer
    await advance(hass, freezer, 15 * 60)
    assert [c.data["position"] for c in calls["set_cover_position"]] == [10]


async def test_panel_without_sidebar(hass: HomeAssistant, base_states) -> None:
    hass.config.components.add("frontend")
    hass.http = Mock(async_register_static_paths=AsyncMock())
    with (
        patch("homeassistant.components.frontend.async_panel_exists", return_value=False),
        patch("homeassistant.components.panel_custom.async_register_panel") as register,
    ):
        await setup_entry(hass, make_entry(show_panel=False))
    kwargs = register.call_args.kwargs
    assert kwargs["sidebar_title"] is None
    assert kwargs["config_panel_domain"] == DOMAIN


async def test_restart_protection_counts_from_the_start(
    hass: HomeAssistant, base_states, calls, freezer: FrozenDateTimeFactory
) -> None:
    from homeassistant.core import CoreState

    freezer.move_to("2026-10-15 20:00:00+02:00")
    hass.set_state(CoreState.starting)
    await setup_entry(hass, make_entry())
    set_cover(hass, 100)
    # Home Assistant needs 4 minutes to start
    await advance(hass, freezer, 4 * 60)
    hass.set_state(CoreState.running)
    hass.bus.async_fire("homeassistant_started")
    await hass.async_block_till_done()
    await advance(hass, freezer, 4 * 60)
    assert calls["close_cover"] == []  # 5 minutes from the start
    await advance(hass, freezer, 2 * 60)
    assert len(calls["close_cover"]) == 1
