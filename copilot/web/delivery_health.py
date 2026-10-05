"""Local, durable delivery health and transition-only notices. No network I/O."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _date(value: object) -> datetime | None:
    try:
        date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return date.astimezone()  # Also accept old, naive local timestamps.
    except (ValueError, TypeError):
        return None


def drive_links_ready(report: dict) -> bool:
    for key, pattern in (
        ("drive_folder_url", r"/drive/folders/[A-Za-z0-9_-]+/?"),
        ("drive_html_url", r"/file/d/[A-Za-z0-9_-]+/view/?"),
        ("drive_pdf_url", r"/file/d/[A-Za-z0-9_-]+/view/?"),
    ):
        try:
            url = urlparse(str(report.get(key) or ""))
            if (url.scheme != "https" or url.netloc != "drive.google.com"
                    or not re.fullmatch(pattern, url.path)):
                return False
        except ValueError:
            return False
    return True


class DeliveryHealth:
    """Keep notices across reload/restart without exposing report contents."""

    channels = {"drive": "drive_status", "gmail": "mail_status", "telegram": "telegram_status"}

    def __init__(self, reports_root: Path, state_file: Path, retry_days: int = 3):
        self.reports_root = reports_root
        self.state_file = state_file
        self.retry_days = retry_days
        self.lock = threading.RLock()

    @staticmethod
    def configured(settings: dict) -> dict[str, bool]:
        return {
            "drive": bool(settings.get("drive_folder_id") or settings.get("drive_remote")
                          or settings.get("drive_local_path")),
            "gmail": bool(settings.get("email_to")),
            "telegram": bool(settings.get("telegram_account") and settings.get("telegram_config")),
        }

    def _collect(self, settings: dict, now: datetime) -> tuple[dict, dict]:
        configured = self.configured(settings)
        channels = {key: {"configured": enabled, "state": "idle" if enabled else "not_configured",
                          "sent": 0, "pending": 0, "waiting": 0, "failed": 0,
                          "action_required": 0, "issues": []}
                    for key, enabled in configured.items()}
        observations = {}
        considered = 0
        with self.lock:
            tracked_meetings = {item.get("meeting_id") for item in _read(self.state_file).get("issues", {}).values()}
        for path in sorted(self.reports_root.glob("*/report.json")):
            report = _read(path)
            generated = _date(report.get("generated_at"))
            expired = bool(generated and now - generated > timedelta(days=self.retry_days))
            # Completed historical reports do not fill the recent summary. An
            # unresolved delivery must not silently disappear when retry ends.
            if expired and path.parent.name not in tracked_meetings:
                continue
            considered += 1
            for channel, field in self.channels.items():
                if not configured[channel]:
                    continue
                raw = report.get(field)
                if expired and raw in {None, "not_configured"}:
                    continue
                state, reason = "pending", "pending"
                if not generated:
                    state, reason = "failed", "metadata_invalid"
                elif raw == ("uploaded" if channel == "drive" else "sent"):
                    state, reason = "sent", "sent"
                    if channel == "drive" and settings.get("drive_folder_id") and not drive_links_ready(report):
                        state, reason = "failed", "links_missing"
                elif raw == "waiting_for_end":
                    state, reason = "waiting", "waiting_for_end"
                elif raw == "auth_required":
                    state, reason = "action_required", "auth_required"
                elif raw not in {None, "not_configured", "pending"}:
                    state, reason = "failed", "delivery_failed"
                elif now - generated > timedelta(minutes=15):
                    state, reason = "failed", "retry_overdue"
                if expired and state not in {"sent", "waiting"}:
                    state, reason = "action_required", "retry_expired"
                key = f"{path.parent.name}:{channel}"
                observations[key] = {"meeting_id": path.parent.name, "channel": channel,
                                     "state": state, "reason": reason}
                item = channels[channel]
                item[state] += 1
                if state in {"failed", "action_required"}:
                    item["issues"].append({"meeting_id": path.parent.name, "reason": reason})
        for item in channels.values():
            if not item["configured"]:
                continue
            item["state"] = next((key for key in ("action_required", "failed", "pending", "waiting", "sent")
                                  if item[key]), "idle")
        states = {item["state"] for item in channels.values()}
        overall = next((key for key in ("action_required", "failed", "pending", "waiting", "sent", "idle")
                        if key in states), "not_configured")
        return {"channels": channels, "state": overall, "reports": considered,
                "issue_count": sum(item["failed"] + item["action_required"] for item in channels.values())}, observations

    def snapshot(self, settings: dict, *, now: datetime | None = None) -> dict:
        summary, _ = self._collect(settings, now or datetime.now().astimezone())
        with self.lock:
            stored = _read(self.state_file)
        ack = int(stored.get("acknowledged_through") or 0)
        summary.update({"checked_at": stored.get("checked_at"),
                        "notifications": [item for item in stored.get("events", []) if item["id"] > ack],
                        "acknowledged_through": ack})
        # Backward compatibility for older installed web clients.
        mail = summary["channels"]["gmail"]
        summary.update({"mail_configured": mail["configured"],
                        "mail_pending": mail["pending"] + mail["failed"] + mail["action_required"],
                        "mail_auth_required": any(i["reason"] == "auth_required" for i in mail["issues"])})
        return summary

    def refresh(self, settings: dict, *, now: datetime | None = None) -> dict:
        now = now or datetime.now().astimezone()
        _, observations = self._collect(settings, now)
        with self.lock:
            stored = _read(self.state_file)
            previous = stored.get("issues", {})
            current = {key: item for key, item in observations.items()
                       if item["state"] in {"failed", "action_required"}}
            events = list(stored.get("events", []))
            sequence = int(stored.get("sequence") or 0)
            changes = [(item, item["state"]) for key, item in current.items()
                       if previous.get(key) != item]
            changes += [(observations[key], "recovered") for key in previous
                        if key in observations and observations[key]["state"] == "sent"]
            for item, kind in changes:
                sequence += 1
                events.append({**item, "kind": kind, "id": sequence,
                               "at": now.isoformat(timespec="seconds")})
            # A retry returning to pending is not recovery. Retain the failure
            # episode until success so the later restoration can be announced.
            tracked = {key: item for key, item in previous.items()
                       if key in observations and observations[key]["state"] in {"pending", "waiting"}}
            tracked.update(current)
            stored.update({"version": 1, "issues": tracked, "sequence": sequence,
                           "events": events[-50:], "checked_at": now.isoformat(timespec="seconds")})
            self._save(stored)
        return self.snapshot(settings, now=now)

    def acknowledge(self, through: int) -> None:
        if isinstance(through, bool) or not isinstance(through, int) or through < 0:
            raise ValueError("Invalid delivery notification ID")
        with self.lock:
            stored = _read(self.state_file)
            stored["acknowledged_through"] = max(int(stored.get("acknowledged_through") or 0),
                                                  min(through, int(stored.get("sequence") or 0)))
            self._save(stored)

    def _save(self, value: dict) -> None:
        self.state_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(self.state_file)
