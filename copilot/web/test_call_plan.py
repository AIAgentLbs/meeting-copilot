import json
import tempfile
import unittest
from pathlib import Path

from call_plan import CallPlans
from repo_preparations import RepositoryPreparations


class CallPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "preparations.json"
        self.state = self.root / "call-plans-state.json"
        self.config.write_text(json.dumps({"version": 1, "plans": [{
            "id": "sample-2026-09-29", "starts_at": "2026-09-29T10:00:00+02:00",
            "attendee_aliases": ["Alex Sample"], "title_aliases": ["documents demo"],
            "title": "Sample preparation", "intro": "Prepare the demo.",
            "links": [{"label": "Brief", "url": "https://example.com/brief"},
                      {"label": "Unsafe", "url": "file:///private/brief"}],
            "items": [{"id": "q1", "kind": "question", "text": "What format do you use?"},
                      {"id": "r1", "kind": "risk", "text": "Is access approved?"}],
        }]}), encoding="utf-8")
        self.plan = CallPlans(self.config, self.state)
        self.meeting = {
            "meeting_id": "meeting-a", "meeting": "Generic video call",
            "started_at": "2026-09-29T08:04:00Z",
            "remote_attendees": ["Alex Sample"],
            "segments": [{"text": "We use PDF scans for our current document intake.", "provisional": False}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_calendar_match_and_private_links(self):
        result = self.plan.snapshot(self.meeting)
        self.assertEqual(result["id"], "sample-2026-09-29")
        self.assertEqual(len(result["links"]), 1)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_other_meeting_does_not_inherit_plan(self):
        other = {**self.meeting, "meeting_id": "meeting-b", "remote_attendees": ["Another Person"]}
        self.assertIsNone(self.plan.snapshot(other))
        later = {**self.meeting, "meeting_id": "meeting-c", "started_at": "2026-09-30T08:04:00Z"}
        self.assertIsNone(self.plan.snapshot(later))

    def test_generic_capture_title_uses_tentative_near_time_only(self):
        generic = {**self.meeting, "meeting_id": "generic", "meeting": "Google Chrome Helper", "remote_attendees": []}
        self.assertEqual(self.plan.snapshot(generic)["match"], "time-only")
        outside = {**generic, "meeting_id": "later", "started_at": "2026-09-29T08:20:00Z"}
        self.assertIsNone(self.plan.snapshot(outside))

    def test_explicit_evidence_updates_only_current_meeting(self):
        answer = 'PLAN_UPDATE: {"id":"q1","status":"resolved","evidence":"We use PDF scans for our current document intake"}'
        self.assertEqual(self.plan.apply_analysis(self.meeting, answer), 1)
        self.assertEqual(self.plan.snapshot(self.meeting)["items"][0]["status"], "resolved")
        self.assertEqual(self.plan.snapshot(self.meeting)["score"], {
            "resolved": 1, "clarify": 0, "total": 2, "percent": 50,
            "by_kind": {
                "question": {"resolved": 1, "clarify": 0, "total": 1},
                "risk": {"resolved": 0, "clarify": 0, "total": 1},
                "objection": {"resolved": 0, "clarify": 0, "total": 0},
            },
        })
        other = {**self.meeting, "meeting_id": "meeting-b", "remote_attendees": ["Another Person"]}
        self.assertIsNone(self.plan.snapshot(other))
        self.assertEqual(self.plan.apply_analysis(self.meeting, 'PLAN_UPDATE: {"id":"r1","status":"resolved","evidence":"not in captured speech"}'), 0)
        self.assertEqual(self.plan.snapshot(self.meeting)["items"][1]["status"], "open")

    def test_manual_override_is_persistent_and_wins(self):
        self.plan.manual_status(self.meeting, "q1", "clarify")
        fresh = CallPlans(self.config, self.state)
        self.assertEqual(fresh.snapshot(self.meeting)["items"][0]["status"], "clarify")
        answer = 'PLAN_UPDATE: {"id":"q1","status":"resolved","evidence":"We use PDF scans for our current document intake"}'
        self.assertEqual(fresh.apply_analysis(self.meeting, answer), 0)
        self.assertEqual(fresh.snapshot(self.meeting)["items"][0]["status"], "clarify")

    def test_invalid_config_does_not_crash(self):
        self.config.write_text('{"version":1,"plans":[{"id":"bad","starts_at":"2026-09-29T10:00:00+02:00","items":[{"id":{},"kind":"question","text":"Hi"}]}]}')
        self.assertIsNone(self.plan.snapshot(self.meeting))

    def test_discover_existing_repository_preparation(self):
        repo = self.root / "selected-repo"
        repo.mkdir()
        source = repo / "PREP.md"
        source.write_text("""---
call_date: 2026-09-29
---
# Sales kit: Acme / Alex Sample

[Brief](https://example.com/brief)

## Мемо перед встречей
**Цель встречи.** Уточнить процесс и следующий шаг.

## Опросник
### Обязательные вопросы
1. Как устроена обработка одного документа?
2. Кто проверяет результат?

## Ответы на вопросы и возражения
**«У нас уже есть Excel».**

## Проверка перед встречей
- [ ] Разрешён внешний показ образцов.
""", encoding="utf-8")
        active = self.root / "active-repos.json"
        active.write_text(json.dumps({"repositories": [{"name": "sales", "path": str(repo)}]}), encoding="utf-8")
        found = RepositoryPreparations(active).for_date("2026-09-29")
        self.assertEqual(len(found), 1)
        self.assertEqual([item["kind"] for item in found[0]["items"]], [
            "question", "question", "risk", "objection",
        ])
        self.assertEqual(found[0]["links"][0]["url"], "https://example.com/brief")
        discovered = CallPlans(self.root / "absent.json", self.root / "discovered-state.json", active)
        self.assertEqual(discovered.snapshot(self.meeting)["source_label"], "sales/PREP.md")
        self.assertEqual(discovered.snapshot(self.meeting)["score"]["total"], 4)
        other = {**self.meeting, "meeting_id": "unrelated", "remote_attendees": [], "meeting": "Another call"}
        self.assertIsNone(discovered.snapshot(other))

    def test_configured_call_reads_current_repository_file(self):
        repo = self.root / "selected-repo"
        repo.mkdir()
        source = repo / "PREP.md"
        source.write_text("---\ncall_date: 2026-09-29\n---\n# Sales kit: Acme / Alex Sample\n## Опросник\n1. Первый вопрос?\n", encoding="utf-8")
        active = self.root / "active-repos.json"
        active.write_text(json.dumps({"repositories": [{"name": "sales", "path": str(repo)}]}), encoding="utf-8")
        self.config.write_text(json.dumps({"version": 1, "plans": [{
            "id": "sample-2026-09-29", "starts_at": "2026-09-29T10:00:00+02:00",
            "attendee_aliases": ["Alex Sample"], "title_aliases": ["Acme"],
            "source_file": str(source),
            "items": [{"id": "manual-risk", "kind": "risk", "text": "Проверить доступ."}],
        }]}), encoding="utf-8")
        plans = CallPlans(self.config, self.state, active)
        first = plans.snapshot(self.meeting)
        self.assertEqual(first["score"]["total"], 2)
        self.assertIn("Первый вопрос", first["items"][0]["text"])
        source.write_text("---\ncall_date: 2026-09-29\n---\n# Sales kit: Acme / Alex Sample\n## Опросник\n1. Обновлённый вопрос?\n", encoding="utf-8")
        second = plans.snapshot(self.meeting)
        self.assertIn("Обновлённый вопрос", second["items"][0]["text"])

    def test_calendar_matches_repository_preparation_when_capture_title_is_generic(self):
        repo = self.root / "selected-repo"
        repo.mkdir()
        (repo / "PREP.md").write_text(
            "---\ncall_date: 2026-09-29\n---\n# Sales kit: Acme / Alex Sample\n"
            "## Опросник\n1. Кто проверяет документы?\n", encoding="utf-8",
        )
        active = self.root / "active-repos.json"
        active.write_text(json.dumps({"repositories": [{"name": "sales", "path": str(repo)}]}), encoding="utf-8")

        class FakeCalendar:
            def for_day(self, day):
                return [{"title": "Demo documents — Acme / Alex Sample",
                         "start": "2026-09-29T10:00:00+02:00",
                         "end": "2026-09-29T10:30:00+02:00", "link": ""}]

        plans = CallPlans(self.root / "absent.json", self.state, active, FakeCalendar())
        generic = {**self.meeting, "meeting_id": "calendar-match", "meeting": "Google Chrome Helper",
                   "remote_attendees": [], "started_at": "2026-09-29T08:18:00Z"}
        matched = plans.snapshot(generic)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["match"], "calendar")
        self.assertEqual(matched["source_label"], "sales/PREP.md")
        unrelated = {**generic, "meeting_id": "unrelated", "started_at": "2026-09-29T09:20:00Z"}
        self.assertIsNone(plans.snapshot(unrelated))


if __name__ == "__main__":
    unittest.main()
