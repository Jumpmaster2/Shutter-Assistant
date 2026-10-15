"""Localised texts for logbook entries, the last reason and notifications."""

from __future__ import annotations

from typing import Any

_TEXTS: dict[str, dict[str, str]] = {
    "sun_lower": {
        "de": "Sonnenschutz: auf {position} %",
        "en": "Sun protection: to {position} %",
    },
    "sun_already": {
        "de": "Sonnenschutz: steht schon weiter unten, nur vorgemerkt",
        "en": "Sun protection: already further closed, only marked",
    },
    "sun_blocked_window": {
        "de": "Sonnenschutz: Fenster offen, Rollo nicht gefahren",
        "en": "Sun protection: window open, cover not moved",
    },
    "sun_manual": {
        "de": "Sonnenschutz manuell erkannt, heute keine Automatikfahrt",
        "en": "Manual sun protection detected, no automatic movement today",
    },
    "sun_position_manual": {
        "de": "Auf Sonnenschutz-Position gefahren, als Sonnenschutz vorgemerkt",
        "en": "Moved to the sun protection position, marked as sun protection",
    },
    "auto_up": {
        "de": "Sonne aus dem Bereich: hoch",
        "en": "Sun left the sector: open",
    },
    "evening_close": {"de": "Abendlauf: zu", "en": "Evening run: closed"},
    "follow_up_close": {
        "de": "Fenster am Abend geschlossen: zu",
        "en": "Window closed in the evening: closed",
    },
    "ventilation": {
        "de": "Lüften: auf {position} %",
        "en": "Ventilation: to {position} %",
    },
    "trigger_close": {
        "de": "Schließ-Auslöser aktiv: zu",
        "en": "Close trigger active: closed",
    },
    "vacation_open": {
        "de": "Urlaub morgens: auf {position} %",
        "en": "Vacation morning: to {position} %",
    },
    "vacation_close": {"de": "Urlaub abends: zu", "en": "Vacation evening: closed"},
    "morning_open": {
        "de": "Morgenöffnung: auf {position} %",
        "en": "Morning opening: to {position} %",
    },
    "morning_sun": {
        "de": "Morgenöffnung direkt auf Sonnenschutz: {position} %",
        "en": "Morning opening directly to sun protection: {position} %",
    },
    "override_on": {
        "de": "Manuelle Bewegung erkannt: Übersteuerung bis {until}",
        "en": "Manual movement detected: override until {until}",
    },
    "override_off": {"de": "Übersteuerung beendet", "en": "Override ended"},
    "notify_title": {"de": "☀️ Sonnenschutz", "en": "☀️ Sun protection"},
    "notify_window_open": {
        "de": "{name}: Fenster offen, Rollo nicht gefahren",
        "en": "{name}: window open, cover not moved",
    },
    "until_sunrise": {"de": "Sonnenaufgang", "en": "sunrise"},
}


def resolve_language(option: str | None, ha_language: str | None) -> str:
    """'de' or 'en' from the option ('auto' follows Home Assistant)."""
    lang = option if option in ("de", "en") else (ha_language or "en")
    return "de" if lang.lower().startswith("de") else "en"


def text(language: str, key: str, **kwargs: Any) -> str:
    """Return the localised text."""
    lang = "de" if language.lower().startswith("de") else "en"
    entry = _TEXTS.get(key)
    if entry is None:
        return key
    try:
        return entry[lang].format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return entry[lang]
