"""Private, meeting-scoped preparation and live checklist state."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from calendar_meetings import CalendarMeetings
from repo_preparations import RepositoryPreparations


KINDS = {"question", "risk", "objection"}
STATUSES = {"open", "resolved", "clarify"}
UPDATE_RE = re.compile(r"(?m)^PLAN_UPDATE\s*[:—-]\s*(\{[^\n]*\})\s*$")


def _normal(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


def _safe_link(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username


class CallPlans:
    def __init__(
        self, config_path: Path, state_path: Path,
        repositories_path: Path | None = None,
        calendar: CalendarMeetings | None = None,
    ) -> None:
        self.config_path = config_path
        self.state_path = state_path
        self.lock = threading.RLock()
        self.repositories = RepositoryPreparations(repositories_path) if repositories_path else None
        self.calendar = calendar

    def _plans(self, transcript: dict) -> list[dict]:
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        configured = raw.get("plans", []) if isinstance(raw, dict) and raw.get("version") == 1 else []
        if not isinstance(configured, list):
            configured = []
        plans = []
        used_sources = set()
        for original in configured:
            if not isinstance(original, dict):
                continue
            plan = dict(original)
            source = plan.get("source_file")
            if isinstance(source, str) and self.repositories:
                prepared = self.repositories.from_active_file(source)
                if prepared:
                    used_sources.add(prepared["source_path"])
                    plan["title"] = prepared["title"]
                    plan["intro"] = " ".join(part for part in (
                        str(plan.get("intro") or ""), prepared["intro"]
                    ) if part)
                    plan["source_label"] = prepared["source_label"]
                    plan["meeting_link"] = prepared.get("meeting_link", "")
                    explicit_items = plan.get("items", [])
                    plan["items"] = prepared["items"] + (
                        [item for item in explicit_items if isinstance(item, dict)]
                        if isinstance(explicit_items, list) else []
                    )
                    links = plan.get("links", [])
                    merged = (links if isinstance(links, list) else []) + prepared["links"]
                    plan["links"] = list({link.get("url"): link for link in merged if isinstance(link, dict) and isinstance(link.get("url"), str)}.values())
            plans.append(plan)
        if self.repositories and transcript.get("started_at"):
            try:
                local_date = datetime.fromisoformat(
                    str(transcript["started_at"]).replace("Z", "+00:00")
                ).astimezone().date().isoformat()
            except ValueError:
                local_date = ""
            if local_date:
                plans.extend(
                    found for found in self.repositories.for_date(local_date)
                    if found["source_path"] not in used_sources
                )
        return plans

    def _state(self) -> dict:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": 1, "meetings": {}}
        meetings = raw.get("meetings") if isinstance(raw, dict) else None
        return {"version": 1, "meetings": meetings if isinstance(meetings, dict) else {}}

    def _save(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(self.state_path)

    @staticmethod
    def _valid(plan: dict) -> bool:
        if not isinstance(plan.get("id"), str) or not plan["id"]:
            return False
        if plan.get("starts_at"):
            try:
                datetime.fromisoformat(str(plan["starts_at"]))
            except ValueError:
                return False
        else:
            try:
                datetime.fromisoformat(str(plan["call_date"]))
            except (KeyError, ValueError):
                return False
        items = plan.get("items")
        if not isinstance(items, list) or len(items) > 60:
            return False
        ids = [item.get("id") for item in items if isinstance(item, dict)]
        if len(ids) != len(items) or not all(isinstance(item_id, str) for item_id in ids):
            return False
        return len(set(ids)) == len(ids) and all(
            isinstance(item.get("id"), str)
            and re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", item["id"])
            and item.get("kind") in KINDS
            and isinstance(item.get("text"), str)
            and 0 < len(item["text"]) <= 500
            for item in items
        )

    @staticmethod
    def _matches(plan: dict, transcript: dict) -> bool:
        try:
            started = datetime.fromisoformat(str(transcript.get("started_at") or "").replace("Z", "+00:00"))
            if started.tzinfo is None:
                return False
            if plan.get("starts_at"):
                expected = datetime.fromisoformat(str(plan["starts_at"]))
                if expected.tzinfo is None or abs((started - expected).total_seconds()) > 2 * 3600:
                    return False
            elif started.astimezone().date().isoformat() != plan.get("call_date"):
                return False
        except (ValueError, TypeError, KeyError):
            return False
        meeting_link = str(transcript.get("meeting_link") or "").rstrip("/")
        planned_link = str(plan.get("meeting_link") or "").rstrip("/")
        if meeting_link and planned_link and meeting_link == planned_link:
            return True
        names = _normal(" ".join(str(name) for name in transcript.get("remote_attendees", [])))
        title = _normal(str(transcript.get("meeting") or ""))
        attendee_hit = any(_normal(str(alias)) in names for alias in plan.get("attendee_aliases", []) if _normal(str(alias)))
        title_hit = any(_normal(str(alias)) in title for alias in plan.get("title_aliases", []) if _normal(str(alias)))
        return attendee_hit or title_hit

    @staticmethod
    def _generic_capture(transcript: dict) -> bool:
        if transcript.get("remote_attendees") or transcript.get("meeting_link"):
            return False
        title = _normal(str(transcript.get("meeting") or ""))
        return not title or any(generic in title for generic in ("chrome helper", "meeting", "telemost", "zoom"))

    @staticmethod
    def _time_fallback(plan: dict, transcript: dict) -> bool:
        """Show a tentative plan for a generic app title near one scheduled call."""
        try:
            expected = datetime.fromisoformat(str(plan["starts_at"]))
            started = datetime.fromisoformat(str(transcript.get("started_at") or "").replace("Z", "+00:00"))
            if expected.tzinfo is None or started.tzinfo is None:
                return False
            if abs((started - expected).total_seconds()) > 10 * 60:
                return False
        except (ValueError, TypeError, KeyError):
            return False
        return CallPlans._generic_capture(transcript)

    def _calendar_candidates(self, plans: list[dict], transcript: dict) -> list[dict]:
        if not self.calendar or not self._generic_capture(transcript):
            return []
        try:
            started = datetime.fromisoformat(str(transcript["started_at"]).replace("Z", "+00:00"))
            if started.tzinfo is None:
                return []
        except (KeyError, TypeError, ValueError):
            return []
        matches = []
        for event in self.calendar.for_day(started.astimezone().date()):
            try:
                event_start = datetime.fromisoformat(event["start"])
                event_end = datetime.fromisoformat(event["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if not event_start - timedelta(minutes=15) <= started <= event_end + timedelta(minutes=20):
                continue
            event_title = _normal(str(event.get("title") or ""))
            event_link = str(event.get("link") or "").rstrip("/")
            for plan in plans:
                if plan in matches:
                    continue
                scheduled = plan.get("starts_at") or plan.get("call_date")
                try:
                    scheduled_at = datetime.fromisoformat(str(scheduled))
                    scheduled_day = scheduled_at.astimezone().date() if scheduled_at.tzinfo else scheduled_at.date()
                    if scheduled_day != started.astimezone().date():
                        continue
                except (TypeError, ValueError):
                    continue
                aliases = [
                    alias for field in ("title_aliases", "attendee_aliases")
                    for alias in (plan.get(field) if isinstance(plan.get(field), list) else [])
                ]
                name_hit = any(
                    len(alias_normal := _normal(str(alias))) >= 4 and alias_normal in event_title
                    for alias in aliases
                )
                planned_link = str(plan.get("meeting_link") or "").rstrip("/")
                if name_hit or (event_link and planned_link and event_link == planned_link):
                    matches.append(plan)
        return matches

    def _plan_for(self, transcript: dict, state: dict) -> dict | None:
        meeting_id = str(transcript.get("meeting_id") or "")
        if not meeting_id:
            return None
        bound_id = state["meetings"].get(meeting_id, {}).get("plan_id")
        plans = [plan for plan in self._plans(transcript) if self._valid(plan)]
        if bound_id:
            return next((plan for plan in plans if plan["id"] == bound_id), None)
        confirmed = next((plan for plan in plans if self._matches(plan, transcript)), None)
        if confirmed:
            return confirmed
        calendar_matches = self._calendar_candidates(plans, transcript)
        if len(calendar_matches) == 1:
            return calendar_matches[0]
        tentative = [plan for plan in plans if self._time_fallback(plan, transcript)]
        return tentative[0] if len(tentative) == 1 else None

    def snapshot(self, transcript: dict) -> dict | None:
        meeting_id = str(transcript.get("meeting_id") or "")
        if not meeting_id:
            return None
        with self.lock:
            state = self._state()
            plan = self._plan_for(transcript, state)
            if plan is None:
                return None
            if meeting_id not in state["meetings"]:
                calendar_matches = self._calendar_candidates([plan], transcript)
                state["meetings"][meeting_id] = {
                    "plan_id": plan["id"], "items": {},
                    "match": "confirmed" if self._matches(plan, transcript)
                    else "calendar" if calendar_matches else "time-only",
                }
                self._save(state)
            meeting = state["meetings"][meeting_id]
            items = []
            for source in plan["items"]:
                item_state = meeting.get("items", {}).get(source["id"], {})
                items.append({
                    "id": source["id"], "kind": source["kind"], "text": source["text"],
                    "status": item_state.get("status", "open"),
                    "evidence": item_state.get("evidence", ""),
                    "updated_at": item_state.get("updated_at", ""),
                    "source": item_state.get("source", ""),
                })
            links = [
                {"label": str(link.get("label") or "Материал")[:100], "url": link["url"]}
                for link in plan.get("links", []) if isinstance(link, dict)
                and isinstance(link.get("url"), str) and _safe_link(link["url"])
            ][:30]
            by_kind = {
                kind: {
                    "resolved": sum(item["kind"] == kind and item["status"] == "resolved" for item in items),
                    "clarify": sum(item["kind"] == kind and item["status"] == "clarify" for item in items),
                    "total": sum(item["kind"] == kind for item in items),
                }
                for kind in ("question", "risk", "objection")
            }
            return {
                "id": plan["id"], "meeting_id": meeting_id,
                "match": meeting.get("match", "confirmed"),
                "title": str(plan.get("title") or "Подготовка")[:200],
                "intro": str(plan.get("intro") or "")[:1500],
                "source_label": str(plan.get("source_label") or "")[:200],
                "links": links, "items": items,
                "score": {
                    "resolved": sum(item["status"] == "resolved" for item in items),
                    "clarify": sum(item["status"] == "clarify" for item in items),
                    "total": len(items),
                    "percent": round(100 * sum(item["status"] == "resolved" for item in items) / len(items)) if items else 0,
                    "by_kind": by_kind,
                },
            }

    def source_context(self, transcript: dict) -> str:
        if not self.repositories:
            return ""
        with self.lock:
            plan = self._plan_for(transcript, self._state())
            source = plan.get("source_path") if plan else None
            if not source and plan:
                source = plan.get("source_file")
            return self.repositories.context_from_active_file(source) if isinstance(source, str) else ""

    def manual_status(self, transcript: dict, item_id: str, status: str) -> dict:
        if status not in STATUSES:
            raise ValueError("Некорректный статус")
        with self.lock:
            plan = self.snapshot(transcript)
            if plan is None or item_id not in {item["id"] for item in plan["items"]}:
                raise ValueError("Пункт не найден в текущей встрече")
            state = self._state()
            state["meetings"][plan["meeting_id"]]["items"][item_id] = {
                "status": status, "evidence": "",
                "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "source": "manual",
            }
            self._save(state)
            return self.snapshot(transcript)

    def apply_analysis(self, transcript: dict, answer: str) -> int:
        """Accept only explicitly quoted evidence from this meeting's captured speech."""
        with self.lock:
            plan = self.snapshot(transcript)
            if plan is None:
                return 0
            valid_items = {item["id"]: item for item in plan["items"]}
            speech = _normal(" ".join(
                str(segment.get("text") or "") for segment in transcript.get("segments", [])
                if not segment.get("provisional")
            ))
            state = self._state()
            meeting_items = state["meetings"][plan["meeting_id"]]["items"]
            updated = 0
            for raw in UPDATE_RE.findall(answer):
                try:
                    update = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(update, dict):
                    continue
                item_id = str(update.get("id") or "")
                status = str(update.get("status") or "")
                evidence = str(update.get("evidence") or "").strip()
                quote = _normal(evidence)
                if (
                    item_id not in valid_items or status not in {"resolved", "clarify"}
                    or len(quote) < 12 or quote not in speech
                    or meeting_items.get(item_id, {}).get("source") == "manual"
                ):
                    continue
                meeting_items[item_id] = {
                    "status": status, "evidence": evidence[:400],
                    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "source": "analysis",
                }
                updated += 1
            if updated:
                self._save(state)
            return updated
