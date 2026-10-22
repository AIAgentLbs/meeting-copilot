"""Interface preferences in the shared config.json: the web UI reads and writes only these keys."""

import json
import threading
from pathlib import Path

from ai_providers import _file_lock
from private_dirs import private_dir
from stt import _atomic_write

# Explicit supported values only. Do not expose keys, paths or other settings.
CHOICES = {
    "interface_language": lambda value: value in ("en", "ru"),
    "transcript_hidden": lambda value: isinstance(value, bool),
}
_WRITE_LOCK = threading.Lock()


def interface_preferences(config_path: Path) -> dict:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(config, dict):
        return {}
    return {key: config[key] for key, valid in CHOICES.items() if key in config and valid(config[key])}


def save_preferences(config_path: Path, change) -> dict:
    """Writes only the given preference keys, under config.json.lock like the AI and speech choices:
    missing file = empty object, malformed or not an object = refuse; every other key is kept."""
    if not isinstance(change, dict) or not change or any(key not in CHOICES or not CHOICES[key](value)
                                                          for key, value in change.items()):
        raise ValueError("Send interface_language (en or ru) and/or transcript_hidden (true or false)")
    private_dir(config_path.parent)
    with _WRITE_LOCK, _file_lock(config_path.with_name(config_path.name + ".lock")):
        try:
            text = config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = None
        try:
            data = {} if text is None else json.loads(text)
        except ValueError:
            raise ValueError(f"{config_path} is not valid JSON; fix it before saving interface preferences") from None
        if not isinstance(data, dict):
            raise ValueError(f"{config_path} must hold a JSON object")
        data.update(change)
        _atomic_write(config_path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return dict(change)
