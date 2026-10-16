import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class CanonicalTranscriptTests(unittest.TestCase):
    def test_missing_live_end_does_not_assign_a_voice_across_a_recognition_gap(self):
        from canonical_transcript import canonical_segments
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            started = "2026-10-16T09:00:00Z"
            (root / "meta.json").write_text(json.dumps({"started": started}))
            (root / "transcript.json").write_text(json.dumps({"engine": "parakeet", "segments": [
                {"speaker": "them", "start_ms": 6000, "end_ms": 8000, "text": "Covered voice"},
                {"speaker": "them", "start_ms": 60000, "end_ms": 70000, "text": "Unobserved later voice"}]}))
            payload = {"status": "finished", "started_at": started, "recording_dir": directory,
                       "segments": [{"source": "system", "timestamp": "2026-10-16T09:00:05Z",
                                     "voice_id": "remote-1"}]}
            segments = canonical_segments(payload)
            self.assertNotIn("voice_id", segments[0])
            self.assertNotIn("voice_id", segments[1])

    def test_per_track_final_keeps_unambiguous_live_remote_voices(self):
        from canonical_transcript import canonical_segments
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            started = "2026-10-16T09:00:00Z"
            (root / "meta.json").write_text(json.dumps({"started": started}))
            (root / "transcript.json").write_text(json.dumps({"engine": "parakeet", "segments": [
                {"speaker": "them", "start_ms": 2000, "end_ms": 4000, "text": "First speaker"},
                {"speaker": "them", "start_ms": 6000, "end_ms": 8000, "text": "Second speaker"}]}))
            payload = {"status": "finished", "started_at": started, "recording_dir": directory,
                       "segments": [
                           {"source": "system", "timestamp": "2026-10-16T09:00:01Z",
                            "end_timestamp": "2026-10-16T09:00:05Z", "voice_id": "remote-2"},
                           {"source": "system", "timestamp": "2026-10-16T09:00:05Z",
                            "end_timestamp": "2026-10-16T09:00:09Z", "voice_id": "remote-1"}]}
            self.assertEqual([s.get("voice_id") for s in canonical_segments(payload)], ["remote-2", "remote-1"])

    def test_final_arriving_during_refresh_is_not_cached_as_already_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live.json"
            started = "2026-10-16T09:00:00Z"
            live.write_text(json.dumps({"version": 1, "source": "test", "meeting_id": "synthetic-race",
                "status": "finished", "started_at": started, "recording_dir": directory,
                "segments": [{"source": "microphone", "timestamp": started, "text": "Live"}]}))
            (root / "meta.json").write_text(json.dumps({"started": started}))
            def arriving_after_read(payload):
                (root / "transcript.json").write_text(json.dumps({"engine": "parakeet", "segments": [
                    {"speaker": "me", "start_ms": 0, "end_ms": 1000, "text": "Final"}]}))
                return None
            with patch.object(server, "capture_mentions"), patch.object(server, "RECOVERED_TRANSCRIPTS_ROOT", root):
                bridge = server.TranscriptState(live)
                with patch.object(server, "canonical_segments", side_effect=arriving_after_read):
                    bridge.refresh()
                self.assertEqual(bridge.snapshot()["segments"][0]["text"], "Live")
                bridge.refresh()
                self.assertEqual(bridge.snapshot()["segments"][0]["text"], "Final")

    def test_late_final_transcript_replaces_live_gibberish_without_live_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recording = root / "recording"
            recording.mkdir()
            live = root / "live.json"
            payload = {"version": 1, "source": "test", "meeting_id": "synthetic-en",
                       "status": "finished", "started_at": "2026-10-16T09:00:00Z",
                       "recording_dir": str(recording), "segments": [
                           {"source": "microphone", "timestamp": "2026-10-16T09:00:01Z",
                            "text": "ошибочное распознавание"}]}
            live.write_text(json.dumps(payload))
            (recording / "meta.json").write_text(json.dumps({"started": payload["started_at"]}))
            with patch.object(server, "capture_mentions"), patch.object(server, "RECOVERED_TRANSCRIPTS_ROOT", root):
                bridge = server.TranscriptState(live)
                bridge.refresh()
                self.assertEqual(bridge.snapshot()["segments"][0]["text"], "ошибочное распознавание")
                final = {"engine": "parakeet", "segments": [
                    {"speaker": "me", "start_ms": 1000, "end_ms": 2000, "text": "The project is on track."},
                    {"speaker": "them A", "start_ms": 2500, "end_ms": 4000, "text": "Let us review the schedule."}]}
                (recording / "transcript.json").write_text(json.dumps(final))
                bridge.refresh()
                segments = bridge.snapshot()["segments"]
                self.assertEqual([s["text"] for s in segments], ["The project is on track.", "Let us review the schedule."])
                self.assertEqual([s["source"] for s in segments], ["microphone", "system"])
                self.assertEqual(segments[1]["timestamp"], "2026-10-16T09:00:02.500+00:00")
                self.assertEqual(segments[1]["end_timestamp"], "2026-10-16T09:00:04+00:00")
                self.assertEqual(segments[1]["voice_id"], "remote-1")
                revision = bridge.snapshot()["revision"]
                bridge.refresh()
                self.assertEqual(bridge.snapshot()["revision"], revision)
                self.assertEqual(json.loads(live.read_text()), payload)

    def test_active_mismatched_or_invalid_final_never_replaces_live(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live.json"
            canonical = root / "transcript.json"
            payload = {"version": 1, "source": "test", "meeting_id": "synthetic-en",
                       "status": "recording", "started_at": "2026-10-16T09:00:00Z",
                       "recording_dir": str(root), "segments": [
                           {"source": "system", "timestamp": "2026-10-16T09:00:01Z", "text": "Live speech"}]}
            final = {"engine": "parakeet", "segments": [
                {"speaker": "me", "start_ms": 0, "end_ms": 1000, "text": "Different speech"}]}
            for status, started, content in [
                ("recording", payload["started_at"], json.dumps(final)),
                ("finished", "2026-10-15T09:00:00Z", json.dumps(final)),
                ("finished", payload["started_at"], "{unfinished"),
                ("finished", payload["started_at"], json.dumps({"segments": []})),
            ]:
                with self.subTest(status=status, started=started, content=content):
                    payload["status"] = status
                    live.write_text(json.dumps(payload))
                    canonical.write_text(content)
                    (root / "meta.json").write_text(json.dumps({"started": started}))
                    with patch.object(server, "capture_mentions"), patch.object(server, "RECOVERED_TRANSCRIPTS_ROOT", root):
                        bridge = server.TranscriptState(live)
                        bridge.refresh()
                        self.assertEqual([s["text"] for s in bridge.snapshot()["segments"]], ["Live speech"])
