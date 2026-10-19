"""Regression checks for meeting report delivery and retries."""

import json
import subprocess
import sys
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
        connector = patch.object(self.archive.delivery_settings, "executable", return_value="/fake/gws-personal")
        connector.start()
        self.addCleanup(connector.stop)
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
        with patch.object(self.archive, "_upload_drive_report_gws", return_value=("auth_required", {})), \
             patch("archive.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{"id":"sent"}', "")) as run:
            result = self.archive.deliver(self.detail, report)
            self.assertEqual(result["drive_status"], "auth_required")
            self.assertEqual(result["mail_status"], "sent")
            self.assertTrue(any("gmail" in call.args[0] for call in run.call_args_list))
            run.reset_mock()
            self.archive.deliver(self.detail, report, previous=result)
            self.assertFalse(any("gmail" in call.args[0] for call in run.call_args_list))

    def telegram_setup(self):
        settings = {"email_enabled": False, "drive_enabled": False,
                    "telegram_enabled": True, "telegram_account": "synthetic",
                    "telegram_config": str(self.config / "telegram.env")}
        (self.config / "telegram.env").write_text("# Synthetic fixture: no credentials")
        (self.config / "delivery.json").write_text(json.dumps(settings))

    def test_telegram_uses_own_runtime_and_does_not_require_drive(self):
        self.telegram_setup()
        with patch("archive.subprocess.run", return_value=subprocess.CompletedProcess(
                [], 0, '{"ok":true,"status":"sent","message_id":42}', "")) as run:
            result = self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)})
        self.assertEqual(result["telegram_status"], "sent")
        self.assertEqual(result["telegram_message_id"], 42)
        self.assertEqual(run.call_args.args[0][0], sys.executable)

    def test_telegram_lost_acknowledgement_does_not_automatically_repeat(self):
        self.telegram_setup()
        for error in (subprocess.TimeoutExpired([], 180), ValueError("broken json")):
            with patch("archive.subprocess.run", side_effect=error) as run:
                result = self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)})
                self.assertEqual(result["telegram_status"], "unknown")
                run.reset_mock()
                self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)}, previous=result)
                run.assert_not_called()

    def test_telegram_missing_dependency_and_invalid_ack_are_not_sent(self):
        self.telegram_setup()
        for payload, expected in (({"status": "dependency_missing"}, "dependency_missing"),
                                  ({"ok": True, "status": "sent"}, "unknown")):
            with patch("archive.subprocess.run", return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(payload), "")):
                result = self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)})
            self.assertEqual(result["telegram_status"], expected)

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

    def test_named_gws_account_delivers_without_gog(self):
        report = {"pdf_path": str(self.pdf)}
        links = {
            "drive_folder_url": "https://drive.google.com/drive/folders/test",
            "drive_html_url": "https://drive.google.com/file/d/html/view",
            "drive_pdf_url": "https://drive.google.com/file/d/pdf/view",
        }
        with patch.object(self.archive, "_upload_drive_report_gws", return_value=("uploaded", links)), \
             patch.object(self.archive, "_gws_call", return_value={"id": "sent-id"}) as gws:
            result = self.archive.deliver(self.detail, report)
        self.assertEqual(result["drive_status"], "uploaded")
        self.assertEqual(result["mail_status"], "sent")
        self.assertEqual(result["gmail_message_id"], "sent-id")
        self.assertEqual(result["drive_pdf_url"], links["drive_pdf_url"])
        self.assertEqual(gws.call_args.args[:2], ("gmail", "+send"))

    def test_missing_drive_links_are_repaired_without_resending_successes(self):
        report_dir = self.archive.reports_root / "meeting-1"
        report_dir.mkdir()
        (report_dir / "report.json").write_text(json.dumps({
            "generated_at": datetime.now().astimezone().isoformat(),
            "pdf_path": str(self.pdf), "drive_status": "uploaded",
            "mail_status": "sent", "telegram_status": "sent",
        }), encoding="utf-8")
        with patch.object(self.archive, "report_detail", return_value=self.detail), \
             patch.object(self.archive, "deliver", return_value={
                 "drive_status": "uploaded", "mail_status": "sent", "telegram_status": "sent",
             }) as deliver:
            self.assertEqual(self.archive.retry_pending_deliveries(), 1)
        self.assertEqual(deliver.call_args.kwargs["previous"]["mail_status"], "sent")
        self.assertEqual(deliver.call_args.kwargs["previous"]["telegram_status"], "sent")

    def test_delivery_diagnostics_never_persist_raw_output(self):
        result = subprocess.CompletedProcess([], 1, "private meeting text",
                                             "insufficient authentication scopes token=secret")
        error = self.archive._delivery_failure("gws", result)
        self.assertEqual(error, {"provider": "gws", "reason": "permission_missing", "exit_code": 1})
        self.assertNotIn("secret", json.dumps(error))

    def test_gws_failure_retains_safe_diagnostics(self):
        error = {}
        with patch("archive.shutil.which", return_value="/fake/gws"), \
             patch("archive.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 1, "", "invalid_grant private-details")):
            self.assertIsNone(self.archive._gws_call("gmail", "+send", diagnostics=error))
        self.assertEqual(error["reason"], "authorization_expired")
        self.assertEqual(error["provider"], "gws")

    def test_failed_send_preserves_diagnostics_without_unsafe_fallback(self):
        with patch("archive.subprocess.run", return_value=subprocess.CompletedProcess(
                 [], 1, "", "private error details")) as run:
            result = self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)}, previous={
                "drive_status": "uploaded", "drive_folder_url": "https://drive.google.com/drive/folders/a",
                "drive_pdf_url": "https://drive.google.com/file/d/b/view",
                "drive_html_url": "https://drive.google.com/file/d/c/view",
            })
        self.assertEqual(result["mail_status"], "failed")
        self.assertEqual(result["mail_error"], {"provider": "gws", "reason": "client_failed", "exit_code": 1})
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][0], "/fake/gws-personal")

    def test_attachment_and_upload_run_inside_file_directory(self):
        for flag in ("--attach", "--upload"):
            with patch("archive.subprocess.run", return_value=subprocess.CompletedProcess([], 0, '{"id":"ok"}', "")) as run:
                self.archive._gws_call("gmail", "+send", flag, str(self.pdf))
            self.assertEqual(run.call_args.kwargs["cwd"], str(self.pdf.resolve().parent))

    def test_disabled_channels_never_call_providers(self):
        settings = json.loads((self.config / "delivery.json").read_text())
        settings.update(email_enabled=False, drive_enabled=False, telegram_enabled=False)
        (self.config / "delivery.json").write_text(json.dumps(settings))
        with patch("archive.subprocess.run") as run:
            self.archive.deliver(self.detail, {"pdf_path":str(self.pdf)})
        run.assert_not_called()

    def test_enabling_email_does_not_backfill_old_meetings(self):
        settings = json.loads((self.config / "delivery.json").read_text())
        settings.update(email_enabled=True, drive_enabled=False, email_enabled_at=(datetime.now().astimezone()+timedelta(days=1)).isoformat())
        (self.config / "delivery.json").write_text(json.dumps(settings))
        with patch("archive.subprocess.run") as run:
            self.archive.deliver(self.detail, {"pdf_path":str(self.pdf)})
        run.assert_not_called()

    def test_unknown_send_is_not_automatically_repeated(self):
        with patch("archive.subprocess.run") as run:
            self.archive.deliver(self.detail, {"pdf_path":str(self.pdf)}, previous={
                "mail_status":"unknown", "drive_status":"uploaded",
                "drive_folder_url":"https://drive.google.com/drive/folders/a",
                "drive_pdf_url":"https://drive.google.com/file/d/b/view", "drive_html_url":"https://drive.google.com/file/d/c/view"})
        run.assert_not_called()

    def test_receipt_prevents_duplicate_after_report_regeneration(self):
        folder = self.archive.reports_root / "meeting-1"
        folder.mkdir()
        (folder / "delivery-receipts.json").write_text(json.dumps({
            "mail_status": "sent", "gmail_message_id": "acknowledged-id"}))
        with patch("archive.subprocess.run") as run:
            result = self.archive.deliver(self.detail, {"pdf_path": str(self.pdf)},
                previous={"mail_status": "failed", "mail_error": {"reason": "client_failed"}},
                channels={"email"})
        run.assert_not_called()
        self.assertEqual(result["mail_status"], "sent")
        self.assertEqual(result["gmail_message_id"], "acknowledged-id")
        self.assertEqual(result["mail_error"], {})

    def test_revised_report_refreshes_drive_without_resending_mail(self):
        detail = {
            **self.detail,
            "duration_seconds": 300,
            "transcript": [{"speaker": "Ana", "text": "Pilot approved"}],
            "journal": [], "frames": [], "meeting_chat": [], "participants": [],
            "report": {
                "source_signature": "outdated", "drive_status": "uploaded",
                "mail_status": "sent", "telegram_status": "sent",
            },
        }

        def print_pdf(_html, pdf):
            pdf.write_bytes(b"%PDF-test")

        def delivery_result(_detail, _report, *, previous):
            on_disk = json.loads((self.archive.reports_root / "meeting-1" / "report.json").read_text())
            self.assertEqual(on_disk["mail_status"], "sent")
            self.assertEqual(on_disk["telegram_status"], "sent")
            return {"drive_status": "uploaded", "mail_status": "sent", "telegram_status": "sent"}

        with patch.object(self.archive, "report_detail", return_value=detail), \
             patch.object(self.archive, "_print_pdf", side_effect=print_pdf), \
             patch.object(self.archive, "deliver", side_effect=delivery_result) as deliver:
            self.archive.generate_report("meeting-1")
        previous = deliver.call_args.kwargs["previous"]
        self.assertEqual(previous["drive_status"], "pending")
        self.assertEqual(previous["mail_status"], "sent")
        self.assertEqual(previous["telegram_status"], "sent")


if __name__ == "__main__":
    unittest.main()
