"""Observe durable audio independently of recognition; never start/stop capture.

Can run beside an old Capture binary during a call. Recovery only sends the
existing `record resume` command after matching a live owner and meeting clock.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, OverflowError):
        return {}


def epoch(value) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError):
        return 0


def owner_alive(pid) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


class RecordingLocations:
    def __init__(self, config: Path, legacy_root: Path, home: Path | None = None):
        self.config, self.legacy_root = config, legacy_root
        self.home = home or Path.home()

    def roots(self) -> list[Path]:
        configured = read_json(self.config).get("recordings_dir")
        candidates = [self.home / "Recordings", self.legacy_root]
        if isinstance(configured, str) and configured.strip():
            candidates.insert(0, Path(configured).expanduser())
        return list(dict.fromkeys(path.resolve() for path in candidates))

    def contains(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(resolved.is_relative_to(root) for root in self.roots())

    def markers(self) -> list[Path]:
        # Preserve unreadable/malformed markers for the delivery safety gate.
        return [path for root in self.roots() for path in root.glob("*/.recording.json")]

    def active(self, started_at: str = "") -> dict | None:
        matches = []
        for path in self.markers():
            if not self.contains(path):
                continue
            marker = read_json(path)
            started = epoch(marker.get("started"))
            if not owner_alive(marker.get("pid")) or not started:
                continue
            if started_at and abs(started - epoch(started_at)) > 2:
                continue
            files = marker.get("files")
            if not isinstance(files, dict):
                continue
            tracks = {}
            for kind in ("mic", "system"):
                name = files.get(kind)
                if not isinstance(name, str) or Path(name).name != name or not name.endswith(".caf"):
                    continue
                track = path.parent / name
                if not self.contains(track):
                    continue
                try:
                    tracks[kind] = {"path": str(track), "bytes": track.stat().st_size}
                except OSError:
                    tracks[kind] = {"path": str(track), "bytes": 0, "missing": True}
            if tracks:
                matches.append({"directory": str(path.parent), "pid": marker["pid"],
                                "started_at": marker["started"], "tracks": tracks})
        return max(matches, key=lambda item: epoch(item["started_at"]), default=None)


class RecordingHealth:
    def __init__(self, locations: RecordingLocations):
        self.locations = locations
        self.lock = threading.RLock()
        self.identity = None
        self.observed = {}

    def sample(self, transcript: dict, now: float | None = None) -> dict:
        now = time.time() if now is None else now
        with self.lock:
            active = self.locations.active(str(transcript.get("started_at") or ""))
            if not active:
                self.identity, self.observed = None, {}
                return {"state": "inactive", "tracks": [], "audio_recording": False}
            identity = (active["directory"], active["pid"])
            if identity != self.identity:
                self.identity, self.observed = identity, {}
            tracks = []
            for kind in ("mic", "system"):
                item = active["tracks"].get(kind)
                if not item or item.get("missing"):
                    tracks.append({"source": kind, "bytes": 0, "state": "stalled",
                                   "last_growth_age_seconds": None})
                    continue
                previous = self.observed.get(kind)
                grew_at = now if previous is None or item["bytes"] > previous[0] else previous[1]
                verified = bool(previous and (item["bytes"] > previous[0] or previous[2]))
                self.observed[kind] = (item["bytes"], grew_at, verified)
                state = "recording" if verified else "verifying"
                if now - grew_at >= 45 or (previous and item["bytes"] < previous[0]):
                    state = "stalled"
                tracks.append({"source": kind, "bytes": item["bytes"], "state": state,
                               "last_growth_age_seconds": max(0, int(now - grew_at))})
            states = {track["state"] for track in tracks}
            state = "stalled" if "stalled" in states else "verifying" if "verifying" in states else "recording"
            if transcript.get("status") == "paused":
                state = "paused"
            return {**active, "tracks": tracks, "state": state,
                    "audio_recording": state == "recording"}


class RecognitionGuard:
    """Singleton, bounded retries. Missing words on a quiet call is not failure."""
    cooldown = 90
    retry_window = 600
    max_attempts = 3

    def __init__(self, health: RecordingHealth, live_file: Path, state_file: Path,
                 binary: Path, runner=None, notifier=None):
        self.health, self.live_file, self.state_file, self.binary = health, live_file, state_file, binary
        self.runner = runner or subprocess.run
        self.notifier = notifier
        self.lock = threading.RLock()
        self.identity = ""
        self.attempts = []
        self.observation = {}

    def _save(self, payload: dict):
        self.state_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, self.state_file)

    def tick(self, *, now=None, manual_meeting_id=None) -> dict:
        now = time.time() if now is None else now
        with self.lock:
            # Protect the command AND persisted cooldown from another process.
            self.state_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with self.state_file.with_suffix(".lock").open("a") as lease:
                os.chmod(lease.name, 0o600)
                try:
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return read_json(self.state_file)
                transcript = read_json(self.live_file)
                capture = self.health.sample(transcript, now)
                meeting_id = str(transcript.get("meeting_id") or "")
                identity = meeting_id + ":" + str(transcript.get("started_at") or "")
                saved = read_json(self.state_file)
                if saved.get("identity") == identity:
                    raw_attempts = saved.get("attempts", [])
                    self.attempts = [v for v in raw_attempts
                                     if not isinstance(v, bool) and isinstance(v, (int, float))
                                     and math.isfinite(v) and now - v < self.retry_window] if isinstance(raw_attempts, list) else []
                else:
                    self.attempts = []
                native_status = str(transcript.get("status") or "")
                age = now - epoch(transcript.get("updated_at"))
                progress = epoch(transcript.get("recognition_progress_at"))
                stalled = (native_status == "overloaded" and age >= 45
                           or native_status == "loading" and age >= 120
                           or native_status == "error" and age >= 10
                           or native_status == "recording" and progress and now - progress >= 60)
                state = "healthy"
                reason = ""
                if capture["state"] == "stalled":
                    state, reason = "action_required", "audio_track_stalled"
                elif stalled:
                    state, reason = "waiting", "recognition_stalled"
                if manual_meeting_id is not None:
                    if not manual_meeting_id or manual_meeting_id != meeting_id:
                        raise ValueError("Встреча изменилась; обновите страницу")
                    if native_status not in {"loading", "overloaded", "error", "recording"}:
                        raise ValueError("Нет активной расшифровки для возобновления")
                    stalled = True
                if stalled and meeting_id and capture["audio_recording"]:
                    # An explicit owner retry may start a fresh bounded budget,
                    # but never bypass the in-flight cooldown.
                    if (manual_meeting_id is not None and len(self.attempts) >= self.max_attempts
                            and now - self.attempts[-1] >= self.cooldown):
                        self.attempts = []
                    if self.attempts and now - self.attempts[-1] < self.cooldown:
                        if (saved.get("reason") == "recognition_resume_failed"
                                and epoch(transcript.get("updated_at")) <= self.attempts[-1]):
                            state, reason = "action_required", "recognition_resume_failed"
                        else:
                            state = "recovering"
                    elif len(self.attempts) >= self.max_attempts:
                        state, reason = "action_required", "recognition_retries_exhausted"
                    else:
                        # Re-read immediately before mutation: no stale tab or
                        # unrelated live exporter may target another recording.
                        current = read_json(self.live_file)
                        active = self.health.locations.active(transcript.get("started_at", ""))
                        if (current.get("meeting_id") != meeting_id or not active
                                or active["pid"] != capture.get("pid")):
                            raise ValueError("Активная встреча изменилась")
                        self.attempts.append(now)  # reserve before command/crash
                        self._save({"identity": identity, "attempts": self.attempts,
                                    "state": "recovering", "meeting_id": meeting_id})
                        try:
                            self.runner([str(self.binary), "record", "resume"],
                                        capture_output=True, text=True, timeout=8, check=True)
                            state, reason = "recovering", "recognition_resume_sent"
                        except (OSError, subprocess.SubprocessError):
                            state, reason = "action_required", "recognition_resume_failed"
                elif manual_meeting_id is not None:
                    raise ValueError("Сначала нужно подтвердить, что аудиодорожки продолжают расти")
                payload = {"identity": identity, "attempts": self.attempts,
                           "meeting_id": meeting_id, "state": state, "reason": reason,
                           "checked_at": now, "capture": capture}
                last_notice = saved.get("last_notice", "") if saved.get("identity") == identity else ""
                notice = ""
                if state == "action_required" and reason != last_notice:
                    notice = reason
                elif (state == "healthy" and capture["audio_recording"]
                      and native_status == "recording" and age <= 30
                      and last_notice and last_notice != "recovered"):
                    notice = "recovered"
                if notice and self.notifier:
                    try:
                        self.notifier(notice)
                    except (OSError, subprocess.SubprocessError):
                        pass
                payload["last_notice"] = notice or last_notice
                self.observation = payload
                self._save(payload)
                return payload

    def loop(self, stop: threading.Event | None = None):
        stop = stop or threading.Event()
        while not stop.is_set():
            try:
                self.tick()
            except (OSError, ValueError):
                pass  # next observation retries; never touch capture on uncertainty
            stop.wait(5)


def default_guard() -> RecognitionGuard:
    home = Path.home()
    root = home / ".local/share/meeting-copilot"
    locations = RecordingLocations(home / ".config/meeting-copilot/config.json", root / "recordings")
    binaries = [Path("/Applications/Meeting Copilot Capture.app/Contents/MacOS/MeetingCopilotCapture"),
                home / "Applications/Meeting Copilot Capture.app/Contents/MacOS/MeetingCopilotCapture"]
    binary = next((candidate for candidate in binaries if candidate.is_file()), binaries[0])
    return RecognitionGuard(RecordingHealth(locations), root / "meeting-copilot-live.json",
                            root / "recording-health.json", binary, notifier=notify_owner)


def notify_owner(reason: str):
    # Generic, fixed copy: never expose a meeting title, transcript or pathname.
    messages = {
        "audio_track_stalled": "Аудиодорожка перестала записываться. Проверьте Meeting Copilot: запись может быть неполной.",
        "recognition_retries_exhausted": "Расшифровка не восстановилась после повторов. Звук сохраняется отдельно; проверьте Meeting Copilot.",
        "recognition_resume_failed": "Не удалось возобновить расшифровку. Аудиозапись не перезапускалась.",
        "recovered": "Запись звука и расшифровка Meeting Copilot снова подтверждены.",
    }
    message = messages.get(reason)
    if message:
        subprocess.run(["/usr/bin/osascript", "-e",
                        'on run argv\ndisplay notification (item 1 of argv) with title "Meeting Copilot"\nend run',
                        message], capture_output=True, text=True, timeout=4, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    guard = default_guard()
    if args.once:
        print(json.dumps(guard.tick(), ensure_ascii=False))
    else:
        guard.loop()
