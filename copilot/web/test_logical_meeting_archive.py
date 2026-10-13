import json
import tempfile
import unittest
from pathlib import Path
from archive import MeetingArchive
from meeting_boundaries import MeetingBoundaries


class LogicalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.config = root / "config"
        self.config.mkdir()
        self.recording = root / "recordings" / "physical"
        self.recording.mkdir(parents=True)
        (self.recording / "meta.json").write_text(json.dumps({"started": "2026-01-01T10:00:00Z", "ended": "2026-01-01T10:20:00Z", "duration_seconds": 1200}))
        (self.recording / "audio.wav").write_bytes(b"synthetic")
        self.store = MeetingBoundaries(root / "boundaries.json")
        self.archive = MeetingArchive(root / "recordings", root / "archive", root / "reports", self.config)
        self.physical = {"meeting_id": "p1", "meeting": "Example", "status": "recording",
                         "started_at": "2026-01-01T10:00:00Z", "recording_dir": str(self.recording),
                         "updated_at": "2026-01-01T10:20:00Z", "segments": [
                             {"timestamp": "2026-01-01T10:02:00Z", "source": "system", "text": "old"},
                             {"timestamp": "2026-01-01T10:08:00Z", "source": "system", "text": "new"}]}
        self.second = self.store.split(self.physical, "p1", "one", "Example", "2026-01-01T10:05:00Z")["meeting_id"]
        self.physical["status"] = "finished"

    def sync(self):
        for part in self.store.project(self.physical):
            self.archive.sync_transcript(part)

    def test_report_not_merged_and_duration_bounded(self):
        self.sync()
        first = self.archive.report_detail("p1")
        second = self.archive.report_detail(self.second)
        self.assertEqual(first["source_meeting_ids"], ["p1"])
        self.assertEqual(second["source_meeting_ids"], [self.second])
        self.assertEqual(first["duration_seconds"], 300)
        self.assertEqual(second["duration_seconds"], 900)
        self.assertEqual([s["text"] for s in first["transcript"]], ["old"])
        self.assertEqual([s["text"] for s in second["transcript"]], ["new"])
        self.assertEqual(second["audio_file"], "")
        self.assertEqual(second["audio_range"]["start_seconds"], 300)

    def test_first_archive_shrinks_from_physical_to_logical(self):
        self.archive.sync_transcript(self.physical)
        self.sync()
        self.assertEqual([s["text"] for s in self.archive.detail("p1")["transcript"]], ["old"])
        self.physical["segments"].insert(0, {"timestamp": "2026-01-01T10:01:00Z", "source": "system", "text": "late"})
        self.sync()
        self.assertEqual([s["text"] for s in self.archive.detail("p1")["transcript"]], ["late", "old"])
        self.assertEqual(len(self.archive.detail(self.second)["transcript"]), 1)

    def test_closed_logical_interval_report_eligible_with_native_marker(self):
        self.physical["status"] = "recording"
        (self.recording / ".recording.json").write_text("{}")
        self.sync()
        self.assertTrue(self.archive.needs_report("p1"))
        self.assertFalse(self.archive.needs_report(self.second))
