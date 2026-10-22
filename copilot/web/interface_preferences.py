"""The web UI inherits the first-run native choice, never the private config."""

import json
import threading
from pathlib import Path

from ai_providers import _file_lock
from private_dirs import private_dir
from stt import _atomic_write

LANGUAGES = ("en", "ru")
_WRITE_LOCK = threading.Lock()


def interface_preferences(config_path: Path) -> dict:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(config, dict):
        return {}
    language = config.get("interface_language")
    # Explicit supported choices only. Do not expose keys, paths or other settings.
    return {"interface_language": language} if language in LANGUAGES else {}


def save_interface_language(config_path: Path, language) -> dict:
    """Settings writes only `interface_language`, under config.json.lock like the AI and speech
    choices: missing file = empty object, malformed or not an object = refuse; other keys kept."""
    if language not in LANGUAGES:
        raise ValueError("Choose the interface language: en or ru")
    private_dir(config_path.parent)
    with _WRITE_LOCK, _file_lock(config_path.with_name(config_path.name + ".lock")):
        try:
            text = config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            text = None
        try:
            data = {} if text is None else json.loads(text)
        except ValueError:
            raise ValueError(f"{config_path} is not valid JSON; fix it before saving the interface language") from None
        if not isinstance(data, dict):
            raise ValueError(f"{config_path} must hold a JSON object")
        data["interface_language"] = language
        _atomic_write(config_path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return {"interface_language": language}
