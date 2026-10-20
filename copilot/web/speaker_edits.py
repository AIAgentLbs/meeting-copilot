"""Save corrected speaker attribution in the canonical meeting transcript."""

import copy
import hashlib
import json
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def segment_id(segment: dict) -> str:
    # Text changes while streaming; channel + start time remain the identity.
    value = f"{segment.get('source', '')}\n{segment.get('timestamp', '')}"
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def base_speaker(segment: dict) -> tuple[str, str]:
    if segment.get("speaker_identity") == "manual" and segment.get("speaker_id"):
        return str(segment["speaker_id"]), str(segment.get("speaker") or "Собеседник")
    if segment.get("speaker_identity") == "unverified":
        return "unassigned", "Распределить"
    if segment.get("source") == "microphone":
        return "self", "Я"
    voice = str(segment.get("voice_id") or "")
    if re.fullmatch(r"remote-[1-9][0-9]*", voice):
        slot = int(voice.split("-")[-1])
        if slot > 100:
            return voice, str(segment.get("speaker") or f"Восстановленный голос {slot - 100}")
        return voice, str(segment.get("speaker") or f"Собеседник {voice.split('-')[-1]}")
    name = str(segment.get("speaker") or "")
    if name and not re.fullmatch(r"(?:Спикер|Собеседник)\s*\d*", name):
        return "named-" + hashlib.sha256(name.casefold().encode()).hexdigest()[:12], name
    return "remote-1", "Собеседник 1"


class SpeakerEdits:
    def __init__(self, archive_root: Path):
        self.root = archive_root
        self.lock = threading.RLock()

    def _path(self, meeting_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", meeting_id) or meeting_id in {".", ".."}:
            raise ValueError("Некорректная встреча")
        return self.root / meeting_id / "meeting.json"

    def _read(self, meeting_id: str) -> dict:
        try:
            return json.loads(self._path(meeting_id).read_text())
        except FileNotFoundError:
            return {"version": 1, "meeting_id": meeting_id, "segments": []}

    def _write(self, meeting_id: str, snapshot: dict) -> None:
        path = self._path(meeting_id)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        canonical = self._read(meeting_id)
        for field in ("meeting", "status", "started_at", "updated_at", "latest_at", "capture_warnings"):
            if field in snapshot:
                canonical[field] = snapshot[field]
        canonical["segments"] = snapshot["segments"]
        canonical["speaker_names"] = snapshot.get("speaker_names", {})
        canonical["speaker_revision"] = int(canonical.get("speaker_revision", 0)) + 1
        canonical["speaker_corrected_at"] = datetime.now(timezone.utc).isoformat()
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(canonical, ensure_ascii=False, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)

    @staticmethod
    def _name(value: str) -> str:
        value = str(value).strip()
        if not value or len(value) > 80 or any(ord(char) < 32 for char in value):
            raise ValueError("Укажите имя длиной до 80 символов без переносов строк")
        return value

    def annotate(self, snapshot: dict) -> dict:
        result = copy.deepcopy(snapshot)
        meeting_id = str(result.get("meeting_id") or "")
        if not meeting_id:
            return result
        with self.lock:
            canonical = self._read(meeting_id)
        names = canonical.get("speaker_names", {})
        corrected = {segment_id(s): s for s in canonical.get("segments", [])
                     if s.get("speaker_identity") == "manual"}
        counts = Counter()
        labels = dict(names)
        for segment in result.get("segments", []):
            key = segment_id(segment)
            if saved := corrected.get(key):
                for field in ("speaker", "speaker_id", "speaker_confidence", "speaker_identity"):
                    segment[field] = saved[field]
            identity, label = base_speaker(segment)
            segment["segment_id"] = key
            target = identity
            labels.setdefault(target, label if target == identity else "Собеседник")
            label = names.get(target) or labels[target]
            segment["speaker_id"] = target
            segment["speaker_label"] = label
            if target in names:
                segment["speaker"] = label
                segment["speaker_confidence"] = "manual"
                segment["speaker_identity"] = "manual"
            elif target == "unassigned":
                segment["speaker"] = "Распределить"
            counts[target] += 1
        result["speakers"] = [
            {"id": key, "name": labels[key], "count": counts[key],
             "manual": key in names, "unassigned": key == "unassigned"}
            for key in sorted(labels, key=lambda key: (key == "unassigned", key != "self", key))
            if counts[key] or key in names
        ]
        result["speaker_names"] = dict(names)
        result["speaker_revision"] = canonical.get("speaker_revision", 0)
        return result

    def rename(self, snapshot: dict, speaker_id: str, name: str) -> dict:
        name = self._name(name)
        meeting_id = str(snapshot.get("meeting_id") or "")
        with self.lock:
            annotated = self._editing_snapshot(snapshot)
            if speaker_id == "unassigned" or speaker_id not in {p["id"] for p in annotated.get("speakers", [])}:
                raise ValueError("Выберите спикера. Неразмеченные реплики сначала нужно распределить")
            annotated["speaker_names"][speaker_id] = name
            for segment in annotated["segments"]:
                if segment["speaker_id"] == speaker_id:
                    segment.update(speaker=name, speaker_label=name,
                                   speaker_identity="manual", speaker_confidence="manual")
            self._write(meeting_id, annotated)
            return self.annotate(annotated)

    def assign(self, snapshot: dict, segment_ids: list[str], speaker_id: str = "", name: str = "") -> dict:
        if not isinstance(segment_ids, list) or not segment_ids or len(segment_ids) > 20000:
            raise ValueError("Выберите реплики")
        meeting_id = str(snapshot.get("meeting_id") or "")
        with self.lock:
            annotated = self._editing_snapshot(snapshot)
            available = {segment["segment_id"] for segment in annotated.get("segments", [])}
            if not set(segment_ids) <= available:
                raise ValueError("Стенограмма изменилась. Откройте разметку снова")
            if name:
                name = self._name(name)
                speaker_id = "manual-" + hashlib.sha256(name.casefold().encode()).hexdigest()[:12]
                annotated["speaker_names"][speaker_id] = name
            elif speaker_id not in {p["id"] for p in annotated.get("speakers", [])} or speaker_id == "unassigned":
                raise ValueError("Укажите участника или новое имя")
            # Remember the default label so assigned snippets have a name even
            # when the automatic source group disappears on the next refresh.
            label = annotated["speaker_names"].get(speaker_id) or next(p["name"] for p in annotated["speakers"] if p["id"] == speaker_id)
            selected = set(segment_ids)
            for segment in annotated["segments"]:
                if segment["segment_id"] in selected:
                    segment.update(speaker_id=speaker_id, speaker=label, speaker_label=label,
                                   speaker_identity="manual", speaker_confidence="manual")
            self._write(meeting_id, annotated)
            return self.annotate(annotated)

    def _editing_snapshot(self, snapshot: dict) -> dict:
        # A stale browser or capture snapshot must not erase archived turns.
        result = copy.deepcopy(snapshot)
        canonical = self._read(str(result.get("meeting_id") or ""))
        segments = {segment_id(s): s for s in canonical.get("segments", [])}
        segments.update({segment_id(s): s for s in result.get("segments", [])})
        result["segments"] = sorted(segments.values(), key=lambda s: str(s.get("timestamp") or ""))
        return self.annotate(result)
