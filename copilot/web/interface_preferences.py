"""The web UI inherits the first-run native choice, never the private config."""

import json
from pathlib import Path


def interface_preferences(config_path: Path) -> dict:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(config, dict):
        return {}
    language = config.get("interface_language")
    # Explicit supported choices only. Do not expose keys, paths or other settings.
    return {"interface_language": language} if language in ("en", "ru") else {}
