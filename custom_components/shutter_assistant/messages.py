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
    # closing to a position other than 0 % (evening position, frost, tilted window)
    "evening_close_partial": {
        "de": "Abendlauf: auf {position} %",
        "en": "Evening run: to {position} %",
    },
    "follow_up_close_partial": {
        "de": "Fenster am Abend geschlossen: auf {position} %",
        "en": "Window closed in the evening: to {position} %",
    },
    "trigger_close_partial": {
        "de": "Schließ-Auslöser aktiv: auf {position} %",
        "en": "Close trigger active: to {position} %",
    },
    "vacation_close_partial": {
        "de": "Urlaub abends: auf {position} %",
        "en": "Vacation evening: to {position} %",
    },
    "protection_wind": {
        "de": "Windschutz: auf {position} %",
        "en": "Wind protection: to {position} %",
    },
    "protection_rain": {
        "de": "Regenschutz: auf {position} %",
        "en": "Rain protection: to {position} %",
    },
    "protection_on": {"de": "{kind} aktiv", "en": "{kind} active"},
    "protection_off": {"de": "{kind} beendet", "en": "{kind} ended"},
    "protection_end": {
        "de": "Wetterschutz beendet: Automatik wieder aktiv",
        "en": "Weather protection ended: automatic active again",
    },
    "protection_automatic_off": {
        "de": "Wetterschutz beendet: Automatik aus",
        "en": "Weather protection ended: automatic off",
    },
    "kind_wind": {"de": "Windschutz", "en": "Wind protection"},
    "kind_rain": {"de": "Regenschutz", "en": "Rain protection"},
    "kind_frost": {"de": "Frostschutz", "en": "Frost protection"},
    "service": {"de": "Service: auf {position} %", "en": "Service: to {position} %"},
    "resume": {"de": "Automatik fortgesetzt", "en": "Automatic resumed"},
    "cover_retry": {
        "de": "{position} % nicht erreicht, Befehl wiederholt",
        "en": "{position} % not reached, command repeated",
    },
    "cover_failed": {
        "de": "{position} % auch nach Wiederholung nicht erreicht",
        "en": "{position} % not reached after repeating",
    },
    "notify_failed_title": {"de": "⚠️ Rollo", "en": "⚠️ Cover"},
    "notify_cover_failed": {
        "de": "{name}: Rollo hat {position} % nicht erreicht",
        "en": "{name}: cover did not reach {position} %",
    },
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
