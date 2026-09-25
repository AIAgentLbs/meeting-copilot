#!/usr/bin/env python3
"""Recover Meet account labels and active speakers from existing local frames."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from meet_participants import meet_active_speaker, meet_participant_labels


def backfill(index_path: Path, meeting_id: str, recordings_root: Path, inspector: Path) -> dict:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    scanned = 0
    changed = 0
    participants: set[str] = set()
    for item in payload.get("items", []):
        if item.get("meeting_id") != meeting_id:
            continue
        if not str(item.get("window_title") or "").casefold().startswith("meet -"):
            continue
        frame = Path(str(item.get("path") or "")).resolve()
        if not frame.is_file() or not frame.is_relative_to(recordings_root.resolve()):
            continue
        scanned += 1
        result = subprocess.run(
            [str(inspector), str(frame)], capture_output=True, text=True, timeout=25,
            check=False,
        )
        if result.returncode != 0:
            continue
        try:
            observations = json.loads(result.stdout)
        except ValueError:
            continue
        labels = meet_participant_labels(observations)
        before = (item.get("participant_labels", []), item.get("speaker", ""), item.get("speaker_confidence", ""))
        item["participant_labels"] = labels
        participants.update(labels)
        active = meet_active_speaker(frame, observations)
        if active and (not item.get("speaker") or item.get("speaker_confidence") == "meet-active-tile"):
            item["speaker"] = active
            item["speaker_confidence"] = "meet-active-tile"
        elif not active and item.get("speaker_confidence") == "meet-active-tile":
            item["speaker"] = ""
            item["speaker_confidence"] = ""
        if before != (item["participant_labels"], item.get("speaker", ""), item.get("speaker_confidence", "")):
            changed += 1
    if changed:
        temporary = index_path.with_suffix(".backfill.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(index_path)
    return {"scanned": scanned, "enriched": changed, "account_labels": sorted(participants)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--recordings-root", type=Path, required=True)
    parser.add_argument("--inspector", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(backfill(args.index, args.meeting_id, args.recordings_root, args.inspector), ensure_ascii=False))
