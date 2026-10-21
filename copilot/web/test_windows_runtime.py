import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from recording_health import RecordingLocations, owner_alive


class WindowsRuntimeTests(unittest.TestCase):
    def test_codex_analysis_uses_the_chosen_model_and_stays_read_only(self):
        import server
        from test_ai_providers import chosen_codex
        with tempfile.TemporaryDirectory() as tmp, chosen_codex(tmp, server):
            session = server.CodexSession(Path(tmp) / "copilot.json")
            import ai_providers
            result = ai_providers.Result(0, '{"type":"item.completed","item":{"type":"agent_message","text":"FACT: Synthetic"}}', '')
            with patch.object(ai_providers, "_run", return_value=result) as run:
                self.assertEqual(session._run_ai("Synthetic input"), "FACT: Synthetic")
            args = run.call_args.args[0]
            self.assertEqual(args[args.index("-m") + 1], "fixture-model")
            self.assertIn('default_permissions="meetontrack"', args)
            self.assertNotIn('"write"', " ".join(args))
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

    def test_health_names_the_installed_version(self):
        # MEETONTRACK-65: the launcher reuses a running server only for its own version.
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        import server
        with patch.dict(server.UPDATES.identity, {"version": "9.9.9-windows-beta.1"}):
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                connection.request("GET", "/api/health")
                body = json.loads(connection.getresponse().read())
                connection.close()
            finally:
                httpd.shutdown()
                httpd.server_close()
        self.assertEqual(body, {"ok": True, "service": "meeting-copilot", "version": "9.9.9-windows-beta.1"})

    def test_windows_liveness_never_calls_os_kill(self):
        with patch("recording_health.os.name", "nt"), patch("recording_health.os.kill") as kill, \
             patch("recording_health.windows_owner_alive", return_value=True, create=True):
            self.assertTrue(owner_alive(1234))
            kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
