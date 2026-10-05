import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from archive import MeetingArchive


class ShortRecordingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.config.mkdir()
        self.recordings = self.root / "recordings"
        self.recordings.mkdir()
        self.archive = MeetingArchive(self.recordings, self.root / "archive", self.root / "reports", self.config)

    def test_boundary_and_manual_or_unknown_origin(self):
        for duration, expected in ((0, True), (299, True), (300, False), (301, False)):
            for trigger in ("mic-activity", "calendar"):
                self.assertEqual(self.archive._short_automatic({"recording_trigger": trigger,
                                                               "duration_seconds": duration}), expected)
        for trigger in ("manual", "", None):
            self.assertFalse(self.archive._short_automatic({"recording_trigger": trigger, "duration_seconds": 10}))

    def test_wait_before_stopping_does_not_make_dictation_a_meeting(self):
        for reason, quiet in (("call-ended", 15), ("silence", 600), ("calendar-event-ended", 60)):
            for duration, expected in ((quiet + 299, True), (quiet + 300, False)):
                self.assertEqual(self.archive._short_automatic({"recording_trigger": "mic-activity",
                                                               "stop_reason": reason, "duration_seconds": duration}), expected)

    def test_runtime_configuration_and_invalid_values(self):
        for value, expected in ((600, True), (60, False), ("bad", True), (-1, True), (True, True)):
            (self.config / "config.json").write_text(json.dumps({"auto_record": {"min_duration_seconds": value}}))
            self.assertEqual(self.archive._short_automatic({"recording_trigger": "mic-activity",
                                                           "duration_seconds": 120}), expected)

    def test_discarded_native_session_cannot_reappear_from_transcript(self):
        directory = self.recordings / "fixture"
        directory.mkdir()
        started = "2026-10-02T10:00:00Z"
        marker = directory / ".recording.json"
        marker.write_text(json.dumps({"trigger": "mic-activity", "started": started}))
        transcript = {"meeting_id": "fixture", "started_at": started, "recording_dir": str(directory),
                      "status": "recording", "latest_at": "2026-10-02T10:01:00Z",
                      "segments": [{"timestamp": "2026-10-02T10:01:00Z", "text": "Synthetic dictation"}]}
        self.archive.sync_transcript(transcript)
        self.assertEqual(self.archive.detail("fixture")["recording_trigger"], "mic-activity")
        marker.unlink()
        directory.rmdir()
        self.archive.sync_transcript({**transcript, "status": "finished"})
        self.assertEqual(self.archive.list_meetings(), [])
        self.assertFalse(self.archive.needs_report("fixture"))
        self.assertEqual(len(self.archive.detail("fixture")["transcript"]), 1)

    def test_short_raw_auto_session_is_hidden_without_deleting_audio(self):
        directory = self.recordings / "raw"
        directory.mkdir()
        audio = directory / "mic.caf"
        audio.write_bytes(b"fixture")
        (directory / "meta.json").write_text(json.dumps({"trigger": "mic-activity", "duration_seconds": 120,
                                                         "files": {"mic": "mic.caf"}}))
        self.assertEqual(self.archive.list_meetings(), [])
        self.assertTrue(audio.exists())

    def test_short_auto_delivery_is_blocked_and_long_merged_call_survives(self):
        ended = datetime.now(timezone.utc) - timedelta(minutes=5)
        detail = {"recording_trigger": "mic-activity", "duration_seconds": 120, "status": "finished",
                  "started_at": (ended - timedelta(seconds=120)).isoformat(), "ended_at": ended.isoformat()}
        self.assertFalse(self.archive._ready_for_delivery(detail))
        merged = {**detail, "duration_seconds": 3600, "recording_discarded": True,
                  "source_meeting_ids": ["long", "short"]}
        self.assertFalse(self.archive._short_automatic(merged))


if __name__ == "__main__":
    unittest.main()
