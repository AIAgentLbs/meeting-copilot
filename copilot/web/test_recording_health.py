import json
import os
import subprocess
import tempfile
import time
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from recording_health import RecordingHealth, RecordingLocations, RecognitionGuard, epoch


class RecordingHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.config = self.home / "config.json"
        self.legacy = self.home / "legacy"
        self.locations = RecordingLocations(self.config, self.legacy, self.home)
        self.directory = self.home / "Recordings" / "call"
        self.directory.mkdir(parents=True)
        self.marker = self.directory / ".recording.json"
        self.start = "2026-10-02T11:37:36Z"
        self.marker.write_text(json.dumps({"pid": os.getpid(), "started": self.start,
            "files": {"mic": "mic.caf", "system": "system.caf"}}))
        for source in ("mic", "system"):
            (self.directory / f"{source}.caf").write_bytes(b"audio")
        self.live = self.home / "live.json"
        self.payload = {"meeting_id": "same-call", "started_at": self.start,
                        "status": "overloaded", "updated_at": self.start}
        self.live.write_text(json.dumps(self.payload))
        self.now = epoch(self.start) + 200
        self.health = RecordingHealth(self.locations)
        self.runner = Mock()
        self.guard = RecognitionGuard(self.health, self.live, self.home / "guard.json",
                                      Path("/test/Capture"), self.runner)

    def grow(self, source=None):
        for kind in ([source] if source else ["mic", "system"]):
            with (self.directory / f"{kind}.caf").open("ab") as f:
                f.write(b"more audio")

    def test_finds_native_default_and_custom_and_legacy_roots(self):
        self.assertEqual(self.locations.active(self.start)["directory"], str(self.directory.resolve()))
        custom = self.home / "custom"
        self.config.write_text(json.dumps({"recordings_dir": str(custom)}))
        self.assertEqual(self.locations.roots(), [p.resolve() for p in (custom, self.home / "Recordings", self.legacy)])

    def test_clock_mismatch_dead_owner_and_bool_pid_are_not_active(self):
        self.assertIsNone(self.locations.active("2026-10-01T00:00:00Z"))
        for pid in (True, -1, 999999999):
            marker = json.loads(self.marker.read_text())
            marker["pid"] = pid
            self.marker.write_text(json.dumps(marker))
            self.assertIsNone(self.locations.active(self.start))

    def test_track_path_cannot_escape_recording_roots(self):
        self.marker.write_text(json.dumps({"pid": os.getpid(), "started": self.start,
            "files": {"mic": "../private.caf", "system": "/tmp/system.caf"}}))
        self.assertIsNone(self.locations.active(self.start))

    def test_first_observation_does_not_claim_recording(self):
        sample = self.health.sample(self.payload, self.now)
        self.assertEqual(sample["state"], "verifying")
        self.assertFalse(sample["audio_recording"])
        self.grow()
        self.assertTrue(self.health.sample(self.payload, self.now + 5)["audio_recording"])

    def test_one_stalled_track_is_failure_not_recording(self):
        self.health.sample(self.payload, self.now)
        self.grow()
        self.health.sample(self.payload, self.now + 5)
        self.grow("mic")
        self.assertEqual(self.health.sample(self.payload, self.now + 51)["state"], "stalled")

    def test_one_missing_track_never_claims_complete_audio_recording(self):
        marker = json.loads(self.marker.read_text())
        del marker["files"]["system"]
        self.marker.write_text(json.dumps(marker))
        self.health.sample(self.payload, self.now)
        self.grow("mic")
        sample = self.health.sample(self.payload, self.now + 5)
        self.assertFalse(sample["audio_recording"])
        self.assertEqual(sample["state"], "stalled")
        self.guard.tick(now=self.now + 5)
        self.runner.assert_not_called()

    def test_missing_caf_is_immediate_failure_not_eventual_verified_recording(self):
        (self.directory / "system.caf").unlink()
        self.assertEqual(self.health.sample(self.payload, self.now)["state"], "stalled")

    def test_corrupt_retry_metadata_and_non_string_status_do_not_crash(self):
        self.guard.state_file.write_text(json.dumps({"identity": "same-call:" + self.start, "attempts": None}))
        self.payload["status"] = ["invalid"]
        self.live.write_text(json.dumps(self.payload))
        self.guard.tick(now=self.now)
        self.grow()
        self.guard.tick(now=self.now + 5)
        self.runner.assert_not_called()

    def test_explicit_owner_retry_can_renew_exhausted_budget(self):
        self.guard.tick(now=self.now)
        for delta in (5, 96, 187, 278):
            self.grow()
            self.guard.tick(now=self.now + delta)
        self.assertEqual(self.runner.call_count, 3)
        self.grow()
        self.guard.tick(now=self.now + 279, manual_meeting_id="same-call")
        self.assertEqual(self.runner.call_count, 4)

    def test_overload_resumes_only_after_growth_same_meeting(self):
        self.guard.tick(now=self.now)
        self.runner.assert_not_called()
        self.grow()
        result = self.guard.tick(now=self.now + 5)
        self.assertEqual(result["state"], "recovering")
        self.runner.assert_called_once_with(["/test/Capture", "record", "resume"],
            capture_output=True, text=True, timeout=8, check=True)

    def test_quiet_legacy_recording_does_not_restart(self):
        self.payload["status"] = "recording"
        self.live.write_text(json.dumps(self.payload))
        self.guard.tick(now=self.now)
        self.grow()
        self.guard.tick(now=self.now + 5)
        self.runner.assert_not_called()

    def test_explicit_decoder_heartbeat_stall_recovers(self):
        self.payload.update(status="recording", recognition_progress_at=self.start)
        self.live.write_text(json.dumps(self.payload))
        self.guard.tick(now=self.now)
        self.grow()
        self.guard.tick(now=self.now + 5)
        self.runner.assert_called_once()

    def test_pause_missing_model_and_finished_are_never_resumed(self):
        for status in ("paused", "model_missing", "finished", "idle"):
            self.payload["status"] = status
            self.live.write_text(json.dumps(self.payload))
            self.guard.tick(now=self.now)
            self.grow()
            self.guard.tick(now=self.now + 5)
        self.runner.assert_not_called()

    def test_retry_budget_and_cooldown_survive_guard_restart(self):
        self.guard.tick(now=self.now)
        for delta in (5, 10, 96, 187, 278):
            self.grow()
            self.guard.tick(now=self.now + delta)
        self.assertEqual(self.runner.call_count, 3)
        result = json.loads(self.guard.state_file.read_text())
        self.assertEqual(result["reason"], "recognition_retries_exhausted")
        restarted = RecognitionGuard(self.health, self.live, self.guard.state_file,
                                     Path("/test/Capture"), self.runner)
        self.grow()
        restarted.tick(now=self.now + 279)
        self.assertEqual(self.runner.call_count, 3)

    def test_new_meeting_does_not_inherit_old_retries(self):
        self.guard.tick(now=self.now)
        self.grow()
        self.guard.tick(now=self.now + 5)
        self.payload["meeting_id"] = "new-call"
        self.live.write_text(json.dumps(self.payload))
        self.grow()
        self.guard.tick(now=self.now + 10)
        self.assertEqual(self.runner.call_count, 2)

    def test_stale_tab_never_resumes_another_call(self):
        self.guard.tick(now=self.now)
        self.grow()
        with self.assertRaises(ValueError):
            self.guard.tick(now=self.now + 5, manual_meeting_id="old-call")
        self.runner.assert_not_called()

    def test_failed_command_records_action_required_and_keeps_cooldown(self):
        self.runner.side_effect = subprocess.TimeoutExpired("Capture", 8)
        self.guard.tick(now=self.now)
        self.grow()
        result = self.guard.tick(now=self.now + 5)
        self.assertEqual(result["reason"], "recognition_resume_failed")
        self.grow()
        self.assertEqual(self.guard.tick(now=self.now + 10)["reason"], "recognition_resume_failed")
        self.runner.assert_called_once()

    def test_notifications_are_changes_only_and_require_verified_recovery(self):
        notices = Mock()
        self.guard.notifier = notices
        (self.directory / "system.caf").unlink()
        self.guard.tick(now=self.now)
        self.guard.tick(now=self.now + 5)
        notices.assert_called_once_with("audio_track_stalled")
        self.marker.unlink()
        self.guard.tick(now=self.now + 10)
        self.assertEqual(notices.call_count, 1)  # no "recovered" merely because the call stopped

    def test_real_http_resume_and_stale_tab_use_only_validated_native_command(self):
        import server
        self.guard.tick(now=time.time())
        self.grow()
        with patch.object(server, "RECOGNITION_GUARD", self.guard):
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            worker = threading.Thread(target=httpd.serve_forever, daemon=True)
            worker.start()
            try:
                client = HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                for meeting, status in (("old-call", 400), ("same-call", 200), ("same-call", 200)):
                    client.request("POST", "/api/recognition/resume", json.dumps({"meeting_id": meeting}),
                                   {"Content-Type": "application/json"})
                    response = client.getresponse()
                    self.assertEqual(response.status, status)
                    response.read()
                self.runner.assert_called_once()
                client.close()
            finally:
                httpd.shutdown()
                httpd.server_close()
                worker.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
