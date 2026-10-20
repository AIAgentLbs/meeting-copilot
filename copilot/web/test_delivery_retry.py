import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from archive import MeetingArchive
from delivery_retry import DeliveryRetry


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.archive=MeetingArchive(root/"recordings",root/"archive",root/"reports",root/"config")
        self.archive.config_root.mkdir()
        (self.archive.config_root/"delivery.json").write_text(json.dumps({"email_enabled":True,"email_to":"a@example.com"}))
        directory=self.archive.reports_root/"call-1"
        directory.mkdir()
        (directory/"meeting-report.pdf").write_bytes(b"%PDF-test")
        self.path=directory/"report.json"
        self.path.write_text(json.dumps({"mail_status":"failed","generated_at":datetime.now(timezone.utc).isoformat()}))
        self.retry=DeliveryRetry(self.archive)
        self.detail={"meeting_id":"call-1","status":"finished", "ended_at":(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()}

    def run_retry(self, confirm=False):
        with patch.object(self.archive,"report_detail",return_value=self.detail), \
             patch.object(self.archive,"deliver",return_value={"mail_status":"sent","gmail_message_id":"test-id"}) as send:
            self.retry._run("call-1","request-0123456789",{"email"},confirm)
        return send

    def test_success_request_is_idempotent(self):
        self.run_retry().assert_called_once()
        self.run_retry().assert_not_called()
        self.assertEqual(json.loads(self.path.read_text())["mail_status"],"sent")

    def test_sent_message_requires_confirmation(self):
        self.path.write_text(json.dumps({"mail_status":"sent"}))
        self.run_retry().assert_not_called()
        self.assertEqual(self.retry.snapshot()["error"],"resend_confirmation_required")

    def test_disabled_channel_cannot_be_retried(self):
        (self.archive.config_root/"delivery.json").write_text('{"email_enabled":false}')
        self.run_retry().assert_not_called()
        self.assertEqual(self.retry.snapshot()["error"],"channel_disabled")

    def test_active_recording_cannot_be_retried(self):
        self.detail["status"]="recording"
        self.run_retry().assert_not_called()
        self.assertEqual(self.retry.snapshot()["error"],"meeting_not_finished")

    def test_invalid_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.retry.submit({"meeting_id":"../outside","request_id":"request-0123456789","channels":["email"]})


if __name__ == "__main__":
    unittest.main()
