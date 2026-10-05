"""Synthetic, offline delivery checks: no real mail, uploads or report data."""

import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from archive import MeetingArchive
from delivery_health import DeliveryHealth


class DeliveryHealthTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.reports = self.root / "reports"
        self.reports.mkdir()
        self.state = self.root / "config" / "delivery-health.json"
        self.monitor = DeliveryHealth(self.reports, self.state)
        self.now = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
        self.settings = {"drive_folder_id": "folder", "email_to": "synthetic@example.test",
                         "telegram_account": "test", "telegram_config": "/synthetic/config"}
        self.report = {"generated_at": (self.now - timedelta(hours=1)).isoformat(),
                       "drive_status": "uploaded", "mail_status": "sent", "telegram_status": "sent",
                       "drive_folder_url": "https://drive.google.com/drive/folders/folder",
                       "drive_html_url": "https://drive.google.com/file/d/html/view",
                       "drive_pdf_url": "https://drive.google.com/file/d/pdf/view"}
        self.save()

    def save(self, meeting="test"):
        path = self.reports / meeting / "report.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(self.report), encoding="utf-8")

    def refresh(self, offset=0):
        return self.monitor.refresh(self.settings, now=self.now + timedelta(minutes=offset))

    def test_healthy_and_unconfigured_channels_are_silent(self):
        self.assertEqual(self.refresh()["notifications"], [])
        self.assertEqual(self.refresh(60)["notifications"], [])
        health = self.monitor.refresh({}, now=self.now)
        self.assertEqual(health["state"], "not_configured")
        self.assertEqual(health["notifications"], [])

    def test_each_channel_is_independently_monitored_without_email(self):
        self.settings.pop("email_to")
        self.report.update(drive_status="failed", telegram_status="auth_required")
        self.save()
        health = self.refresh()
        self.assertEqual(health["issue_count"], 2)
        self.assertEqual(health["channels"]["gmail"]["state"], "not_configured")
        self.assertEqual({e["channel"] for e in health["notifications"]}, {"drive", "telegram"})

    def test_repeated_checks_and_restart_do_not_duplicate_events(self):
        self.report["mail_status"] = "failed"
        self.save()
        first = self.refresh()
        self.assertEqual(len(first["notifications"]), 1)
        self.monitor = DeliveryHealth(self.reports, self.state)
        self.assertEqual(self.refresh(1)["notifications"], first["notifications"])
        self.monitor.acknowledge(first["notifications"][0]["id"])
        self.assertEqual(self.refresh(2)["notifications"], [])
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_reason_change_and_actual_recovery_are_announced_once(self):
        self.report["telegram_status"] = "failed"
        self.save()
        self.refresh()
        self.report["telegram_status"] = "auth_required"
        self.save()
        health = self.refresh(1)
        self.assertEqual([e["kind"] for e in health["notifications"]], ["failed", "action_required"])
        self.report["telegram_status"] = "sent"
        self.save()
        recovered = self.refresh(2)
        self.assertEqual(recovered["notifications"][-1]["kind"], "recovered")
        self.assertEqual(self.refresh(3)["notifications"], recovered["notifications"])

    def test_expired_failure_is_not_false_recovery_and_remains_visible(self):
        self.report["mail_status"] = "failed"
        self.save()
        self.refresh()
        health = self.refresh(3 * 24 * 60)
        self.assertEqual(health["notifications"][-1]["reason"], "retry_expired")
        self.assertEqual(health["channels"]["gmail"]["state"], "action_required")
        self.assertFalse(any(e["kind"] == "recovered" for e in health["notifications"]))

    def test_disabling_channel_or_removing_report_does_not_claim_recovery(self):
        self.report["mail_status"] = "failed"
        self.save()
        self.refresh()
        self.settings.pop("email_to")
        self.assertFalse(any(e["kind"] == "recovered" for e in self.refresh()["notifications"]))
        (self.reports / "test" / "report.json").unlink()
        self.assertFalse(any(e["kind"] == "recovered" for e in self.refresh()["notifications"]))

    def test_old_report_can_recover_after_retry_window_ends(self):
        self.report["mail_status"] = "failed"
        self.save()
        self.refresh()
        self.refresh(3 * 24 * 60)
        self.report["mail_status"] = "sent"
        self.save()
        health = self.refresh(3 * 24 * 60 + 1)
        self.assertEqual(health["notifications"][-1]["kind"], "recovered")
        self.assertEqual(len(self.refresh(3 * 24 * 60 + 2)["notifications"]), len(health["notifications"]))

    def test_install_does_not_announce_unobserved_historical_failures(self):
        self.report.update(mail_status="auth_required", generated_at=(self.now - timedelta(days=10)).isoformat())
        self.save()
        self.assertEqual(self.refresh()["notifications"], [])
        self.assertEqual(self.refresh()["issue_count"], 0)

    def test_pending_grace_and_active_call_are_not_failures(self):
        self.report.update(generated_at=self.now.isoformat(), mail_status="pending")
        self.save()
        self.assertEqual(self.refresh()["notifications"], [])
        self.assertEqual(self.refresh(16)["notifications"][0]["reason"], "retry_overdue")
        self.report.update(drive_status="waiting_for_end", mail_status="waiting_for_end", telegram_status="waiting_for_end")
        self.save()
        health = self.refresh(17)
        self.assertEqual(health["state"], "waiting")
        self.assertFalse(any(e["kind"] == "recovered" for e in health["notifications"]))

    def test_pending_retry_does_not_hide_later_recovery(self):
        self.report["mail_status"] = "failed"
        self.save()
        self.refresh()
        self.report.update(mail_status="pending", generated_at=self.now.isoformat())
        self.save()
        self.assertEqual(len(self.refresh(1)["notifications"]), 1)
        self.report["mail_status"] = "sent"
        self.save()
        self.assertEqual(self.refresh(2)["notifications"][-1]["kind"], "recovered")

    def test_drive_links_and_local_only_destination(self):
        self.report["drive_pdf_url"] = "https://drive.google.com.evil.test/file/d/pdf/view"
        self.save()
        self.assertEqual(self.refresh()["channels"]["drive"]["issues"][0]["reason"], "links_missing")
        self.settings.pop("drive_folder_id")
        self.settings["drive_local_path"] = "/synthetic/local"
        self.assertEqual(self.refresh()["channels"]["drive"]["state"], "sent")

    def test_corrupt_metadata_and_naive_timestamp_are_safe(self):
        (self.reports / "test" / "report.json").write_text("{broken", encoding="utf-8")
        self.assertEqual(self.refresh()["issue_count"], 3)
        self.report["generated_at"] = datetime.now().isoformat()
        self.save()
        self.assertEqual(self.monitor.snapshot(self.settings)["issue_count"], 0)

    def test_ack_does_not_swallow_future_events_or_race_with_new_failure(self):
        self.report["mail_status"] = "failed"
        self.save()
        first_id = self.refresh()["notifications"][-1]["id"]
        self.report["telegram_status"] = "failed"
        self.save()
        second_id = self.refresh()["notifications"][-1]["id"]
        self.monitor.acknowledge(first_id)
        self.assertEqual([e["id"] for e in self.refresh()["notifications"]], [second_id])
        self.monitor.acknowledge(999999)
        self.report["telegram_status"] = "sent"
        self.save()
        self.assertEqual(len(self.refresh()["notifications"]), 1)
        for invalid in (-1, True, "1", None):
            with self.assertRaises(ValueError):
                self.monitor.acknowledge(invalid)

    def test_health_contains_no_addresses_or_meeting_contents(self):
        self.report.update(title="PRIVATE_TITLE", body="PRIVATE_CONTENT", mail_status="failed")
        self.save()
        rendered = json.dumps(self.refresh())
        for secret in ("PRIVATE_TITLE", "PRIVATE_CONTENT", "synthetic@example.test"):
            self.assertNotIn(secret, rendered)

    def test_http_health_and_ack_preserve_origin_guard(self):
        import server
        config = self.root / "config"
        config.mkdir(exist_ok=True)
        (config / "delivery.json").write_text(json.dumps(self.settings), encoding="utf-8")
        archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.reports, config)
        self.report["mail_status"] = "failed"
        self.report["generated_at"] = datetime.now().astimezone().isoformat()
        self.save()
        archive.check_delivery_health()
        with patch.object(server, "ARCHIVE", archive):
            http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            worker = threading.Thread(target=http.serve_forever, daemon=True)
            worker.start()
            try:
                base = f"http://127.0.0.1:{http.server_port}"
                with urlopen(base + "/api/delivery") as response:
                    health = json.load(response)["delivery"]
                through = health["notifications"][-1]["id"]
                request = Request(base + "/api/delivery/ack", data=json.dumps({"through": through}).encode(),
                                  headers={"Content-Type": "application/json", "Origin": base})
                with urlopen(request) as response:
                    self.assertEqual(json.load(response)["delivery"]["notifications"], [])
                request.add_header("Origin", "https://untrusted.example.test")
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 403)
                error.exception.close()
            finally:
                http.shutdown()
                http.server_close()
                worker.join(2)


if __name__ == "__main__":
    unittest.main()
