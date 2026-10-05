import copy
import json
import threading
import tempfile
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

from archive import MeetingArchive
from speaker_edits import SpeakerEdits, segment_id


class SpeakerEditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.edits = SpeakerEdits(self.root / "archive")
        self.snapshot = {
            "meeting_id": "meeting-a",
            "segments": [
                {"source": "microphone", "timestamp": "2026-09-27T10:00:00Z", "text": "hello"},
                {"source": "system", "voice_id": "remote-1", "timestamp": "2026-09-27T10:00:10Z", "text": "hi"},
                {"source": "system", "voice_id": "remote-1", "timestamp": "2026-09-27T10:00:20Z", "text": "yes"},
                {"source": "microphone", "speaker_identity": "unverified", "timestamp": "2026-09-27T10:10:00Z", "text": "uncertain"},
            ],
        }

    def tearDown(self):
        self.directory.cleanup()

    def test_stable_voice_slots_and_unassigned_are_distinct(self):
        result = self.edits.annotate(self.snapshot)
        self.assertEqual([s["speaker_id"] for s in result["segments"]], ["self", "remote-1", "remote-1", "unassigned"])
        self.assertEqual(result["speakers"][1]["name"], "Собеседник 1")
        self.assertNotIn("speaker_id", self.snapshot["segments"][0])

    def test_bulk_rename_survives_reload_and_new_streamed_turn(self):
        result = self.edits.rename(self.snapshot, "remote-1", "Alex Sample")
        self.assertEqual([s["speaker_label"] for s in result["segments"][1:3]], ["Alex Sample"] * 2)
        fresh = copy.deepcopy(self.snapshot)
        fresh["segments"].append({"source": "system", "voice_id": "remote-1", "timestamp": "2026-09-27T10:01:00Z", "text": "new"})
        reloaded = SpeakerEdits(self.root / "archive").annotate(fresh)
        self.assertEqual(reloaded["segments"][-1]["speaker"], "Alex Sample")
        self.assertEqual(result["segments"][0]["speaker_id"], "self")

    def test_manual_name_wins_over_screenshot_name(self):
        self.edits.rename(self.snapshot, "remote-1", "Alex")
        automatic = copy.deepcopy(self.snapshot)
        automatic["segments"][1]["speaker"] = "Different OCR Name"
        self.assertEqual(self.edits.annotate(automatic)["segments"][1]["speaker"], "Alex")

    def test_assignment_only_changes_selected_turn_not_source_or_text(self):
        key = segment_id(self.snapshot["segments"][-1])
        result = self.edits.assign(self.snapshot, [key], "remote-1")
        segment = result["segments"][-1]
        self.assertEqual(segment["speaker_id"], "remote-1")
        self.assertEqual(segment["source"], "microphone")
        self.assertEqual(segment["text"], "uncertain")
        self.assertEqual(segment["speaker_identity"], "manual")
        self.assertEqual(result["segments"][0]["speaker_id"], "self")

    def test_new_participant_and_subsequent_rename(self):
        key = segment_id(self.snapshot["segments"][-1])
        first = self.edits.assign(self.snapshot, [key], name="Ana Silva")
        target = first["segments"][-1]["speaker_id"]
        result = self.edits.rename(first, target, "Ana")
        self.assertEqual(result["segments"][-1]["speaker"], "Ana")

    def test_same_name_in_other_meeting_is_not_changed(self):
        self.edits.rename(self.snapshot, "remote-1", "Alex")
        other = {**self.snapshot, "meeting_id": "meeting-b"}
        self.assertEqual(self.edits.annotate(other)["segments"][1]["speaker_label"], "Собеседник 1")

    def test_partial_text_changes_do_not_change_segment_id(self):
        segment = self.snapshot["segments"][0]
        self.assertEqual(segment_id(segment), segment_id({**segment, "text": "revised text"}))

    def test_stale_edit_preserves_all_canonical_turns(self):
        self.edits.rename(self.snapshot, "remote-1", "Alex")
        stale = {**self.snapshot, "segments": self.snapshot["segments"][:2]}
        result = self.edits.rename(stale, "remote-1", "Alex Sample")
        self.assertEqual(len(result["segments"]), 4)
        self.assertEqual(result["segments"][2]["speaker"], "Alex Sample")

    def test_validation_rejects_unknown_ids_and_unassigned_bulk_rename(self):
        with self.assertRaises(ValueError):
            self.edits.rename(self.snapshot, "unassigned", "Alex")
        with self.assertRaises(ValueError):
            self.edits.assign(self.snapshot, ["not-present"], "remote-1")
        with self.assertRaises(ValueError):
            self.edits.assign(self.snapshot, [], "self")
        with self.assertRaises(ValueError):
            self.edits.rename(self.snapshot, "remote-1", "bad\nname")
        with self.assertRaises(ValueError):
            self.edits.annotate({**self.snapshot, "meeting_id": "../escape"})

    def test_archive_and_report_use_corrected_canonical_transcript(self):
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.root / "config")
        archive.sync_transcript(self.snapshot)
        archive.speaker_edits.rename(self.snapshot, "remote-1", "Alex Sample")
        detail = archive.detail("meeting-a")
        self.assertEqual(detail["transcript"][1]["speaker"], "Alex Sample")
        page = archive._report_html(detail, [])
        self.assertIn("Alex Sample", page)
        canonical = json.loads((self.root / "archive/meeting-a/meeting.json").read_text())
        self.assertEqual(canonical["segments"][1]["speaker"], "Alex Sample")
        self.assertFalse((self.root / "archive/meeting-a/speaker-edits.json").exists())
        self.assertNotIn("history", canonical)
        archive.sync_transcript(self.snapshot)
        self.assertEqual(archive.detail("meeting-a")["transcript"][1]["speaker"], "Alex Sample")

    def test_recorded_manual_correction_keeps_original_group_across_roundtrip(self):
        first = self.edits.rename(self.snapshot, "remote-1", "Alex")
        second = self.edits.annotate(first)
        self.assertEqual(second["segments"][1]["speaker_id"], "remote-1")
        self.assertEqual(second["segments"][1]["speaker"], "Alex")

    def test_capture_refresh_cannot_undo_selected_turn_correction(self):
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.root / "config")
        archive.sync_transcript(self.snapshot)
        key = segment_id(self.snapshot["segments"][-1])
        archive.speaker_edits.assign(self.snapshot, [key], "remote-1")
        refreshed = copy.deepcopy(self.snapshot)
        refreshed["segments"][-1]["text"] = "updated recognition"
        archive.sync_transcript(refreshed)
        canonical = json.loads((self.root / "archive/meeting-a/meeting.json").read_text())
        self.assertEqual(canonical["segments"][-1]["speaker_identity"], "manual")
        self.assertEqual(canonical["segments"][-1]["speaker_id"], "remote-1")
        self.assertEqual(canonical["segments"][-1]["text"], "updated recognition")

    def test_report_refresh_uses_correction_without_resending_memos(self):
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.root / "config")
        archive.sync_transcript(self.snapshot)
        report_dir = self.root / "reports/meeting-a"
        report_dir.mkdir()
        (report_dir / "report.json").write_text(json.dumps({"mail_status": "sent", "telegram_status": "sent", "drive_status": "uploaded"}))
        archive.speaker_edits.rename(self.snapshot, "remote-1", "Alex Sample")
        with patch.object(archive, "_print_pdf", side_effect=lambda html, pdf: pdf.write_bytes(b"%PDF synthetic fixture")), patch.object(archive, "deliver") as delivery:
            result = archive.generate_report("meeting-a", deliver=False)
            delivery.assert_not_called()
        self.assertEqual(result["mail_status"], "sent")
        self.assertEqual(result["telegram_status"], "sent")
        self.assertEqual(result["drive_status"], "pending")
        self.assertIn("Alex Sample", (report_dir / "index.html").read_text())

    def test_http_editor_writes_canonical_archive_and_rejects_undo(self):
        import server
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.root / "config")
        archive.sync_transcript(self.snapshot)
        transcript = Mock()
        transcript.snapshot.return_value = self.snapshot
        frames = Mock()
        frames.annotate.side_effect = lambda snapshot: snapshot
        with patch.multiple(server, ARCHIVE=archive, TRANSCRIPT=transcript, FRAMES=frames, COPILOT=Mock()):
            http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            worker = threading.Thread(target=http.serve_forever, daemon=True)
            worker.start()
            try:
                url = f"http://127.0.0.1:{http.server_port}/api/speakers"
                def post(payload):
                    request = urllib.request.Request(url, data=json.dumps({"meeting_id": "meeting-a", **payload}).encode(), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(request) as response:
                        return json.load(response)
                result = post({"operation": "rename", "speaker_id": "remote-1", "name": "Alex"})
                self.assertTrue(result["ok"])
                result = post({"operation": "assign", "segment_ids": [segment_id(self.snapshot["segments"][-1])], "speaker_id": "remote-1"})
                self.assertEqual(result["transcript"]["segments"][-1]["speaker"], "Alex")
                saved = json.loads((self.root / "archive/meeting-a/meeting.json").read_text())
                self.assertEqual(saved["segments"][-1]["speaker"], "Alex")
                self.assertNotIn("history", saved)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    post({"operation": "undo"})
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
            finally:
                http.shutdown()
                worker.join()
                http.server_close()


if __name__ == "__main__":
    unittest.main()
