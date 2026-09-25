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
from datetime import datetime, timedelta
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
    delivery_retry_days = 3
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

            previous_report = detail.get("report") or {}
            source_signature = self.source_signature(detail)
            previous_delivery = dict(previous_report)
            if (previous_report.get("source_signature") != source_signature
                    and previous_report.get("drive_status") == "uploaded"):
                # A revised PDF must replace its Drive copy, but a previously
                # delivered email or Telegram message must never be resent.
                previous_delivery["drive_status"] = "pending"
            meta = {
                "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "html": f"/api/archive/report/{detail['meeting_id']}/index.html",
                "pdf": f"/api/archive/report/{detail['meeting_id']}/meeting-report.pdf",
                "html_path": str(html_path),
                "pdf_path": str(pdf_path),
                "included_frames": len(rendered_frames),
                "drive_status": "pending",
                # Keep sent markers durable even if the process exits during
                # a slow Drive refresh; a restart must not resend the memo.
                "mail_status": str(previous_report.get("mail_status") or "not_configured"),
                "telegram_status": str(previous_report.get("telegram_status") or "not_configured"),
                "source_signature": source_signature,
                "generated_while_recording": not self._ready_for_delivery(detail),
            }
            _atomic_json(report_dir / "report.json", meta)
            delivery = (
                self.deliver(detail, meta, previous=previous_delivery)
                if self._ready_for_delivery(detail)
                else {
                    "drive_status": (
                        "uploaded" if previous_report.get("drive_status") == "uploaded"
                        else "waiting_for_end"
                    ),
                    "mail_status": (
                        "sent" if previous_report.get("mail_status") == "sent"
                        else "waiting_for_end"
                    ),
                    "telegram_status": (
                        "sent" if previous_report.get("telegram_status") == "sent"
                        else "waiting_for_end"
                    ),
                }
            )
            meta.update(delivery)
            checked_at = datetime.now().astimezone()
            meta["delivery_checked_at"] = checked_at.isoformat(timespec="seconds")
            meta["delivery_retry_at"] = (
                checked_at + timedelta(minutes=15)
            ).isoformat(timespec="seconds")
            _atomic_json(report_dir / "report.json", meta)
            return meta

    def retry_pending_deliveries(
        self, *, max_reports: int = 5, meeting_ids: set[str] | None = None
    ) -> int:
        """Retry incomplete delivery without regenerating PDFs or resending successes."""
        settings = _json(self.config_root / "delivery.json", {})
        if not isinstance(settings, dict):
            return 0
        now = datetime.now().astimezone()
        reports = sorted(
            self.reports_root.glob("*/report.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        retried = 0
        for path in reports:
            if meeting_ids is not None and path.parent.name not in meeting_ids:
                continue
            if retried >= max_reports:
                break
            meta = _json(path, {})
            generated = _date(str(meta.get("generated_at") or ""))
            if not generated or (now - generated).total_seconds() > self.delivery_retry_days * 86400:
                continue
            retry_at = _date(str(meta.get("delivery_retry_at") or ""))
            if retry_at and retry_at > now:
                continue
            wants_drive = bool(settings.get("drive_folder_id") or settings.get("drive_remote") or settings.get("drive_local_path"))
            wants_mail = bool(settings.get("email_to"))
            wants_telegram = bool(settings.get("telegram_account") and settings.get("telegram_config"))
            pending = (
                (wants_drive and meta.get("drive_status") != "uploaded")
                or (wants_mail and meta.get("mail_status") != "sent")
                or (wants_telegram and meta.get("telegram_status") != "sent")
            )
            if not pending:
                continue
            detail = self.report_detail(path.parent.name)
            if (not detail or not self._ready_for_delivery(detail)
                    or not Path(str(meta.get("pdf_path") or "")).is_file()):
                continue
            with self.lock:
                if _json(path, {}) != meta:
                    # Report generation may have completed while we prepared
                    # the retry. Re-check next scan instead of resending it.
                    continue
                meta.update(self.deliver(detail, meta, previous=meta))
                meta["delivery_checked_at"] = now.isoformat(timespec="seconds")
                meta["delivery_retry_at"] = (now + timedelta(minutes=15)).isoformat(timespec="seconds")
                _atomic_json(path, meta)
            retried += 1
        return retried

    def delivery_health(self) -> dict:
        """Expose recent delivery failures without revealing addresses or report data."""
        settings = _json(self.config_root / "delivery.json", {})
        if not isinstance(settings, dict) or not settings.get("email_to"):
            return {"mail_configured": False, "mail_pending": 0, "mail_auth_required": False}
        now = datetime.now().astimezone()
        pending = 0
        auth_required = False
        for path in self.reports_root.glob("*/report.json"):
            meta = _json(path, {})
            generated = _date(str(meta.get("generated_at") or ""))
            if not generated or (now - generated).total_seconds() > self.delivery_retry_days * 86400:
                continue
            if meta.get("mail_status") != "sent":
                pending += 1
                auth_required |= meta.get("mail_status") == "auth_required"
        return {
            "mail_configured": True,
            "mail_pending": pending,
            "mail_auth_required": auth_required,
        }

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
            "report_schema": 4,
            "product_name": MeetingArchive.product_name,
            "title": detail.get("title", ""),
            "segments": detail.get("transcript", []),
            "journal": detail.get("journal", []),
            "frames": [
                {key: item.get(key) for key in ("id", "captured_at", "speaker", "participant_labels", "path")}
                for item in detail.get("frames", [])
            ],
            "chat": detail.get("meeting_chat", []),
            "participants": detail.get("participants", []),
        }
        return hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def needs_report(self, meeting_id: str) -> bool:
        detail = self.report_detail(meeting_id)
        if not detail or not self._ready_for_delivery(detail):
            return False
        if not detail["transcript"] and not detail["journal"] and not detail["frames"]:
            return False
        report = detail.get("report") or {}
        return bool(report.get("generated_while_recording")) or (
            report.get("source_signature") != self.source_signature(detail)
        )

    def _ready_for_delivery(self, detail: dict) -> bool:
        # Long calls may be split into chunks. An active capture marker means
        # no chunk is final even if its exporter says "finished".
        if any(self.recordings_root.glob("*/.recording.json")):
            return False
        if detail.get("status") not in {"finished", "complete", "completed", "stopped", "idle"}:
            return False
        chain = self._continuous_chain(detail)
        if chain and detail.get("meeting_id") != chain[-1].get("meeting_id"):
            return False
        ended = _date(str(detail.get("ended_at") or ""))
        return bool(ended and (datetime.now().astimezone() - ended).total_seconds() >= 120)

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

    @staticmethod
    def _gws_call(*args: str, timeout: int = 60) -> dict | None:
        """Use the already-authorized Workspace CLI without exposing tokens."""
        gws = shutil.which("gws")
        if not gws:
            return None
        try:
            result = subprocess.run(
                [gws, *args], capture_output=True, text=True, timeout=timeout,
                env=os.environ | {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"},
            )
            if result.returncode != 0:
                return None
            payload = json.loads(result.stdout or "{}")
            return payload if isinstance(payload, dict) else None
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None

    @classmethod
    def _gws_items(cls, parent_id: str, name: str) -> list[dict]:
        escaped = name.replace("'", "\\'")
        params = json.dumps({
            "q": f"'{parent_id}' in parents and name = '{escaped}' and trashed = false",
            "fields": "files(id,name,mimeType,webViewLink)", "pageSize": 20,
        })
        payload = cls._gws_call("drive", "files", "list", "--params", params) or {}
        return [item for item in payload.get("files", []) if isinstance(item, dict)]

    @classmethod
    def _upload_drive_report_gws(
        cls, reports_folder_id: str, folder_name: str, source: Path
    ) -> tuple[str, dict[str, str]]:
        """Upload a private report tree with the user's existing Google token."""
        folder = next(
            (item for item in cls._gws_items(reports_folder_id, folder_name)
             if item.get("mimeType") == "application/vnd.google-apps.folder"), None
        )
        if not folder:
            folder = cls._gws_call(
                "drive", "files", "create", "--json", json.dumps({
                    "name": folder_name, "parents": [reports_folder_id],
                    "mimeType": "application/vnd.google-apps.folder",
                }), "--params", '{"fields":"id,name,mimeType,webViewLink"}',
            )
        folder_id = str((folder or {}).get("id") or "")
        if not folder_id:
            return "auth_required", {}
        files = [source / "index.html", source / "meeting-report.pdf"]
        files.extend(sorted((source / "assets").glob("*.jpg")))
        uploaded: dict[str, dict] = {}
        for path in files:
            if not path.is_file():
                return "failed", {}
            parent = folder_id
            if path.parent.name == "assets":
                assets = next(
                    (item for item in cls._gws_items(folder_id, "assets")
                     if item.get("mimeType") == "application/vnd.google-apps.folder"), None
                )
                if not assets:
                    assets = cls._gws_call(
                        "drive", "files", "create", "--json", json.dumps({
                            "name": "assets", "parents": [folder_id],
                            "mimeType": "application/vnd.google-apps.folder",
                        }), "--params", '{"fields":"id,name,mimeType,webViewLink"}',
                    )
                parent = str((assets or {}).get("id") or "")
                if not parent:
                    return "failed", {}
            existing = next(iter(cls._gws_items(parent, path.name)), None)
            params = json.dumps({"fields": "id,name,webViewLink"})
            if existing:
                params = json.dumps({"fileId": existing["id"], "fields": "id,name,webViewLink"})
                item = cls._gws_call(
                    "drive", "files", "update", "--params", params,
                    "--upload", str(path), timeout=180,
                )
            else:
                item = cls._gws_call(
                    "drive", "files", "create", "--json", json.dumps({
                        "name": path.name, "parents": [parent],
                    }), "--params", params, "--upload", str(path), timeout=180,
                )
            if not item or not item.get("id"):
                return "failed", {}
            uploaded[path.name] = item
        html_file = uploaded["index.html"]
        pdf_file = uploaded["meeting-report.pdf"]
        links = {
            "drive_folder_url": str(folder.get("webViewLink") or f"https://drive.google.com/drive/folders/{folder_id}"),
            "drive_html_url": str(html_file.get("webViewLink") or f"https://drive.google.com/file/d/{html_file['id']}/view"),
            "drive_pdf_url": str(pdf_file.get("webViewLink") or f"https://drive.google.com/file/d/{pdf_file['id']}/view"),
        }
        return "uploaded", links

    def deliver(self, detail: dict, report: dict, *, previous: dict | None = None) -> dict:
        settings = _json(self.config_root / "delivery.json", {})
        previous = previous or {}
        local_drive_setting = str(settings.get("drive_local_path") or "").strip()
        local_drive = Path(local_drive_setting).expanduser() if local_drive_setting else None
        remote = str(settings.get("drive_remote") or "").strip()
        meeting_started = _date(detail.get("started_at")) or datetime.now().astimezone()
        stamp = meeting_started.strftime("%Y-%m-%d")
        time_stamp = meeting_started.strftime("%H-%M")
        title = re.sub(r"[/\\:*?\"<>|]+", "-", detail["title"]).strip()[:80]
        folder_name = f"{stamp} {time_stamp} {title} [{detail['meeting_id'][-8:]}]"
        source = self.reports_root / detail["meeting_id"]
        drive_status = str(previous.get("drive_status") or "not_configured")
        drive_folder = str(previous.get("drive_folder") or "")
        drive_links: dict[str, str] = {
            key: str(previous[key]) for key in (
                "drive_folder_url", "drive_html_url", "drive_pdf_url"
            ) if previous.get(key)
        }

        gog = shutil.which("gog")
        gws = shutil.which("gws")
        recipient = str(settings.get("email_to") or "").strip()
        google_account = str(settings.get("google_account") or recipient).strip()
        reports_folder_id = str(settings.get("drive_folder_id") or "").strip()

        # The API upload is authoritative: delivery proceeds only after Google
        # returns private webViewLink values for both report files.
        if drive_status == "uploaded":
            if not drive_links and gws and reports_folder_id:
                refreshed, links = self._upload_drive_report_gws(
                    reports_folder_id, folder_name, source
                )
                if refreshed == "uploaded":
                    drive_links = links
                    drive_folder = links.get("drive_folder_url", drive_folder)
        elif gog and google_account and reports_folder_id:
            drive_status, drive_links = self._upload_drive_report(
                gog, google_account, reports_folder_id, folder_name, source
            )
            drive_folder = drive_links.get("drive_folder_url", "")
            if drive_status != "uploaded" and gws:
                drive_status, drive_links = self._upload_drive_report_gws(
                    reports_folder_id, folder_name, source
                )
                drive_folder = drive_links.get("drive_folder_url", "")
        elif gws and google_account and reports_folder_id:
            drive_status, drive_links = self._upload_drive_report_gws(
                reports_folder_id, folder_name, source
            )
            drive_folder = drive_links.get("drive_folder_url", "")
        elif local_drive is not None and local_drive.parent.exists():
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

        mail_status = str(previous.get("mail_status") or "not_configured")
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
        if mail_status != "sent" and (gog or gws) and recipient:
            subject = f"{self.product_name}: {detail['title']} — {stamp}"
            body = (
                f"Отчёт по встрече «{detail['title']}» от {stamp}.\n\n"
                f"Сформирован {self.product_name}.\n"
                + ("HTML и PDF сохранены в Google Drive. " if drive_status == "uploaded"
                   else "Google Drive пока недоступен; PDF сохранён локально. ")
                + "PDF приложен к письму."
                + links_text
            )
            if gog:
                try:
                    result = subprocess.run(
                        [gog, "--account", recipient, "--no-input", "--json", "gmail",
                         "send", "--to", recipient, "--subject", subject,
                         "--body", body, "--attach", report["pdf_path"]],
                        capture_output=True, text=True, timeout=180,
                    )
                    mail_status = (
                        "sent" if result.returncode == 0 else
                        "auth_required" if result.returncode == 4 else "failed"
                    )
                except (OSError, subprocess.TimeoutExpired):
                    mail_status = "failed"
            # An arbitrary gog failure may have happened after Gmail accepted
            # the message. Fall back only for a confirmed auth failure.
            if gws and (not gog or mail_status in {"not_configured", "auth_required"}):
                sent = self._gws_call(
                    "gmail", "+send", "--to", recipient, "--subject", subject,
                    "--body", body, "--attach", report["pdf_path"], timeout=180,
                )
                mail_status = "sent" if sent and sent.get("id") else "failed"

        telegram_status = str(previous.get("telegram_status") or "not_configured")
        telegram_message_id = previous.get("telegram_message_id")
        telegram_config = Path(
            str(settings.get("telegram_config") or "")
        ).expanduser()
        telegram_account = str(settings.get("telegram_account") or "").strip()
        telegram_target = str(settings.get("telegram_target") or "me").strip()
        telegram_helper = Path(__file__).with_name("telegram_delivery.py")
        if (telegram_status != "sent" and telegram_account
                and telegram_config.is_file() and drive_status == "uploaded"):
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

    @staticmethod
    def _brief_line(value: object, limit: int = 220) -> str:
        """Keep the executive page readable without manufacturing a summary."""
        line = re.sub(r"\s+", " ", str(value or "")).strip()
        line = re.split(r"\b(?:Источник|Основание|Provenance)\s*:", line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        line = re.sub(
            r"^(?:FACT|DECISION|COMMITMENT|ASK|RISK|ФАКТ|РЕШЕНИЕ)\s*[—:–-]\s*",
            "", line, flags=re.IGNORECASE,
        )
        if len(line) <= limit:
            return line
        sentence_end = [match.end() for match in re.finditer(r"[.!?](?=\s|$)", line[:limit])]
        if sentence_end and sentence_end[-1] >= 70:
            return line[:sentence_end[-1]]
        return line[:limit].rsplit(" ", 1)[0].rstrip(".,;: ") + "…"

    @staticmethod
    def _followup_sentence(value: object) -> str:
        """Require an explicit next action, not merely a future-sounding fact."""
        text = str(value or "").replace("\\n", " ")
        text = re.split(r"\b(?:Источник|Основание|Provenance)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
        action = re.compile(
            r"\b(?:(?:пришл|отправ|подготов|покаж|созвон|назнач|запланир|запрошен|"
            r"договорил|согласовал|предостав|передад)\w*|"
            r"will\s+(?:send|prepare|share|schedule|show|provide)|"
            r"agreed\s+to|follow[ -]?up)\b",
            re.IGNORECASE,
        )
        for sentence in re.split(r"(?<=[.!?;])\s+", text):
            if re.search(r"\bне\s+(?:договорил|согласовал|подготов|отправ|предостав)\w*", sentence, re.IGNORECASE):
                continue
            if action.search(sentence):
                line = sentence.strip().lstrip("; ")
                return line[:1].upper() + line[1:]
        return ""

    @staticmethod
    def _known_speaker(value: object) -> bool:
        name = str(value or "").strip()
        return bool(name) and not (
            name.casefold() in {"я", "me", "you", "собеседник", "собеседники", "participant", "участник"}
            or re.fullmatch(r"(?:спикер|speaker|remote|участник)[ -]?\d+", name, re.IGNORECASE)
        )

    @classmethod
    def _front_participants(cls, detail: dict) -> tuple[list[dict], str]:
        """Only observed names and explicitly supplied contacts are shown."""
        people: dict[str, dict] = {}
        speech_by_label: Counter[str] = Counter()

        def person(name: str) -> dict:
            key = name.strip().casefold()
            return people.setdefault(key, {"name": name.strip(), "speech": 0, "contacts": [], "seen": set(), "about": None})

        for item in detail.get("participants", []):
            name = str(item.get("name") or "").strip()
            if not cls._known_speaker(name):
                continue
            entry = person(name)
            entry["seen"].add("контекст встречи")
            for identity in item.get("identities", []):
                value = str(identity.get("value") or "").strip()
                if value and value not in entry["contacts"]:
                    entry["contacts"].append(value)
            for fact in item.get("public_facts", []):
                source_url = str(fact.get("url") or "").strip()
                fact_text = cls._brief_line(fact.get("text"), 140)
                if fact_text and source_url.startswith(("https://", "http://")):
                    entry["about"] = {"text": fact_text, "url": source_url}
                    break

        for item in detail.get("transcript", []):
            name = str(item.get("speaker") or "").strip()
            if name:
                speech_by_label[name.casefold()] += len(str(item.get("text") or ""))
            if cls._known_speaker(name):
                entry = person(name)
                entry["speech"] += len(str(item.get("text") or ""))
                entry["seen"].add("стенограмма")

        meet_label_counts: Counter[str] = Counter()
        for item in detail.get("frames", []):
            meet_label_counts.update({str(label).strip() for label in item.get("participant_labels", []) if label})
        for item in detail.get("frames", []):
            name = str(item.get("speaker") or "").strip()
            if cls._known_speaker(name):
                person(name)["seen"].add("активная плитка Meet" if item.get("speaker_confidence") == "meet-active-tile" else "кадр встречи")
            for label in item.get("participant_labels", []):
                label = str(label or "").strip()
                if cls._known_speaker(label) and meet_label_counts[label] >= 2:
                    person(label)["seen"].add("аккаунт Meet")

        for item in detail.get("meeting_chat", []):
            name = str(item.get("sender") or "").strip()
            if not cls._known_speaker(name):
                continue
            entry = person(name)
            entry["seen"].add("чат")
            message = str(item.get("text") or "")
            for match in re.findall(r"https?://t\.me/[A-Za-z0-9_]{5,}|(?:telegram|телеграм)\s*[:—-]\s*@[A-Za-z0-9_]{5,}", message, re.IGNORECASE):
                if match not in entry["contacts"]:
                    entry["contacts"].append(match)

        spoken_text = " ".join(str(item.get("text") or "") for item in detail.get("transcript", []))
        for entry in people.values():
            first_name = entry["name"].split()[0]
            if (len(first_name) >= 4 and first_name[:1].isupper()
                    and re.search(rf"(?<!\w){re.escape(first_name)}\w*", spoken_text, re.IGNORECASE)):
                entry["seen"].add("имя звучит в разговоре")

        ranked = sorted(people.values(), key=lambda item: (-item["speech"], item["name"].casefold()))
        spoken = [item for item in ranked if item["speech"] > 0]
        main = (
            spoken[0]["name"]
            if spoken and spoken[0]["speech"] >= max(speech_by_label.values(), default=0)
            else "Не определён по записи"
        )
        return ranked, main

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
        participants, main_speaker = self._front_participants(detail)
        active_tiles = Counter(
            str(item.get("speaker") or "").strip()
            for item in detail.get("frames", [])
            if item.get("speaker_confidence") == "meet-active-tile" and item.get("speaker")
        )
        top_tile, top_tile_count = active_tiles.most_common(1)[0] if active_tiles else ("", 0)
        active_tile_note = (
            f'<p class="uncertain">Чаще всего подсвечен в кадрах Meet: <strong>{esc(top_tile)}</strong> '
            f'({top_tile_count} из {sum(active_tiles.values())} кадров с видимой активной плиткой). '
            'Это не доказательство, что он говорил больше всех.</p>'
            if top_tile else ""
        )
        sources = Counter(str(item.get("source") or "") for item in detail.get("transcript", []))
        audio_identity_note = (
            f'<p class="uncertain">В стенограмме {sources["system"]} фрагментов удалённого звука и '
            f'{sources["microphone"]} с локального микрофона. Удалённый канал не разделён '
            'надёжно между аккаунтами Meet.</p>'
            if main_speaker == "Не определён по записи" and sources["system"] else ""
        )
        roster = "".join(
            f'<li><strong>{esc(person["name"])}</strong> · {esc(", ".join(sorted(person["seen"]))) or "участник"}'
            f'{" · " + esc(", ".join(person["contacts"])) if person["contacts"] else ""}'
            f'{"<br>Публично: " + esc(person["about"]["text"]) + " (<a href=\"" + esc(person["about"]["url"]) + "\">источник</a>)" if person["about"] else ""}</li>'
            for person in participants
        )
        if not roster and detail.get("transcript"):
            microphone_seen = any(item.get("source") == "microphone" for item in detail["transcript"])
            roster = (
                '<li>Вы — локальный микрофон.</li><li>Другие голоса — имена не подтверждены записью или чатом.</li>'
                if microphone_seen else '<li>Голоса есть, но имена участников не подтверждены записью или чатом.</li>'
            )
        brief = []
        for category in ("DECISION", "FACT", "COMMITMENT"):
            for item in groups.get(category, [])[-2:]:
                if category == "FACT" and re.search(r"(?:На экране|Источник:\s*OCR)", str(item.get("text") or ""), re.IGNORECASE):
                    continue
                line = self._brief_line(item.get("text"), 240)
                if line and line not in brief:
                    brief.append(line)
        summary_items = "".join(f"<li>{esc(line)}</li>" for line in brief[:3])
        followups = []
        for item in [*groups.get("COMMITMENT", []), *groups.get("FACT", [])]:
            line = self._brief_line(self._followup_sentence(item.get("text")), 220)
            if line and line not in followups:
                followups.append(line)
        followup_items = "".join(f"<li>{esc(line)}</li>" for line in followups[:5])
        topics = []
        if (not self._is_generic_title(detail["title"])
                and not re.match(r"^(?:Meet|Zoom)\s*[-—]\s*[a-z]{3}-[a-z]{4}-[a-z]{3}$", detail["title"], re.IGNORECASE)):
            topics.append(self._brief_line(detail["title"], 120))
        for category in ("QUESTION", "DECISION", "FACT"):
            for item in groups.get(category, [])[:2]:
                if category == "FACT" and re.search(r"(?:На экране|Источник:\s*OCR)", str(item.get("text") or ""), re.IGNORECASE):
                    continue
                line = self._brief_line(item.get("text"), 150)
                if line and line not in topics and not re.search(r"https?://(?:meet\.google\.com|zoom\.us)", line, re.IGNORECASE):
                    topics.append(line)
        topic_items = "".join(f"<li>{esc(line)}</li>" for line in topics[:4])

        toc = [
            '<li><a href="#overview">Участники и суть</a></li>',
            '<li><a href="#followups">Следующие шаги</a></li>',
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
.opening h2{{margin:6mm 0 2mm;font-size:14pt}} .opening ul{{margin:2mm 0 3mm;padding-left:6mm}}
.opening .roster{{columns:2;column-gap:6mm}} .opening .roster li{{break-inside:avoid}}
.opening .main-speaker{{font-size:9pt;color:#56615d;margin:0 0 2mm}} .opening .main-speaker strong{{color:#174c3e}}
.opening .uncertain{{color:#6c7773;font-size:9pt;margin:1mm 0 3mm}}
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
<section id="overview" class="opening"><h2>Участники</h2>
<p class="main-speaker">Основной спикер по объёму распознанной речи: <strong>{esc(main_speaker)}</strong></p>
<ul class="roster">{roster or '<li>Имена участников не подтверждены записью или чатом.</li>'}</ul>
{active_tile_note}
{audio_identity_note}
<p class="uncertain">Имена и контакты показаны только там, где они есть в источниках; роль спикера может требовать ручной проверки.</p></section>
<section id="followups" class="opening"><h2>Следующие шаги</h2><ul>{followup_items or '<li>Автоматически выделенных следующих шагов нет; проверьте стенограмму.</li>'}</ul>
{'' if not followup_items else '<p class="uncertain">Если срок или ответственный не указаны в пункте, они не были подтверждены автоматически.</p>'}</section>
<section id="summary" class="opening"><h2>Суть звонка</h2><div class="summary"><ul>{summary_items or '<li>Проверенное краткое резюме пока не сформировано; см. заметки и стенограмму ниже.</li>'}</ul></div>
<h2>Повестка и темы</h2><ul>{topic_items or '<li>Повестка не зафиксирована; ключевые темы смотрите в резюме.</li>'}</ul></section>
<nav class="toc"><h2>Оглавление</h2><ol>{''.join(toc)}</ol></nav>
{f'<section id="participants"><h2>Справка о собеседниках</h2>{participants_html}</section>' if participants_html else ''}
<section id="notes"><h2>Заметки и сигналы</h2>{''.join(notes_sections) or '<p class="empty">Заметок пока нет.</p>'}</section>
{f'<section id="chat"><h2>Чат встречи</h2>{chat_html}</section>' if chat_html else ''}
{f'<section id="frames" class="page-break"><h2>Ключевые кадры</h2><div class="frames">{frames_html}</div></section>' if frames_html else ''}
{f'<section id="transcript" class="page-break"><h2>Стенограмма</h2>{transcript_html}</section>' if transcript_html else ''}
</body></html>'''
