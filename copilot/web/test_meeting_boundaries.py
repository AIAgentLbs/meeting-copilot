import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

try:
    from meeting_boundaries import MeetingBoundaries, BoundaryConflict, BoundaryUnavailable
except ImportError:
    MeetingBoundaries = None


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "boundaries.json"
        self.physical = {"meeting_id": "p1", "meeting": "Example", "status": "recording",
                         "started_at": "2026-01-01T10:00:00Z", "segments": []}

    def store(self):
        self.assertIsNotNone(MeetingBoundaries, "logical meeting store is missing")
        return MeetingBoundaries(self.path)

    def split(self, store, expected="p1", token="one", at="2026-01-01T10:05:00Z"):
        return store.split(self.physical, expected, token, "Second", at)

    def test_retry_survives_restart(self):
        store = self.store()
        result = self.split(store)
        self.assertEqual(self.split(self.store(), at="2026-01-01T10:06:00Z"), result)
        self.assertEqual([p["meeting_id"] for p in store.project(self.physical)], ["p1", result["meeting_id"]])
        self.assertNotIn("segments", self.path.read_text())

    def test_three_boundaries_are_independent(self):
        store = self.store()
        identity = "p1"
        for minute in (5, 10, 15):
            identity = self.split(store, identity, str(minute), f"2026-01-01T10:{minute:02d}:00Z")["meeting_id"]
        parts = store.project(self.physical)
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0]["audio_range"], {"start_seconds": 0.0, "end_seconds": 300.0})
        self.assertIsNone(parts[-1]["logical_interval"]["end"])

    def test_concurrent_stale_tabs_make_one_boundary(self):
        store = self.store()
        def attempt(token):
            try:
                self.split(store, token=token)
                return "ok"
            except BoundaryConflict:
                return "conflict"
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(attempt, ["a", "b"])), ["conflict", "ok"])

    def test_failed_write_does_not_publish(self):
        store = self.store()
        with patch("meeting_boundaries.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                self.split(store)
        self.assertEqual(len(store.project(self.physical)), 1)
        self.assertFalse(self.path.exists())

    def test_corrupt_store_fails_closed(self):
        self.path.write_text('{"version":1,"sessions":"bad"}')
        self.assertIsNotNone(MeetingBoundaries)
        with self.assertRaises(ValueError):
            MeetingBoundaries(self.path)

    def test_late_and_crossing_speech_preserved_once(self):
        store = self.store()
        self.split(store)
        self.physical["segments"] = [
            {"timestamp": "2026-01-01T10:04:59Z", "end_timestamp": "2026-01-01T10:05:02Z", "text": "old", "source": "system"},
            {"timestamp": "2026-01-01T10:05:00Z", "text": "new", "source": "microphone"},
            {"timestamp": "bad", "text": "uncertain", "source": "system"}]
        parts = store.project(self.physical)
        self.assertEqual([s["text"] for s in parts[0]["segments"]], ["old", "uncertain"])
        self.assertTrue(parts[0]["segments"][0]["spans_boundary"])
        self.assertTrue(parts[0]["segments"][1]["boundary_unassigned"])
        self.assertEqual([s["text"] for s in parts[1]["segments"]], ["new"])

    def test_stop_and_next_physical_session(self):
        store = self.store()
        self.split(store)
        self.physical.update(status="finished", updated_at="2026-01-01T10:09:00Z")
        self.assertEqual(store.project(self.physical)[-1]["logical_interval"]["end"], "2026-01-01T10:09:00Z")
        self.assertEqual(len(store.project({**self.physical, "meeting_id": "p2"})), 1)

    def test_inactive_token_reuse_and_nonmonotonic_rejected(self):
        store = self.store()
        result = self.split(store)
        with self.assertRaises(BoundaryConflict):
            self.split(store, expected=result["meeting_id"], at="2026-01-01T10:04:00Z", token="two")
        with self.assertRaises(BoundaryConflict):
            self.split(store, expected=result["meeting_id"])
        self.physical["status"] = "finished"
        with self.assertRaises(BoundaryUnavailable):
            self.split(store, expected=result["meeting_id"], token="three")
