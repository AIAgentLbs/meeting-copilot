import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recording_health import RecordingLocations, owner_alive


class WindowsRuntimeTests(unittest.TestCase):
    def test_codex_analysis_explicitly_uses_current_model_and_preserves_windows_path(self):
        import server
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            session = server.CodexSession(Path(tmp) / "copilot.json")
            result = SimpleNamespace(stdout='{"type":"item.completed","item":{"type":"agent_message","text":"FACT: Synthetic"}}', stderr='', returncode=0)
            with patch.object(server.subprocess, "run", return_value=result) as run:
                self.assertEqual(session._run_codex("Synthetic input"), "FACT: Synthetic")
            args = run.call_args.args[0]
            self.assertIn("--model", args)
            self.assertEqual(args[args.index("--model") + 1], "gpt-6.1-sol")
            self.assertIn("--sandbox", args)
            self.assertEqual(args[args.index("--sandbox") + 1], "read-only")
            self.assertIn("--ask-for-approval", args)
            self.assertEqual(args[args.index("--ask-for-approval") + 1], "never")

    def test_wav_recording_marker_is_observed_without_changing_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / "recordings"
            recording = root / "fixture"
            recording.mkdir(parents=True)
            config = home / "config.json"
            config.write_text(json.dumps({"recordings_dir": str(root)}))
            marker = {"pid": os.getpid(), "started": "2026-01-01T12:00:00Z",
                      "files": {"mic": "mic.wav", "system": "system.wav"}}
            (recording / ".recording.json").write_text(json.dumps(marker))
            for source in ("mic", "system"):
                (recording / (source + ".wav")).write_bytes(b"synthetic-audio")
            active = RecordingLocations(config, root, home).active(marker["started"])
            self.assertIsNotNone(active)
            self.assertEqual(set(active["tracks"]), {"mic", "system"})

    def test_windows_liveness_never_calls_os_kill(self):
        with patch("recording_health.os.name", "nt"), patch("recording_health.os.kill") as kill, \
             patch("recording_health.windows_owner_alive", return_value=True, create=True):
            self.assertTrue(owner_alive(1234))
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
