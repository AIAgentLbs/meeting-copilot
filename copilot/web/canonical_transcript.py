"""Read the recorder's completed transcript without rewriting its evidence."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path


def _date(value):
    date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if date.tzinfo is None:
        raise ValueError("Recording time must have a timezone")
    return date


def _retain_live_voices(segments, live):
    """Carry only unambiguous acoustic evidence, never invent a named speaker."""
    remote = sorted((s for s in live if s.get("source") == "system"),
                    key=lambda s: s.get("timestamp", ""))
    windows = []
    for item in remote:
        voice = item.get("voice_id", "")
        if not re.fullmatch(r"remote-[1-9][0-9]*", voice):
            continue
        try:
            start = _date(item["timestamp"])
            # A first callback is not proof of coverage for later speech.
            # New exporters supply the last actual decoded observation.
            if not item.get("end_timestamp"):
                continue
            end = _date(item["end_timestamp"])
            windows.append((start, end, voice))
        except (ValueError, KeyError, TypeError):
            continue
    for segment in segments:
        if segment["source"] != "system" or segment.get("voice_id"):
            continue
        start, end = _date(segment["timestamp"]), _date(segment["end_timestamp"])
        overlap = {}
        for first, last, voice in windows:
            seconds = max(0, (min(end, last) - max(start, first)).total_seconds())
            if seconds:
                overlap[voice] = overlap.get(voice, 0) + seconds
        # A final sentence spanning two live voices cannot safely be assigned
        # to either one; keep it unlabelled instead of collapsing the speakers.
        if len(overlap) == 1 and sum(overlap.values()) >= (end - start).total_seconds() * 0.7:
            segment["voice_id"] = next(iter(overlap))
            segment["speaker_confidence"] = "acoustic-diarization"


def canonical_segments(payload):
    """None means use live/recovery, not an empty replacement on read failure."""
    if payload.get("status") != "finished" or not payload.get("recording_dir"):
        return None
    try:
        root = Path(payload["recording_dir"])
        meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
        started = _date(meta["started"])
        if started != _date(payload["started_at"]):
            return None  # Never attach a different physical recording.
        path = root / "transcript.json"
        if path.stat().st_size > 32 * 1024 * 1024:
            return None
        final = json.loads(path.read_text(encoding="utf-8"))
        if not final.get("engine") or not final.get("segments"):
            return None
        segments = []
        voices = {}
        for item in final["segments"]:
            speaker = item["speaker"]
            if not re.fullmatch(r"(?:me|them)(?: [A-Z]+)?", speaker):
                return None
            start, end = item["start_ms"], item["end_ms"]
            if not (isinstance(start, int) and isinstance(end, int) and 0 <= start <= end):
                return None
            text = item["text"].strip()
            if not text:
                continue

            def timestamp(milliseconds):
                at = started + timedelta(milliseconds=milliseconds)
                return at.isoformat(timespec="milliseconds" if at.microsecond else "seconds")

            segment = {"source": "microphone" if speaker.startswith("me") else "system",
                       "timestamp": timestamp(start), "end_timestamp": timestamp(end),
                       "text": text, "provisional": False}
            if speaker.startswith("them "):
                voices.setdefault(speaker, f"remote-{len(voices) + 1}")
                segment["voice_id"] = voices[speaker]
                segment["speaker_confidence"] = "acoustic-diarization"
            segments.append(segment)
        if segments:
            _retain_live_voices(segments, payload.get("segments", []))
        return sorted(segments, key=lambda s: s["timestamp"]) or None
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return None
