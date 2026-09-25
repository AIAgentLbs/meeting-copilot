#!/usr/bin/env python3
"""Durable local meeting archive and illustrated report generation."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def _date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.") or "meeting"


def _fmt_seconds(seconds: int | float | None) -> str:
    total = max(0, int(seconds or 0))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class MeetingArchive:
    """Joins transcript, notes, Zoom chat, screenshots and recording metadata."""

    product_name = "Meeting Copilot by aiagentlbs.com"
    generic_titles = {
        "", "Google Chrome", "Google Chrome Helper", "Google Chrome Helper (Renderer)",
        "Meeting Copilot", "Meeting Copilot Capture", "Zoom", "zoom.us",
    }

    def __init__(
        self,
        recordings_root: Path,
        archive_root: Path,
        reports_root: Path,
        config_root: Path,
    ) -> None:
        self.recordings_root = recordings_root
        self.archive_root = archive_root
        self.reports_root = reports_root
        self.config_root = config_root
        self.lock = threading.RLock()
        self.archive_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.reports_root.mkdir(mode=0o700, parents=True, exist_ok=True)

    @property
    def journal(self) -> list[dict]:
        return list(_json(self.config_root / "journal.json", {}).get("items", []))

    @property
    def frames(self) -> list[dict]:
        return list(_json(self.config_root / "frames.json", {}).get("items", []))

    @property
    def meeting_chat(self) -> list[dict]:
        return list(_json(self.config_root / "meeting-chat.json", {}).get("items", []))

    def sync_transcript(self, transcript: dict) -> None:
        meeting_id = str(transcript.get("meeting_id") or "").strip()
        if not meeting_id:
            return
        clean = {
            "version": 1,
            "meeting_id": meeting_id,
            "meeting": str(transcript.get("meeting") or "Без названия"),
            "status": str(transcript.get("status") or "idle"),
            "started_at": str(transcript.get("started_at") or ""),
            "updated_at": str(transcript.get("updated_at") or ""),
            "latest_at": str(transcript.get("latest_at") or ""),
            "segments": list(transcript.get("segments") or []),
        }
        target = self.archive_root / _safe(meeting_id) / "meeting.json"
        previous = _json(target, {})
        # Never replace a longer completed transcript with a shorter stale one.
        if len(previous.get("segments", [])) > len(clean["segments"]):
            clean["segments"] = previous["segments"]
        if previous != clean:
            _atomic_json(target, clean)

    def _recordings(self) -> list[dict]:
        result: list[dict] = []
        if not self.recordings_root.exists():
            return result
        for meta_path in sorted(self.recordings_root.glob("*/meta.json"), reverse=True):
            meta = _json(meta_path, {})
            if not isinstance(meta, dict):
                continue
            result.append({
                "dir": str(meta_path.parent),
                "folder": meta_path.parent.name,
                "started_at": str(meta.get("started") or ""),
                "ended_at": str(meta.get("ended") or ""),
                "duration_seconds": int(meta.get("duration_seconds") or 0),
                "app": str(meta.get("app") or ""),
                "meta": meta,
            })
        return result

    @staticmethod
    def _item_time(item: dict) -> datetime | None:
        for key in ("captured_at", "created_at", "anchor_at", "timestamp"):
            parsed = _date(str(item.get(key) or ""))
            if parsed:
                return parsed
        return None

    def _match_recording(self, times: list[datetime], started_at: str = "") -> dict | None:
        if started := _date(started_at):
            times = [started, *times]
        recordings = self._recordings()
        best: tuple[float, dict] | None = None
        for recording in recordings:
            start = _date(recording["started_at"])
            end = _date(recording["ended_at"])
            if not start:
                continue
            for point in times:
                distance = abs((point - start).total_seconds())
                inside = point >= start and (end is None or point <= end)
                score = distance if inside else distance + 86400
                if best is None or score < best[0]:
                    best = (score, recording)
        return best[1] if best and best[0] < 90000 else None

    @classmethod
    def _is_generic_title(cls, value: str) -> bool:
        clean = value.strip()
        return clean in cls.generic_titles or clean.startswith("Google Chrome Helper")

    @classmethod
    def _speaker_title(cls, snapshot: dict) -> str:
        names: list[str] = []
        ignored = {"я", "me", "собеседник", "собеседники", "speaker", "speakers"}
        for segment in snapshot.get("segments", []):
            for candidate in str(segment.get("speaker") or "").split(" / "):
                name = candidate.strip()
                folded = name.casefold()
                if (
                    not name
                    or folded in ignored
                    or re.fullmatch(r"(?:спикер|speaker|remote)[ -]?\d+", folded)
                    or any(existing.casefold() == folded for existing in names)
                ):
                    continue
                names.append(name)
        if names:
            return "Встреча: " + ", ".join(names[:4])
        started = _date(str(snapshot.get("started_at") or ""))
        return (
            "Встреча " + started.astimezone().strftime("%d.%m.%Y %H:%M")
            if started else "Встреча без названия"
        )

    @classmethod
    def _recording_title(cls, recording: dict) -> str:
        title = str(recording.get("folder") or "").split(" ", 1)[-1].strip()
        if not cls._is_generic_title(title):
            return title
        started = _date(str(recording.get("started_at") or ""))
        return (
            "Запись " + started.astimezone().strftime("%d.%m.%Y %H:%M")
            if started else "Запись без названия"
        )

    @classmethod
    def _best_title(cls, snapshot: dict, frames: list[dict], recording: dict | None) -> str:
        title = str(snapshot.get("meeting") or "").strip()
        visible = [
            str(item.get("window_title") or "").replace(" 🔊", "").strip()
            for item in frames
        ]
        visible = [value for value in visible if value and "Meeting Copilot" not in value]
        if visible:
            most_common = Counter(visible).most_common(1)[0][0]
            if cls._is_generic_title(title) and not cls._is_generic_title(most_common):
                title = most_common
        if cls._is_generic_title(title) and recording:
            recording_title = recording["folder"].split(" ", 1)[-1]
            if not cls._is_generic_title(recording_title):
                title = recording_title
        return cls._speaker_title(snapshot) if cls._is_generic_title(title) else title

    def display_title(self, snapshot: dict) -> str:
        """Human meeting title for live UI; never expose a browser helper process."""
        meeting_id = str(snapshot.get("meeting_id") or "")
        frames = [
            item for item in self.frames
            if str(item.get("meeting_id") or "") == meeting_id
        ]
        return self._best_title(snapshot, frames, None)

    def _known_ids(self) -> set[str]:
        ids = {
            path.parent.name
            for path in self.archive_root.glob("*/meeting.json")
            if path.parent.name
        }
        for item in [*self.journal, *self.frames, *self.meeting_chat]:
            if item.get("meeting_id"):
                ids.add(str(item["meeting_id"]))
        return ids

    def detail(self, meeting_id: str) -> dict | None:
        meeting_id = _safe(meeting_id)
        snapshot = _json(self.archive_root / meeting_id / "meeting.json", {})
        participant_context = _json(
            self.archive_root / meeting_id / "participants.json", {}
        )
        participants = (
            list(participant_context.get("participants") or [])
            if isinstance(participant_context, dict)
            else []
        )
        journal = [i for i in self.journal if str(i.get("meeting_id")) == meeting_id]
        frames = [i for i in self.frames if str(i.get("meeting_id")) == meeting_id]
        chat = [i for i in self.meeting_chat if str(i.get("meeting_id")) == meeting_id]
        if not snapshot and not journal and not frames and not chat:
            for candidate in self._recordings():
                candidate_id = "recording-" + hashlib.sha1(
                    candidate["folder"].encode("utf-8")
                ).hexdigest()[:16]
                if candidate_id != meeting_id:
                    continue
                return {
                    "meeting_id": meeting_id,
                    "title": self._recording_title(candidate),
                    "status": "recording_only",
                    "started_at": candidate["started_at"],
                    "ended_at": candidate["ended_at"],
                    "duration_seconds": candidate["duration_seconds"],
                    "recording_dir": candidate["dir"],
                    "audio_file": self._audio_file(candidate),
                    "transcript": [], "journal": [], "frames": [], "meeting_chat": [],
                    "participants": participants,
                    "report": {},
                }
            return None
        times = [
            parsed for parsed in map(self._item_time, [*journal, *frames, *chat]) if parsed
        ]
        recording = self._match_recording(times, str(snapshot.get("started_at") or ""))
        title = self._best_title(snapshot, frames, recording)
        segments = list(snapshot.get("segments") or [])
        started = str(snapshot.get("started_at") or (recording or {}).get("started_at") or "")
        ended = str(
            (recording or {}).get("ended_at")
            or snapshot.get("latest_at")
            or snapshot.get("updated_at")
            or ""
        )
        duration = int((recording or {}).get("duration_seconds") or 0)
        report_dir = self.reports_root / meeting_id
        report_meta = _json(report_dir / "report.json", {})
        return {
            "meeting_id": meeting_id,
            "title": title,
            "status": str(snapshot.get("status") or "finished"),
            "started_at": started,
            "ended_at": ended,
            "duration_seconds": duration,
            "recording_dir": (recording or {}).get("dir", ""),
            "audio_file": self._audio_file(recording),
            "transcript": segments,
            "journal": sorted(journal, key=lambda i: str(i.get("created_at") or "")),
            "frames": sorted(frames, key=lambda i: str(i.get("captured_at") or "")),
            "meeting_chat": sorted(chat, key=lambda i: str(i.get("captured_at") or "")),
            "participants": participants,
            "report": report_meta,
        }

    @staticmethod
    def _dedupe_items(items: list[dict], time_key: str) -> list[dict]:
        result: list[dict] = []
        seen: set[str] = set()
        for item in sorted(items, key=lambda value: str(value.get(time_key) or "")):
            identity = str(item.get("id") or "")
            if not identity:
                identity = hashlib.sha1(
                    json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
            if identity in seen:
                continue
            seen.add(identity)
            result.append(item)
        return result

    def _continuous_chain(self, target: dict, max_gap_seconds: int = 90) -> list[dict]:
        """Return recorder chunks belonging to the same uninterrupted call."""
        candidates: list[dict] = []
        target_title = str(target.get("title") or "").strip().casefold()
        for meeting_id in self._known_ids():
            detail = self.detail(meeting_id)
            if not detail or not detail.get("recording_dir"):
                continue
            if str(detail.get("title") or "").strip().casefold() != target_title:
                continue
            if not _date(str(detail.get("started_at") or "")):
                continue
            candidates.append(detail)
        candidates.sort(key=lambda value: str(value.get("started_at") or ""))
        index = next(
            (
                position for position, item in enumerate(candidates)
                if item.get("meeting_id") == target.get("meeting_id")
            ),
            None,
        )
        if index is None:
            return [target]
        first = index
        while first > 0:
            previous = candidates[first - 1]
            current = candidates[first]
            previous_end = _date(str(previous.get("ended_at") or ""))
            current_start = _date(str(current.get("started_at") or ""))
            if not previous_end or not current_start:
                break
            gap = (current_start - previous_end).total_seconds()
            if gap < 0 or gap > max_gap_seconds:
                break
            first -= 1
        last = index
        while last + 1 < len(candidates):
            current = candidates[last]
            following = candidates[last + 1]
            current_end = _date(str(current.get("ended_at") or ""))
            following_start = _date(str(following.get("started_at") or ""))
            if not current_end or not following_start:
                break
            gap = (following_start - current_end).total_seconds()
            if gap < 0 or gap > max_gap_seconds:
                break
            last += 1
        return candidates[first:last + 1]

    def report_detail(self, meeting_id: str) -> dict | None:
        """Build one report payload from all contiguous recorder chunks."""
        target = self.detail(meeting_id)
        if not target:
            return None
        chain = self._continuous_chain(target)
        canonical = dict(chain[-1])
        canonical["started_at"] = chain[0].get("started_at", "")
        canonical["ended_at"] = chain[-1].get("ended_at", "")
        start = _date(str(canonical["started_at"] or ""))
        end = _date(str(canonical["ended_at"] or ""))
        canonical["duration_seconds"] = (
            max(0, int((end - start).total_seconds()))
            if start and end else sum(int(item.get("duration_seconds") or 0) for item in chain)
        )
        canonical["transcript"] = self._dedupe_items(
            [entry for item in chain for entry in item.get("transcript", [])],
            "timestamp",
        )
        canonical["journal"] = self._dedupe_items(
            [entry for item in chain for entry in item.get("journal", [])],
            "created_at",
        )
        canonical["frames"] = self._dedupe_items(
            [entry for item in chain for entry in item.get("frames", [])],
            "captured_at",
        )
        canonical["meeting_chat"] = self._dedupe_items(
            [entry for item in chain for entry in item.get("meeting_chat", [])],
            "captured_at",
        )
        participants: list[dict] = []
        participant_names: set[str] = set()
        for item in chain:
            for participant in item.get("participants", []):
                name = str(participant.get("name") or "").strip().casefold()
                if name and name not in participant_names:
                    participant_names.add(name)
                    participants.append(participant)
        canonical["participants"] = participants
        canonical["source_meeting_ids"] = [item["meeting_id"] for item in chain]
        canonical["report"] = _json(
            self.reports_root / canonical["meeting_id"] / "report.json", {}
        )
        return canonical

    @staticmethod
    def _audio_file(recording: dict | None) -> str:
        if not recording:
            return ""
        files = recording.get("meta", {}).get("files", {})
        candidates = list(dict.fromkeys(files.values())) if isinstance(files, dict) else []
        for candidate in candidates:
            path = Path(recording["dir"]) / str(candidate)
            if path.exists():
                return str(path)
        return ""

    def list_meetings(self) -> list[dict]:
        details = [self.detail(meeting_id) for meeting_id in self._known_ids()]
        meetings = []
        matched_dirs = set()
        for detail in details:
            if not detail:
                continue
            matched_dirs.add(detail.get("recording_dir"))
            meetings.append(self._summary(detail))
        # Keep raw recording-only sessions visible even when no transcript was captured.
        for recording in self._recordings():
            if recording["dir"] in matched_dirs:
                continue
            meeting_id = "recording-" + hashlib.sha1(
                recording["folder"].encode("utf-8")
            ).hexdigest()[:16]
            meetings.append({
                "meeting_id": meeting_id,
                "title": self._recording_title(recording),
                "status": "recording_only",
                "started_at": recording["started_at"],
                "ended_at": recording["ended_at"],
                "duration_seconds": recording["duration_seconds"],
                "transcript_count": 0,
                "journal_count": 0,
                "frame_count": len(list(Path(recording["dir"]).glob("screenshots/*.jpg"))),
                "chat_count": 0,
                "has_audio": bool(self._audio_file(recording)),
                "has_report": False,
                "drive_status": "",
                "mail_status": "",
                "telegram_status": "",
            })
        return sorted(meetings, key=lambda item: item.get("started_at", ""), reverse=True)

    @staticmethod
    def _summary(detail: dict) -> dict:
        report = detail.get("report") or {}
        return {
            "meeting_id": detail["meeting_id"],
            "title": detail["title"],
            "status": detail["status"],
            "started_at": detail["started_at"],
            "ended_at": detail["ended_at"],
            "duration_seconds": detail["duration_seconds"],
            "transcript_count": len(detail["transcript"]),
            "journal_count": len(detail["journal"]),
            "frame_count": len(detail["frames"]),
            "chat_count": len(detail["meeting_chat"]),
            "has_audio": bool(detail["audio_file"]),
            "has_report": bool(report.get("html") and report.get("pdf")),
            "drive_status": str(report.get("drive_status") or ""),
            "mail_status": str(report.get("mail_status") or ""),
            "telegram_status": str(report.get("telegram_status") or ""),
        }

    @staticmethod
    def _choose_frames(frames: list[dict], limit: int = 18) -> list[dict]:
        existing = [item for item in frames if Path(str(item.get("path") or "")).is_file()]
        if len(existing) <= limit:
            return existing
        indexes = {round(index * (len(existing) - 1) / (limit - 1)) for index in range(limit)}
        return [existing[index] for index in sorted(indexes)]

    def generate_report(self, meeting_id: str) -> dict:
        with self.lock:
            detail = self.report_detail(meeting_id)
            if detail is None:
                raise ValueError("Встреча не найдена")
            if not detail["transcript"] and not detail["journal"] and not detail["frames"]:
                raise ValueError("Для этой записи пока нет стенограммы, заметок или кадров")

            report_dir = self.reports_root / detail["meeting_id"]
            assets = report_dir / "assets"
            assets.mkdir(mode=0o700, parents=True, exist_ok=True)
            for old in assets.glob("*.jpg"):
                old.unlink()

            selected_frames = self._choose_frames(detail["frames"])
            rendered_frames: list[dict] = []
            for index, frame in enumerate(selected_frames, start=1):
                source = Path(str(frame.get("path") or ""))
                target = assets / f"frame-{index:02d}.jpg"
                shutil.copy2(source, target)
                rendered_frames.append({**frame, "asset": f"assets/{target.name}"})

            document = self._report_html(detail, rendered_frames)
            html_path = report_dir / "index.html"
            html_path.write_text(document, encoding="utf-8")
            html_path.chmod(0o600)
            pdf_path = report_dir / "meeting-report.pdf"
            self._print_pdf(html_path, pdf_path)
            pdf_path.chmod(0o600)

            meta = {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "html": f"/api/archive/report/{detail['meeting_id']}/index.html",
                "pdf": f"/api/archive/report/{detail['meeting_id']}/meeting-report.pdf",
                "html_path": str(html_path),
                "pdf_path": str(pdf_path),
                "included_frames": len(rendered_frames),
                "drive_status": "pending",
                "mail_status": "not_configured",
                "telegram_status": "not_configured",
                "source_signature": self.source_signature(detail),
            }
            _atomic_json(report_dir / "report.json", meta)
            delivery = self.deliver(detail, meta)
            meta.update(delivery)
            _atomic_json(report_dir / "report.json", meta)
            return meta

    @staticmethod
    def _print_pdf(html_path: Path, pdf_path: Path) -> None:
        """Print with Chrome, then terminate its lingering headless helper."""
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if not chrome.is_file():
            raise RuntimeError("Google Chrome не найден для создания PDF")
        profile = Path(tempfile.mkdtemp(prefix="meeting-copilot-report-"))
        temporary = pdf_path.with_suffix(".tmp.pdf")
        temporary.unlink(missing_ok=True)
        command = [
            str(chrome), "--headless=new", "--disable-gpu",
            "--disable-background-networking", "--disable-component-update",
            "--disable-sync", "--no-first-run", "--no-default-browser-check",
            "--no-pdf-header-footer", f"--user-data-dir={profile}",
            f"--print-to-pdf={temporary}", html_path.resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            stable = 0
            prior = -1
            for _ in range(80):
                time.sleep(0.25)
                size = temporary.stat().st_size if temporary.exists() else 0
                if size > 4096 and size == prior:
                    stable += 1
                    if stable >= 3:
                        break
                else:
                    stable = 0
                prior = size
            if not temporary.is_file() or temporary.stat().st_size <= 4096:
                raise RuntimeError("Chrome не создал PDF")
            if temporary.read_bytes()[:4] != b"%PDF":
                raise RuntimeError("Chrome создал повреждённый PDF")
            temporary.replace(pdf_path)
        finally:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
            shutil.rmtree(profile, ignore_errors=True)
            temporary.unlink(missing_ok=True)

    @staticmethod
    def source_signature(detail: dict) -> str:
        material = {
            "report_schema": 2,
            "product_name": MeetingArchive.product_name,
            "title": detail.get("title", ""),
            "segments": detail.get("transcript", []),
            "journal": detail.get("journal", []),
            "frames": [
                {key: item.get(key) for key in ("id", "captured_at", "speaker", "path")}
                for item in detail.get("frames", [])
            ],
            "chat": detail.get("meeting_chat", []),
            "participants": detail.get("participants", []),
        }
        return hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def needs_report(self, meeting_id: str) -> bool:
        # The recorder rotates long calls into chunks. A closed chunk must
        # never be mistaken for the end of the Zoom/Meet call while any capture
        # marker is still active.
        if any(self.recordings_root.glob("*/.recording.json")):
            return False
        detail = self.report_detail(meeting_id)
        if not detail or detail.get("status") not in {
            "finished", "complete", "completed", "stopped", "idle"
        }:
            return False
        chain = self._continuous_chain(detail)
        if chain and meeting_id != chain[-1].get("meeting_id"):
            return False
        ended = _date(str(detail.get("ended_at") or ""))
        if not ended or (datetime.now().astimezone() - ended).total_seconds() < 120:
            return False
        if not detail["transcript"] and not detail["journal"] and not detail["frames"]:
            return False
        report = detail.get("report") or {}
        return report.get("source_signature") != self.source_signature(detail)

    @staticmethod
    def _drive_items(
        gog: str, account: str, parent_id: str, name: str
    ) -> list[dict]:
        """Read exact child metadata without changing Drive permissions."""
        escaped = name.replace("'", "\\'")
        command = [
            gog, "--account", account, "--no-input", "--json", "drive", "ls",
            "--parent", parent_id,
            "--query", f"name = '{escaped}' and trashed = false",
            "--fields", "files(id,name,mimeType,webViewLink),nextPageToken",
            "--max", "20",
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30,
            env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        )
        if result.returncode != 0:
            return []
        try:
            payload = json.loads(result.stdout or "{}")
        except ValueError:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        items = payload.get("files") or payload.get("results") or []
        return [item for item in items if isinstance(item, dict)]

    @classmethod
    def _drive_links(
        cls,
        gog: str,
        account: str,
        reports_folder_id: str,
        folder_name: str,
        wait_seconds: int = 75,
    ) -> dict[str, str]:
        """Wait for Drive for Desktop sync, then return provider URLs."""
        if not account or not reports_folder_id:
            return {}
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            folders = cls._drive_items(gog, account, reports_folder_id, folder_name)
            folder = next(
                (
                    item for item in folders
                    if item.get("name") == folder_name
                    and item.get("mimeType") == "application/vnd.google-apps.folder"
                ),
                None,
            )
            folder_id = str((folder or {}).get("id") or "")
            folder_url = str((folder or {}).get("webViewLink") or "")
            if folder_id and folder_url:
                children: dict[str, dict] = {}
                for filename in ("index.html", "meeting-report.pdf"):
                    matches = cls._drive_items(gog, account, folder_id, filename)
                    exact = next(
                        (item for item in matches if item.get("name") == filename), None
                    )
                    if exact:
                        children[filename] = exact
                html_url = str(children.get("index.html", {}).get("webViewLink") or "")
                pdf_url = str(
                    children.get("meeting-report.pdf", {}).get("webViewLink") or ""
                )
                if html_url and pdf_url:
                    return {
                        "drive_folder_url": folder_url,
                        "drive_html_url": html_url,
                        "drive_pdf_url": pdf_url,
                    }
            time.sleep(3)
        return {}

    @classmethod
    def _upload_drive_report(
        cls,
        gog: str,
        account: str,
        reports_folder_id: str,
        folder_name: str,
        source: Path,
    ) -> tuple[str, dict[str, str]]:
        """Upload a report tree through Drive API and read back real URLs."""
        folders = cls._drive_items(gog, account, reports_folder_id, folder_name)
        folder = next(
            (
                item for item in folders
                if item.get("name") == folder_name
                and item.get("mimeType") == "application/vnd.google-apps.folder"
            ),
            None,
        )
        if not folder:
            created = subprocess.run(
                [
                    gog, "--account", account, "--no-input", "--json", "drive",
                    "mkdir", folder_name, "--parent", reports_folder_id,
                ],
                capture_output=True, text=True, timeout=60,
                env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            )
            if created.returncode != 0:
                return ("auth_required" if created.returncode in {4, 6} else "failed", {})
            folders = cls._drive_items(gog, account, reports_folder_id, folder_name)
            folder = next(
                (item for item in folders if item.get("name") == folder_name), None
            )
        folder_id = str((folder or {}).get("id") or "")
        if not folder_id:
            return "failed", {}
        pushed = subprocess.run(
            [
                gog, "--account", account, "--no-input", "--json", "drive",
                "sync", "push", str(source), "--parent", folder_id,
            ],
            capture_output=True, text=True, timeout=180,
            env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
        )
        if pushed.returncode != 0:
            return ("auth_required" if pushed.returncode in {4, 6} else "failed", {})
        links = cls._drive_links(
            gog, account, reports_folder_id, folder_name, wait_seconds=15
        )
        return ("uploaded" if links else "failed"), links

    def deliver(self, detail: dict, report: dict) -> dict:
        settings = _json(self.config_root / "delivery.json", {})
        local_drive = Path(str(settings.get("drive_local_path") or "")).expanduser()
        remote = str(settings.get("drive_remote") or "").strip()
        if not remote and not local_drive:
            return {
                "drive_status": "not_configured",
                "mail_status": "not_configured",
                "telegram_status": "not_configured",
            }
        meeting_started = _date(detail.get("started_at")) or datetime.now().astimezone()
        stamp = meeting_started.strftime("%Y-%m-%d")
        time_stamp = meeting_started.strftime("%H-%M")
        title = re.sub(r"[/\\:*?\"<>|]+", "-", detail["title"]).strip()[:80]
        folder_name = f"{stamp} {time_stamp} {title} [{detail['meeting_id'][-8:]}]"
        source = self.reports_root / detail["meeting_id"]
        drive_status = "not_configured"
        drive_folder = ""
        drive_links: dict[str, str] = {}

        gog = shutil.which("gog")
        recipient = str(settings.get("email_to") or "").strip()
        google_account = str(settings.get("google_account") or recipient).strip()
        reports_folder_id = str(settings.get("drive_folder_id") or "").strip()

        # The API upload is authoritative: delivery proceeds only after Google
        # returns private webViewLink values for both report files.
        if gog and google_account and reports_folder_id:
            drive_status, drive_links = self._upload_drive_report(
                gog, google_account, reports_folder_id, folder_name, source
            )
            drive_folder = drive_links.get("drive_folder_url", "")
        elif local_drive and local_drive.parent.exists():
            try:
                destination_path = local_drive / folder_name
                destination_path.mkdir(mode=0o700, parents=True, exist_ok=True)
                for filename in ("index.html", "meeting-report.pdf"):
                    shutil.copy2(source / filename, destination_path / filename)
                source_assets = source / "assets"
                if source_assets.is_dir():
                    shutil.copytree(
                        source_assets, destination_path / "assets", dirs_exist_ok=True
                    )
                drive_status = "uploaded"
                drive_folder = str(destination_path)
            except OSError:
                drive_status = "failed"
        elif remote:
            destination = f"{remote.rstrip('/')}/{folder_name}"
            command = [
                "/opt/homebrew/bin/rclone", "copy", str(source), destination,
                "--include", "index.html", "--include", "meeting-report.pdf",
                "--include", "assets/**", "--create-empty-src-dirs",
            ]
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=180,
                    env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
                )
                drive_status = "uploaded" if result.returncode == 0 else "auth_required"
            except (OSError, subprocess.TimeoutExpired):
                drive_status = "failed"

        mail_status = "not_configured"
        if gog and drive_status == "uploaded" and not drive_links:
            drive_links = self._drive_links(
                gog, google_account, reports_folder_id, folder_name
            )
        links_text = ""
        if drive_links:
            links_text = (
                "\n\nСсылки Google Drive:\n"
                f"Папка: {drive_links['drive_folder_url']}\n"
                f"HTML: {drive_links['drive_html_url']}\n"
                f"PDF: {drive_links['drive_pdf_url']}"
            )
        if gog and recipient and drive_status == "uploaded":
            subject = f"{self.product_name}: {detail['title']} — {stamp}"
            body = (
                f"Отчёт по встрече «{detail['title']}» от {stamp}.\n\n"
                f"Сформирован {self.product_name}.\n"
                "HTML и PDF сохранены в Google Drive. PDF приложен к письму."
                f"{links_text}"
            )
            try:
                result = subprocess.run(
                    [gog, "--account", recipient, "--no-input", "--json", "gmail",
                     "send", "--to", recipient, "--subject", subject,
                     "--body", body, "--attach", report["pdf_path"]],
                    capture_output=True, text=True, timeout=180,
                )
                if result.returncode == 0:
                    mail_status = "sent"
                elif result.returncode == 4:
                    mail_status = "auth_required"
                else:
                    mail_status = "failed"
            except (OSError, subprocess.TimeoutExpired):
                mail_status = "failed"

        telegram_status = "not_configured"
        telegram_message_id = None
        telegram_config = Path(
            str(settings.get("telegram_config") or "")
        ).expanduser()
        telegram_account = str(settings.get("telegram_account") or "").strip()
        telegram_target = str(settings.get("telegram_target") or "me").strip()
        telegram_helper = Path(__file__).with_name("telegram_delivery.py")
        if telegram_account and telegram_config.is_file() and drive_status == "uploaded":
            command = [
                "/opt/homebrew/bin/python3", str(telegram_helper),
                "--config", str(telegram_config),
                "--account", telegram_account,
                "--target", telegram_target,
                "--pdf", report["pdf_path"],
                "--title", detail["title"],
                "--date", stamp,
            ]
            for key, flag in (
                ("drive_folder_url", "--drive-folder-url"),
                ("drive_html_url", "--drive-html-url"),
                ("drive_pdf_url", "--drive-pdf-url"),
            ):
                if drive_links.get(key):
                    command.extend([flag, drive_links[key]])
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=180,
                    env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
                )
                payload = json.loads(result.stdout or "{}")
                telegram_status = str(payload.get("status") or "failed")
                telegram_message_id = payload.get("message_id")
            except (OSError, ValueError, subprocess.TimeoutExpired):
                telegram_status = "failed"
        return {
            "drive_status": drive_status,
            "drive_folder": drive_folder,
            **drive_links,
            "drive_links_status": "ready" if drive_links else "unavailable",
            "mail_status": mail_status,
            "telegram_status": telegram_status,
            "telegram_message_id": telegram_message_id,
        }

    def report_path(self, meeting_id: str, relative: str) -> Path | None:
        base = (self.reports_root / _safe(meeting_id)).resolve()
        target = (base / relative).resolve()
        if base not in target.parents and target != base:
            return None
        return target if target.is_file() else None

    def frame_path(self, frame_id: str) -> Path | None:
        for item in self.frames:
            if str(item.get("id")) == frame_id:
                path = Path(str(item.get("path") or ""))
                return path if path.is_file() else None
        return None

    def _report_html(self, detail: dict, frames: list[dict]) -> str:
        esc = lambda value: html.escape(str(value or ""))
        title = esc(detail["title"])
        started = _date(detail["started_at"])
        date_label = started.astimezone().strftime("%d.%m.%Y %H:%M") if started else "—"
        duration = _fmt_seconds(detail["duration_seconds"])
        groups: dict[str, list[dict]] = {}
        for item in detail["journal"]:
            groups.setdefault(str(item.get("category") or "OTHER"), []).append(item)

        labels = {
            "FACT": "Факты", "CONTRADICTION": "Противоречия", "HISTORY": "История",
            "RISK": "Риски", "COMMITMENT": "Обязательства", "DECISION": "Решения",
            "ASK": "Что спросить", "QUESTION": "Заданные вопросы", "NOTE": "Мои заметки",
            "URL": "Ссылки", "PRODUCT": "Продукты", "SERVICE": "Сервисы",
        }
        priority = ["DECISION", "COMMITMENT", "RISK", "ASK", "FACT", "HISTORY"]
        summary_items = []
        for category in priority:
            for item in groups.get(category, [])[-4:]:
                summary_items.append(
                    f'<li><strong>{esc(labels[category])}.</strong> {esc(item.get("text"))}</li>'
                )
            if len(summary_items) >= 12:
                break

        toc = [
            '<li><a href="#summary">Краткое резюме</a></li>',
        ]
        if detail.get("participants"):
            toc.append('<li><a href="#participants">Справка о собеседниках</a></li>')
        toc.append('<li><a href="#notes">Заметки и сигналы</a></li>')
        if detail["meeting_chat"]:
            toc.append('<li><a href="#chat">Чат встречи</a></li>')
        if frames:
            toc.append('<li><a href="#frames">Ключевые кадры</a></li>')
        if detail["transcript"]:
            toc.append('<li><a href="#transcript">Стенограмма</a></li>')

        notes_sections = []
        for category in [*priority, "CONTRADICTION", "QUESTION", "NOTE", "URL", "PRODUCT", "SERVICE"]:
            items = groups.get(category, [])
            if not items:
                continue
            rows = "".join(
                f'<article class="note"><div class="time">{esc(item.get("timecode") or "")}</div>'
                f'<p>{esc(item.get("text"))}</p></article>' for item in items
            )
            notes_sections.append(f'<h3>{esc(labels.get(category, category))}</h3>{rows}')

        chat_html = "".join(
            f'<article class="chat"><strong>{esc(item.get("sender") or "Участник")}</strong>'
            f'<span>{esc(item.get("displayed_at") or "")}</span><p>{esc(item.get("text"))}</p></article>'
            for item in detail["meeting_chat"]
        )
        frames_html = "".join(
            f'<figure><img src="{esc(item["asset"])}" alt="Кадр встречи">'
            f'<figcaption>{esc(item.get("speaker") or item.get("window_title") or "Кадр встречи")} · '
            f'{esc((_date(item.get("captured_at")) or datetime.now().astimezone()).strftime("%H:%M:%S"))}'
            f'</figcaption></figure>' for item in frames
        )
        transcript_html = "".join(
            f'<article class="utterance"><div><strong>{esc(item.get("speaker") or ("Я" if item.get("source") == "microphone" else "Собеседник"))}</strong>'
            f'<time>{esc((_date(item.get("timestamp")) or datetime.now().astimezone()).strftime("%H:%M:%S"))}</time></div>'
            f'<p>{esc(item.get("text"))}</p>'
            f'{"<p class=\"translated\"><strong>EN:</strong> " + esc(item.get("translation_en")) + "</p>" if item.get("translation_en") else ""}'
            f'</article>' for item in detail["transcript"]
        )

        participant_cards = []
        for participant in detail.get("participants", []):
            identities = []
            for identity in participant.get("identities", []):
                label = f'{identity.get("kind", "контакт")}: {identity.get("value", "")}'
                url = str(identity.get("url") or "").strip()
                identities.append(
                    f'<a class="identity" href="{esc(url)}">{esc(label)}</a>'
                    if url.startswith(("https://", "http://"))
                    else f'<span class="identity">{esc(label)}</span>'
                )

            public_facts = []
            for fact in participant.get("public_facts", []):
                source = esc(fact.get("source") or "публичный источник")
                url = str(fact.get("url") or "").strip()
                source_html = (
                    f'<a href="{esc(url)}">{source}</a>'
                    if url.startswith(("https://", "http://")) else source
                )
                public_facts.append(
                    f'<li>{esc(fact.get("text"))}<div class="provenance">Публично · {source_html}</div></li>'
                )

            correspondence = []
            for item in participant.get("prior_correspondence", []):
                scope = str(item.get("scope") or "local")
                badge = "Не найдено" if scope == "none" else "Локальный архив"
                source = str(item.get("source") or "").strip()
                source_html = f'<div class="provenance">Источник: {esc(source)}</div>' if source else ""
                correspondence.append(
                    f'<article class="correspondence"><h4>{esc(item.get("channel") or "Канал")} '
                    f'<span>{esc(item.get("period") or "")}</span></h4>'
                    f'<div class="evidence {esc(scope)}">{badge}</div>'
                    f'<p>{esc(item.get("summary"))}</p>{source_html}</article>'
                )

            caveats = "".join(
                f'<li>{esc(value)}</li>' for value in participant.get("caveats", [])
            )
            participant_cards.append(
                f'<article class="participant"><h3>{esc(participant.get("name") or "Собеседник")}</h3>'
                f'<div class="identities">{"".join(identities)}</div>'
                f'<p>{esc(participant.get("public_summary") or "")}</p>'
                f'{"<h4>Подтверждённая публичная информация</h4><ul>" + "".join(public_facts) + "</ul>" if public_facts else ""}'
                f'{"<h4>Предыдущая коммуникация</h4>" + "".join(correspondence) if correspondence else ""}'
                f'{"<h4>Ограничения данных</h4><ul class=\"caveats\">" + caveats + "</ul>" if caveats else ""}'
                f'</article>'
            )
        participants_html = "".join(participant_cards)

        return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>
<style>
@page {{ size: A4; margin: 18mm 17mm 20mm; @bottom-center {{ content: "Meeting Copilot by aiagentlbs.com · " counter(page) " / " counter(pages); color:#66736d; font-size:9pt; }} }}
*{{box-sizing:border-box}} body{{font-family:"DejaVu Sans",Arial,sans-serif;color:#18211e;line-height:1.48;font-size:10.5pt;margin:0;letter-spacing:0}}
h1{{font-size:26pt;line-height:1.1;margin:0 0 8mm;color:#174c3e}} h2{{font-size:18pt;color:#174c3e;border-bottom:1px solid #cad7d2;padding-bottom:2mm;margin:11mm 0 4mm}} h3{{font-size:13pt;margin:7mm 0 2mm}}
.brand{{font-size:9pt;text-transform:uppercase;letter-spacing:.13em;color:#2c6958;font-weight:700;margin-bottom:5mm}} .meta{{display:flex;gap:10mm;color:#56615d;margin-bottom:8mm}}
.toc{{background:#eff5f2;border:1px solid #d7e3de;border-radius:8px;padding:5mm 7mm}} .toc h2{{border:0;margin:0 0 2mm;font-size:14pt}} a{{color:#205c4c;text-decoration:none}}
.summary{{background:#f7f4ea;border-left:4px solid #b98a2f;padding:4mm 6mm}} li{{margin:0 0 2mm}}
.participant{{border:1px solid #d7e3de;border-radius:8px;padding:5mm 6mm;margin:0 0 6mm;background:#fbfdfc}} .participant h3{{color:#174c3e;margin:0 0 2mm}} .participant h4{{margin:5mm 0 1.5mm;font-size:11pt}} .participant p{{margin:2mm 0}}
.identities{{display:flex;flex-wrap:wrap;gap:2mm;margin-bottom:3mm}} .identity{{background:#e8f1ed;border-radius:999px;padding:1mm 3mm;font-size:8.5pt}} .provenance{{font-size:8pt;color:#66736d;margin-top:1mm;overflow-wrap:anywhere}}
.correspondence{{position:relative;border-left:3px solid #86aa9e;padding:1mm 0 2mm 4mm;margin:2mm 0 4mm;break-inside:avoid}} .correspondence h4{{margin:0 0 1mm}} .correspondence h4 span{{font-weight:400;color:#66736d;margin-left:2mm}} .evidence{{display:inline-block;font-size:7.5pt;text-transform:uppercase;letter-spacing:.05em;color:#215848;background:#e8f1ed;border-radius:3px;padding:.5mm 1.5mm}} .evidence.none{{color:#725825;background:#f5eddc}} .caveats{{color:#56615d}}
.note,.chat,.utterance{{break-inside:avoid;border-bottom:1px solid #e0e5e2;padding:2.5mm 0}} .note p,.chat p,.utterance p{{margin:1mm 0 0}} .time,time,.chat span{{font-size:8.5pt;color:#707b77;margin-left:3mm}}
.utterance .translated{{border-left:2px solid #2c6958;padding-left:3mm;background:#eff5f2}}
.frames{{display:grid;grid-template-columns:1fr 1fr;gap:5mm}} figure{{margin:0;break-inside:avoid}} img{{width:100%;height:auto;border:1px solid #d5ddd9;border-radius:5px}} figcaption{{font-size:8.5pt;color:#65706c;margin-top:1mm}}
.empty{{color:#6c7773;font-style:italic}} .page-break{{break-before:page}}
</style></head><body>
<div class="brand">Meeting Copilot by aiagentlbs.com</div><h1>{title}</h1>
<div class="meta"><span>{esc(date_label)}</span><span>Длительность {esc(duration)}</span><span>{len(detail['transcript'])} реплик</span></div>
<nav class="toc"><h2>Оглавление</h2><ol>{''.join(toc)}</ol></nav>
<section id="summary"><h2>Краткое резюме</h2><div class="summary"><ul>{''.join(summary_items) or '<li>Значимые решения и обязательства автоматически не выделены.</li>'}</ul></div></section>
{f'<section id="participants"><h2>Справка о собеседниках</h2>{participants_html}</section>' if participants_html else ''}
<section id="notes"><h2>Заметки и сигналы</h2>{''.join(notes_sections) or '<p class="empty">Заметок пока нет.</p>'}</section>
{f'<section id="chat"><h2>Чат встречи</h2>{chat_html}</section>' if chat_html else ''}
{f'<section id="frames" class="page-break"><h2>Ключевые кадры</h2><div class="frames">{frames_html}</div></section>' if frames_html else ''}
{f'<section id="transcript" class="page-break"><h2>Стенограмма</h2>{transcript_html}</section>' if transcript_html else ''}
</body></html>'''
