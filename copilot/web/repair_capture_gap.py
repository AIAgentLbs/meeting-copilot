"""Add an audio-verified dropout to one private recording, keeping a backup.

Does not infer a person's identity, move source tracks, regenerate or send
reports. Use only after inspecting the original channel waveform.
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def repair(path: Path, meeting_id: str, lost_from: str, apply: bool = False) -> dict:
    datetime.fromisoformat(lost_from.replace("Z", "+00:00"))
    payload = json.loads(path.read_text())
    if payload.get("meeting_id") != meeting_id or payload.get("status") != "finished":
        raise ValueError("Target is not the expected completed meeting")
    warnings = list(payload.get("capture_warnings") or [])
    warning = {"reason": "system-audio-lost", "started_at": lost_from,
               "evidence": "archived stereo system channel verified silent after dropout"}
    if warning not in warnings:
        warnings.append(warning)
    payload["capture_warnings"] = warnings
    if apply:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(path, path.with_name(path.name + ".before-capture-gap-" + stamp))
        temporary = path.with_suffix(".repair.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)
    return {"meeting_id": meeting_id, "lost_from": lost_from, "applied": apply}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("meeting_id")
    parser.add_argument("lost_from")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(repair(args.path, args.meeting_id, args.lost_from, args.apply)))
