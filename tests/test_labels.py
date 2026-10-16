"""The labels of the panel are generated from the translations and must be current."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _generator():
    spec = importlib.util.spec_from_file_location("gen_labels", ROOT / "scripts" / "gen_labels.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_labels_are_current() -> None:
    gen = _generator()
    assert gen.TARGET.read_text(encoding="utf-8") == gen.build(), "run scripts/gen_labels.py"


def test_every_window_and_option_field_has_a_label() -> None:
    import json

    gen = _generator()
    for language in gen.LANGUAGES:
        data = json.loads((gen.TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))
        labels = gen.labels(data)
        for key in ("outdoor_temperature", "group", "sun_position", "morning_trigger_entity"):
            assert labels[key][0], (language, key)
