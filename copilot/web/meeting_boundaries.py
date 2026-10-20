"""Logical meeting intervals over unchanged physical recordings; no speech stored."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class BoundaryConflict(ValueError):
    pass


class BoundaryUnavailable(ValueError):
    pass


def epoch(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def interval_contains(interval, value):
    stamp, start, end = epoch(value), epoch(interval.get("start")), epoch(interval.get("end"))
    return stamp is not None and start is not None and stamp >= start and (end is None or stamp < end)


class MeetingBoundaries:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.revision = 0
        self.data = {"version": 1, "sessions": {}, "requests": {}}
        if path.exists():
            self.data = json.loads(path.read_text())
            self._validate(self.data)

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("sessions"), dict) or not isinstance(data.get("requests"), dict):
            raise ValueError("Invalid meeting boundary store; restore its backup before splitting")
        ids = set()
        for physical_id, parts in data["sessions"].items():
            if not isinstance(parts, list) or not parts or parts[0].get("meeting_id") != physical_id:
                raise ValueError("Invalid meeting intervals")
            for index, part in enumerate(parts):
                if not isinstance(part, dict) or not part.get("meeting_id") or part["meeting_id"] in ids or epoch(part.get("start")) is None:
                    raise ValueError("Invalid meeting interval identity/time")
                ids.add(part["meeting_id"])
                if index and parts[index - 1].get("end") != part["start"]:
                    raise ValueError("Noncontiguous meeting intervals")
                if part.get("end") is not None and (epoch(part["end"]) is None or epoch(part["end"]) <= epoch(part["start"])):
                    raise ValueError("Invalid interval end")
                if index < len(parts) - 1 and part.get("end") is None:
                    raise ValueError("Unclosed meeting interval")
        for token, request in data["requests"].items():
            if not isinstance(token, str) or not isinstance(request, dict) or not isinstance(request.get("result"), dict):
                raise ValueError("Invalid boundary request")

    def _commit(self, data):
        self._validate(data)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".boundaries-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as stream:
                json.dump(data, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.data = data
        self.revision += 1

    def split(self, physical: dict, expected_id: str, token: str, title: str, boundary_at: str) -> dict:
        title = str(title).strip()
        if not token or len(token) > 128 or len(title) > 200 or any(ord(c) < 32 for c in title):
            raise ValueError("Invalid title or request token")
        physical_id = str(physical.get("meeting_id") or "")
        request_key = {"physical_id": physical_id, "expected_id": expected_id, "title": title}
        with self.lock:
            prior = self.data["requests"].get(token)
            if prior:
                if prior["input"] != request_key:
                    raise BoundaryConflict("Request token already used for a different meeting")
                return dict(prior["result"])
            start, boundary = epoch(physical.get("started_at")), epoch(boundary_at)
            if physical.get("status") != "recording" or not physical_id or start is None:
                raise BoundaryUnavailable("Audio recording is not active or its identity is unknown")
            data = copy.deepcopy(self.data)
            parts = data["sessions"].setdefault(physical_id, [{"meeting_id": physical_id, "title": physical.get("meeting", ""), "start": physical["started_at"], "end": None}])
            last = parts[-1]
            if last["meeting_id"] != expected_id or last["end"] is not None or boundary is None or boundary <= epoch(last["start"]):
                raise BoundaryConflict("Meeting changed; refresh and confirm again")
            last["end"] = boundary_at
            logical_id = str(uuid.uuid4())
            title = title or "Meeting " + datetime.fromtimestamp(boundary, timezone.utc).strftime("%H:%M")
            parts.append({"meeting_id": logical_id, "title": title, "start": boundary_at, "end": None})
            result = {"meeting_id": logical_id, "physical_meeting_id": physical_id, "title": title, "started_at": boundary_at}
            data["requests"][token] = {"input": request_key, "result": result}
            self._commit(data)
            return dict(result)

    def retry_result(self, physical_id: str, expected_id: str, token: str, title: str):
        with self.lock:
            prior = self.data["requests"].get(token)
            if not prior:
                return None
            if prior["input"] != {"physical_id": physical_id, "expected_id": expected_id, "title": str(title).strip()}:
                raise BoundaryConflict("Request token already used for a different meeting")
            return dict(prior["result"])

    def project(self, physical: dict) -> list[dict]:
        with self.lock:
            parts = copy.deepcopy(self.data["sessions"].get(physical.get("meeting_id")))
            if not parts:
                return [{**physical, "physical_meeting_id": physical.get("meeting_id", "")}]
            if physical.get("status") == "finished" and parts[-1]["end"] is None:
                end = physical.get("ended_at") or physical.get("updated_at") or physical.get("latest_at")
                if epoch(end) is not None and epoch(end) > epoch(parts[-1]["start"]):
                    data = copy.deepcopy(self.data)
                    data["sessions"][physical["meeting_id"]][-1]["end"] = end
                    self._commit(data)
                    parts[-1]["end"] = end
        result = []
        origin = epoch(physical["started_at"])
        for index, part in enumerate(parts):
            interval = {"start": part["start"], "end": part["end"]}
            segments = []
            for source in physical.get("segments", []):
                unknown = epoch(source.get("timestamp")) is None
                if not interval_contains(interval, source.get("timestamp")) and not (unknown and index == 0):
                    continue
                segment = dict(source)
                segment["original_segment_id"] = hashlib.sha256(f"{source.get('source', '')}\n{source.get('timestamp', '')}".encode()).hexdigest()[:24]
                if unknown:
                    segment["boundary_unassigned"] = True
                if part["end"] and epoch(source.get("end_timestamp")) is not None and epoch(source["end_timestamp"]) > epoch(part["end"]):
                    segment["spans_boundary"] = True
                segments.append(segment)
            result.append({**physical, "meeting_id": part["meeting_id"], "meeting": part["title"],
                           "physical_meeting_id": physical["meeting_id"], "physical_started_at": physical["started_at"],
                           "explicit_boundary": True, "logical_interval": interval,
                           "audio_range": {"start_seconds": epoch(part["start"]) - origin,
                                           "end_seconds": epoch(part["end"]) - origin if part["end"] else None},
                           "started_at": part["start"], "ended_at": part["end"] or "",
                           "status": "finished" if part["end"] else physical.get("status"),
                           "latest_at": segments[-1].get("timestamp", "") if segments else "",
                           "segments": segments, "boundary_revision": self.revision})
        return result

    def physical_id(self, logical_id):
        with self.lock:
            for physical_id, parts in self.data["sessions"].items():
                if any(part["meeting_id"] == logical_id for part in parts):
                    return physical_id
        return logical_id

    def open_sessions(self):
        with self.lock:
            return {identity: [part["meeting_id"] for part in parts]
                    for identity, parts in self.data["sessions"].items() if parts[-1]["end"] is None}

    def closed_ids(self):
        with self.lock:
            return [part["meeting_id"] for parts in self.data["sessions"].values()
                    for part in parts if part["end"] is not None]

    def route_event(self, item: dict) -> dict:
        """Route timestamped physical events without mutating persisted originals."""
        if item.get("logical_event"):
            return dict(item)
        with self.lock:
            physical_id = self.physical_id(item.get("physical_meeting_id") or item.get("meeting_id"))
            parts = self.data["sessions"].get(physical_id)
            if not parts:
                return dict(item)
            if item.get("boundary_unassigned"):
                return {**item, "meeting_id": parts[0]["meeting_id"], "physical_meeting_id": physical_id}
            stamp = next((item[k] for k in ("anchor_at", "captured_at", "timestamp", "created_at") if epoch(item.get(k)) is not None), None)
            if stamp is None:
                return {**item, "meeting_id": parts[0]["meeting_id"], "physical_meeting_id": physical_id, "boundary_unassigned": True}
            for part in parts:
                if interval_contains(part, stamp):
                    return {**item, "physical_meeting_id": physical_id, "meeting_id": part["meeting_id"]}
            return {**item, "meeting_id": parts[0]["meeting_id"], "physical_meeting_id": physical_id, "boundary_unassigned": True}
