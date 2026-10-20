import json
from pathlib import Path
import tempfile
import unittest
import threading
import os
from archive import MeetingArchive, _json, _atomic_json
from ai_providers import AIService, Reply
from summary_rewrite import SummaryRewrites


class SummaryRewriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.archive = MeetingArchive(root / "recordings", root / "archive", root / "reports", root / "config")
        self.archive.sync_transcript({"meeting_id": "old", "meeting": "Previous call", "status": "finished",
                                     "started_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:10:00Z",
                                     "segments": [{"text": "The pilot has not been approved.", "timestamp": "2026-01-01T10:01:00Z"}]})

    def test_rewrite_is_isolated_audited_and_does_not_change_report_delivery_source(self):
        before = self.archive.source_signature(self.archive.detail("old"))
        prompts = []
        def run(prompt):
            prompts.append(prompt)
            return Reply(json.dumps({"points": ["Pilot approval is still pending."], "questions": ["Who approves the pilot?"]}),
                         "fixture-reported-model", "")
        jobs = SummaryRewrites(self.archive, run)
        worker = jobs.submit("old", "Focus on approval and next steps")
        worker.join(3)
        self.assertEqual(jobs.snapshot("old")["state"], "done")
        detail = self.archive.detail("old")
        self.assertEqual(detail["overview"]["points"], ["Pilot approval is still pending."])
        self.assertEqual(detail["overview"]["model"], "fixture-reported-model")
        self.assertIn("The pilot has not been approved.", prompts[0])
        self.assertEqual(self.archive.source_signature(detail), before)
        self.assertEqual(list(self.archive.reports_root.iterdir()), [])
        self.archive.rename_meeting("old", "New label")
        self.assertEqual(self.archive.detail("old")["overview"]["points"], ["Pilot approval is still pending."])
        jobs.run = lambda _: "invalid"
        jobs.submit("old", "Shorten this").join(3)
        self.assertEqual(self.archive.detail("old")["overview"]["points"], ["Pilot approval is still pending."])

    def test_invalid_model_output_preserves_existing_summary_and_title(self):
        self.archive.rename_meeting("old", "Chosen title")
        jobs = SummaryRewrites(self.archive, lambda _: '{"points":"not an array","questions":[]}')
        worker = jobs.submit("old", "Shorten")
        worker.join(3)
        self.assertEqual(jobs.snapshot("old")["state"], "failed")
        self.assertEqual(self.archive.detail("old")["title"], "Chosen title")
        self.assertNotIn("model", self.archive.detail("old")["overview"])

    def test_rewrite_does_not_apply_to_changed_source_material(self):
        jobs = SummaryRewrites(self.archive, lambda _: '{"points":["Old result"],"questions":[]}')
        worker = jobs.submit("old", "Shorten")
        worker.join(3)
        path = self.archive.archive_root / "old/meeting.json"
        changed = _json(path, {})
        changed["segments"].append({"text": "New source material", "timestamp": "2026-01-01T10:02:00Z"})
        _atomic_json(path, changed)
        self.assertNotIn("Old result", self.archive.detail("old")["overview"]["points"])

    def test_resumed_meeting_rejects_inflight_rewrite(self):
        started, finish = threading.Event(), threading.Event()
        def run(_):
            started.set(); finish.wait(3)
            return '{"points":["No longer current"],"questions":[]}'
        jobs = SummaryRewrites(self.archive, run)
        worker = jobs.submit("old", "Shorten")
        try:
            self.assertTrue(started.wait(1))
            path = self.archive.archive_root / "old/meeting.json"
            changed = _json(path, {}); changed["status"] = "recording"; _atomic_json(path, changed)
            with self.assertRaises(ValueError): jobs.submit("old", "Another request")
        finally:
            finish.set(); worker.join(3)
        self.assertEqual(jobs.snapshot("old")["state"], "failed")
        self.assertNotIn("model", self.archive.detail("old")["overview"])

    @unittest.skipUnless(os.environ.get("MEETONTRACK_AI_SMOKE_CONFIG"),
                         "Opt-in authenticated smoke: path to a config.json whose ai.purposes.summary_rewrite is set")
    def test_authenticated_provider_can_rewrite_synthetic_meeting(self):
        service = AIService(os.environ["MEETONTRACK_AI_SMOKE_CONFIG"], os.environ.copy())
        jobs = SummaryRewrites(self.archive, lambda prompt: service.run("summary_rewrite", prompt, timeout=180))
        worker = jobs.submit("old", "In English, state briefly whether the pilot was approved. Do not invent agreement.")
        worker.join(190)
        self.assertFalse(worker.is_alive())
        self.assertEqual(jobs.snapshot("old")["state"], "done")
        detail = self.archive.detail("old")
        self.assertTrue(detail["overview"]["model"])
        self.assertTrue(detail["overview"]["points"])


if __name__ == "__main__": unittest.main()
