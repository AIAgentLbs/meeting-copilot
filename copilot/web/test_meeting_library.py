import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import archive as archive_module
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from summary_rewrite import SummaryRewrites

from archive import MeetingArchive


class MeetingLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.config)
        self.snapshot = {"meeting_id": "example", "meeting": "Customer discussion", "status": "finished",
                         "started_at": "2026-10-16T10:00:00Z", "updated_at": "2026-10-16T10:12:00Z",
                         "segments": [{"timestamp": "2026-10-16T10:01:00Z", "speaker": "Alice", "text": "We discussed the lighthouse integration."}]}
        self.archive.sync_transcript(self.snapshot)
        (self.config / "journal.json").write_text(json.dumps({"items": [
            {"id": "fact", "meeting_id": "example", "category": "FACT", "text": "A pilot was discussed.", "created_at": "2026-10-16T10:01:00Z"},
            {"id": "question", "meeting_id": "example", "category": "ASK", "text": "Who will approve the integration?", "created_at": "2026-10-16T10:02:00Z"},
            {"id": "resolved", "meeting_id": "example", "category": "ASK", "text": "When will the pilot start?", "status": "resolved"}]}))

    def test_search_matches_contents_speaker_and_title_but_never_returns_full_transcript(self):
        for query in ["LIGHTHOUSE", "alice", "customer", "pilot"]:
            with self.subTest(query=query):
                meetings = self.archive.list_meetings(query=query)
                self.assertEqual([item["meeting_id"] for item in meetings], ["example"])
                self.assertNotIn("transcript", meetings[0])
        self.assertEqual(self.archive.list_meetings(query="not present"), [])

    def test_rename_survives_capture_refresh_without_changing_audio_or_transcript(self):
        before = (self.root / "archive/example/meeting.json").read_bytes()
        signature = self.archive.source_signature(self.archive.detail("example"))
        self.archive.rename_meeting("example", "Integration pilot")
        self.archive.sync_transcript(self.snapshot)
        self.assertEqual(self.archive.detail("example")["title"], "Integration pilot")
        self.assertEqual(self.archive.list_meetings()[0]["title"], "Integration pilot")
        self.assertEqual((self.root / "archive/example/meeting.json").read_bytes(), before)
        self.assertEqual(self.archive.source_signature(self.archive.detail("example")), signature,
                         "Renaming the library must not trigger automatic report regeneration/delivery")

    def test_empty_or_unknown_rename_is_rejected(self):
        for identity, title in [("missing", "Test"), ("example", " "), ("example", "x" * 201)]:
            with self.subTest(identity=identity, title=title):
                with self.assertRaises(ValueError):
                    self.archive.rename_meeting(identity, title)

    def test_rename_does_not_change_continuous_recording_chain(self):
        first = dict(self.snapshot, recording_dir=str(self.root / "recordings/one"))
        second = dict(self.snapshot, meeting_id="second", recording_dir=str(self.root / "recordings/two"),
                      started_at="2026-10-16T10:12:30Z", updated_at="2026-10-16T10:25:00Z")
        self.archive.sync_transcript(first)
        self.archive.sync_transcript(second)
        before = self.archive.report_detail("example")["source_meeting_ids"]
        self.assertEqual(before, ["example", "second"])
        self.archive.rename_meeting("example", "Different label")
        self.assertEqual(self.archive.report_detail("example")["source_meeting_ids"], before)

    def test_overview_contains_source_grounded_points_and_only_unresolved_questions(self):
        detail = self.archive.detail("example")
        self.assertEqual(detail["overview"]["points"], ["A pilot was discussed."])
        self.assertEqual(detail["overview"]["questions"], ["Who will approve the integration?"])
        self.assertEqual(self.archive.list_meetings()[0]["library_status"], "analysis_ready")

    def test_no_speech_is_not_presented_as_a_completed_summary(self):
        self.snapshot["segments"] = []
        (self.config / "journal.json").write_text('{"items": []}')
        self.archive.sync_transcript(dict(self.snapshot, meeting_id="empty"))
        detail = self.archive.detail("empty")
        self.assertEqual(detail["library_status"], "no_speech")
        self.assertTrue(detail["overview"]["insufficient"])

    def test_search_scans_recording_metadata_once_per_operation_not_per_meeting(self):
        directory = self.root / "recordings/one"
        directory.mkdir(parents=True)
        (directory / "meta.json").write_text('{"started":"2026-10-16T10:00:00Z","duration_seconds":720}')
        for number in range(4):
            self.archive.sync_transcript(dict(self.snapshot, meeting_id=f"m{number}"))
        reads = []
        original = archive_module._json
        def read(path, fallback):
            if path.name == "meta.json": reads.append(str(path))
            return original(path, fallback)
        with patch.object(archive_module, "_json", side_effect=read):
            self.archive.list_meetings(query="alice")
            self.assertEqual(len(reads), 1)
            self.archive.list_meetings(query="alice")
            self.assertEqual(len(reads), 2)

    def test_local_actions_only_resolve_existing_audio_or_folders_in_allowed_roots(self):
        directory = self.root / "recordings/one"
        directory.mkdir(parents=True)
        (directory / "audio.wav").write_bytes(b"synthetic")
        (directory / "meta.json").write_text(json.dumps({"started": self.snapshot["started_at"], "duration_seconds": 720, "files": {"audio": "audio.wav"}}))
        self.archive.sync_transcript(dict(self.snapshot, recording_dir=str(directory)))
        self.assertEqual(self.archive.local_target("example", "audio"), (directory / "audio.wav").resolve())
        self.assertEqual(self.archive.local_target("example", "folder"), directory.resolve())
        with self.assertRaises(ValueError): self.archive.local_target("example", "execute")
        outside = self.root / "outside.txt"
        outside.write_text("not meeting material")
        (directory / "meta.json").write_text(json.dumps({"started": self.snapshot["started_at"], "files": {"audio": str(outside)}}))
        with self.assertRaises(ValueError): self.archive.local_target("example", "audio")

    def test_http_search_rename_rewrite_and_origin_guards(self):
        import server
        jobs = SummaryRewrites(self.archive, lambda _: '{"points":["Approval pending"],"questions":[]}')
        with patch.object(server, "ARCHIVE", self.archive), patch.object(server, "SUMMARY_REWRITES", jobs):
            http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            worker = threading.Thread(target=http.serve_forever, daemon=True); worker.start()
            base = f"http://127.0.0.1:{http.server_port}"
            try:
                with urlopen(base + "/api/archive?q=lighthouse") as response:
                    self.assertEqual([item["meeting_id"] for item in json.load(response)["meetings"]], ["example"])
                for action, payload in [("rename", {"meeting_id": "example", "title": "A new title"}),
                                        ("rewrite", {"meeting_id": "example", "instructions": "Shorten"})]:
                    request = Request(base + "/api/archive/" + action, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Origin": base})
                    with urlopen(request) as response: self.assertTrue(json.load(response)["ok"])
                jobs.worker.join(3)
                with urlopen(base + "/api/summary-rewrite?meeting_id=example") as response:
                    self.assertEqual(json.load(response)["rewrite"]["state"], "done")
                for action in ("rename", "rewrite", "open-local"):
                    request = Request(base + "/api/archive/" + action, data=b'{}', headers={"Origin": "https://untrusted.example"})
                    with self.assertRaises(HTTPError) as failure: urlopen(request)
                    self.assertEqual(failure.exception.code, 403); failure.exception.close()
            finally:
                http.shutdown(); http.server_close(); worker.join()


if __name__ == "__main__":
    unittest.main()
