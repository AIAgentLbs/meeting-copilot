import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import server
from meeting_boundaries import MeetingBoundaries
from archive import MeetingArchive


class LogicalServerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.boundaries = MeetingBoundaries(self.root / "boundaries.json")
        self.transcript = server.TranscriptState(self.root / "live.json")
        self.transcript.meeting_id = "physical"
        self.transcript.meeting = "Example"
        self.transcript.started_at = "2026-01-01T10:00:00Z"
        self.transcript.status = "recording"
        self.session = server.CodexSession(self.root / "copilot.json")
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.root)
        self.native_calls = []
        health = SimpleNamespace(sample=lambda snapshot: {"audio_recording": True, "state": "recording"})
        self.guard = SimpleNamespace(health=health, tick=lambda **kw: self.native_calls.append(kw) or {"ok": True})
        for name, value in (("TRANSCRIPT", self.transcript), ("COPILOT", self.session),
                            ("BOUNDARIES", self.boundaries), ("RECOGNITION_GUARD", self.guard), ("ARCHIVE", archive)):
            patcher = patch.object(server, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        worker = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def post(self, path="/api/meeting/new", expected="physical", token="one", origin=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=3)
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        conn.request("POST", path, json.dumps({"expected_meeting_id": expected, "request_id": token, "title": "Second", "meeting_id": expected}), headers)
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response.status, json.loads(body) if body.startswith(b"{") else {}

    def test_split_keeps_native_identity_and_no_native_controls(self):
        status, result = self.post()
        self.assertEqual(status, 200)
        self.assertNotEqual(result["meeting_id"], "physical")
        self.assertEqual(self.transcript.snapshot()["meeting_id"], result["meeting_id"])
        self.assertEqual(self.transcript.physical_snapshot()["meeting_id"], "physical")
        self.assertEqual(self.native_calls, [])
        self.assertEqual(self.post()[1], result)
        self.assertEqual(self.post(token="two")[0], 409)
        self.assertEqual(self.post("/api/recognition/resume", result["meeting_id"])[0], 200)
        self.assertEqual(self.native_calls, [{"manual_meeting_id": "physical"}])

    def test_inactive_and_wrong_origin_do_not_write(self):
        self.transcript.status = "finished"
        self.assertEqual(self.post()[0], 409)
        self.assertFalse(self.boundaries.path.exists())
        self.transcript.status = "recording"
        self.assertEqual(self.post(origin="https://example.com")[0], 403)
        self.assertFalse(self.boundaries.path.exists())

    def test_split_works_while_audio_records_without_live_transcript(self):
        expected = "physical"
        for status in ("unavailable", "paused", "error"):
            self.transcript.status = status
            code, result = self.post(expected=expected, token=status)
            self.assertEqual(code, 200, (status, result))
            expected = result["meeting_id"]
        self.guard.health.sample = lambda snapshot: {"audio_recording": False}
        self.assertEqual(self.post(token="silent")[0], 409)

    def test_success_retry_returns_same_result_after_recording_stops(self):
        status, result = self.post()
        self.assertEqual(status, 200)
        self.transcript.status = "finished"
        self.guard.health.sample = lambda snapshot: {"audio_recording": False}
        self.assertEqual(self.post(), (200, result))

    def test_old_ai_completion_keeps_old_chat_and_new_thread_empty(self):
        entered, release = threading.Event(), threading.Event()
        def inference(prompt, planning=False):
            entered.set()
            release.wait(3)
            self.session.thread_id = "old-thread"
            return "synthetic old answer"
        with patch.object(self.session, "_run_ai", side_effect=inference), patch.object(server.GOOGLE_CONTEXT, "augment", return_value=""):
            worker = threading.Thread(target=lambda: self.session.ask("question", "old", "Example", "physical", {"repositories": []}))
            worker.start()
            self.assertTrue(entered.wait(2))
            status, result = self.post()
            self.assertEqual(status, 200)
            self.session.bind_meeting(result["meeting_id"])
            self.assertEqual(self.session.snapshot(result["meeting_id"])["messages"], [])
            release.set()
            worker.join(3)
        self.session.bind_meeting(result["meeting_id"])
        self.assertEqual(self.session.thread_id, "")
        self.assertEqual(len(self.session.snapshot("physical")["messages"]), 2)
        self.assertEqual(self.session.snapshot(result["meeting_id"])["messages"], [])

    def test_old_analysis_status_cannot_overwrite_new_meeting(self):
        self.session.bind_meeting("physical")
        self.session.bind_meeting("second")
        self.session.record_analysis(answer="old signal", meeting_id="physical")
        self.assertEqual(self.session.snapshot("second")["analysis"]["state"], "idle")

    def test_import_continuous_chat_routes_each_message_by_its_time(self):
        self.transcript.updated_at = "2026-01-01T10:10:00Z"
        second = self.boundaries.split(self.transcript.physical_snapshot(), "physical", "chat", "Second", "2026-01-01T10:05:00Z")["meeting_id"]
        journal = server.MeetingJournal(self.root / "journal.json")
        chat = server.MeetingChat(self.root / "chat.json")
        messages = server.parse_chat_export(json.dumps([
            {"sender": "Example", "text": "Old content", "timestamp": "2026-01-01T10:02:00Z"},
            {"sender": "Example", "text": "New content", "timestamp": "2026-01-01T10:08:00Z"},
            {"sender": "Example", "text": "Unknown content"}]))
        with patch.object(server, "JOURNAL", journal):
            chat.add_many(messages, second, "Second", "", "export")
        self.assertEqual([item["text"] for item in chat.snapshot(second)], ["New content"])
        old = chat.snapshot("physical")
        self.assertEqual([item["text"] for item in old], ["Old content", "Unknown content"])
        self.assertTrue(old[-1]["boundary_unassigned"])
