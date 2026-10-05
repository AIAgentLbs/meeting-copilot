import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class RecoveredTranscriptTests(unittest.TestCase):
    def test_recovery_survives_exporter_refresh_and_is_meeting_scoped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "live.json"
            original = {"source": "microphone", "timestamp": "2026-10-01T08:00:00Z", "text": "Начало"}
            recovered = {"source": "system", "timestamp": "2026-10-01T08:01:00Z", "end_timestamp": "2026-10-01T08:01:05Z", "text": "Продолжение"}
            payload = {"version": 1, "source": "test", "meeting_id": "test-one", "status": "overloaded", "segments": [original]}
            live.write_text(json.dumps(payload))
            (root / "test-one.json").write_text(json.dumps({"meeting_id": "test-one", "segments": [original, recovered]}))
            with patch.object(server, "RECOVERED_TRANSCRIPTS_ROOT", root):
                bridge = server.TranscriptState(live)
                bridge.refresh()
                self.assertEqual(len(bridge.snapshot()["segments"]), 2)
                self.assertEqual(bridge.snapshot()["segments"][1]["end_timestamp"], recovered["end_timestamp"])
                bridge.refresh()
                self.assertEqual(len(bridge.snapshot()["segments"]), 2)
                payload["meeting_id"] = "test-two"
                payload["status"] = "recording"
                live.write_text(json.dumps(payload))
                bridge.refresh()
                self.assertEqual(len(bridge.snapshot()["segments"]), 1)
