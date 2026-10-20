"""Private, scoped repair of existing Teams account labels; never sends reports."""

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from teams_participants import teams_participant_labels


def backfill(index: Path, meeting_id: str, inspector: Path, apply: bool = False) -> dict:
    payload = json.loads(index.read_text())
    count = 0
    for frame in payload.get("items", []):
        if frame.get("meeting_id") != meeting_id:
            continue
        # Skip off-tab frames early, then confirm the actual visible address
        # from OCR. A Teams window title by itself is not evidence.
        if "teams." not in str(frame.get("visual_text", "")).lower():
            continue
        path = Path(str(frame.get("path", "")))
        if not path.is_file():
            continue
        result = subprocess.run([str(inspector), str(path)], capture_output=True, text=True, timeout=20, check=True)
        labels = teams_participant_labels(json.loads(result.stdout))
        if labels:
            frame["participant_labels"] = labels
            frame["participant_platform"] = "teams"
            count += 1
    if apply and count:
        suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        shutil.copy2(index, index.with_name(index.name + ".before-teams-" + suffix))
        temporary = index.with_suffix(".teams.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(index)
    return {"meeting_id": meeting_id, "labelled_frames": count, "applied": apply}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("meeting_id")
    parser.add_argument("--index", type=Path, default=Path.home() / ".config/meeting-copilot/frames.json")
    parser.add_argument("--inspector", type=Path, default=Path.home() / ".local/share/meeting-copilot/bin/zoom-frame-inspector")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(backfill(args.index, args.meeting_id, args.inspector, args.apply)))
