"""Regression checks for meeting report delivery and retries."""

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from archive import MeetingArchive


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.config = root / "config"
        self.config.mkdir()
        self.archive = MeetingArchive(
            root / "recordings", root / "archive", root / "reports", self.config
        )
        (self.config / "delivery.json").write_text(json.dumps({
            "email_to": "owner@example.com",
            "google_account": "owner@example.com",
            "drive_folder_id": "folder-id",
        }), encoding="utf-8")
        self.detail = {
            "meeting_id": "meeting-1", "title": "Test call",
            "started_at": datetime.now().astimezone().isoformat(),
            "ended_at": (datetime.now().astimezone() - timedelta(minutes=5)).isoformat(),
            "status": "finished",
        }
        self.pdf = root / "meeting-report.pdf"
        self.pdf.write_bytes(b"%PDF-test")

    def test_email_is_attempted_when_drive_requires_auth(self):
        report = {"pdf_path": str(self.pdf)}
        with patch("archive.shutil.which", return_value="/usr/local/bin/gog"), \
             patch.object(self.archive, "_upload_drive_report", return_value=("auth_required", {})), \
             patch("archive.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "{}", "")) as run:
            result = self.archive.deliver(self.detail, report)
            self.assertEqual(result["drive_status"], "auth_required")
            self.assertEqual(result["mail_status"], "sent")
            self.assertTrue(any("gmail" in call.args[0] for call in run.call_args_list))
            run.reset_mock()
            self.archive.deliver(self.detail, report, previous=result)
            self.assertFalse(any("gmail" in call.args[0] for call in run.call_args_list))

    def test_failed_delivery_retries_once_then_waits(self):
        report_dir = self.archive.reports_root / "meeting-1"
        report_dir.mkdir()
        report_path = report_dir / "report.json"
        report_path.write_text(json.dumps({
            "generated_at": datetime.now().astimezone().isoformat(),
            "pdf_path": str(self.pdf),
            "drive_status": "auth_required", "mail_status": "auth_required",
        }), encoding="utf-8")
        with patch.object(self.archive, "report_detail", return_value=self.detail), \
             patch.object(self.archive, "deliver", return_value={
                 "drive_status": "uploaded", "mail_status": "sent"
             }) as deliver:
            self.assertEqual(self.archive.retry_pending_deliveries(), 1)
            self.assertEqual(self.archive.retry_pending_deliveries(), 0)
            deliver.assert_called_once()
        stored = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["mail_status"], "sent")
        self.assertTrue(stored["delivery_retry_at"])
        self.assertEqual(self.archive.delivery_health()["mail_pending"], 0)

    def test_active_meeting_is_not_eligible_for_delivery(self):
        self.detail["status"] = "recording"
        self.assertFalse(self.archive._ready_for_delivery(self.detail))
        self.detail["status"] = "finished"
        marker = self.archive.recordings_root / "chunk" / ".recording.json"
        marker.parent.mkdir(parents=True)
        marker.write_text("{}", encoding="utf-8")
        self.assertFalse(self.archive._ready_for_delivery(self.detail))


if __name__ == "__main__":
    unittest.main()
