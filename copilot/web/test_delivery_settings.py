import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from delivery_settings import DeliverySettings, enabled


class DeliverySettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = DeliverySettings(Path(self.temp.name))
        self.settings.passwords = Mock()

    def test_new_install_is_local_only(self):
        value = self.settings.snapshot()
        for channel in ("email", "drive", "telegram"):
            self.assertFalse(value[channel + "_enabled"])
        self.assertEqual(value["email_provider"], "smtp")

    def test_status_does_not_wait_for_slow_archive_delivery(self):
        result = []
        finished = threading.Event()
        def read_status():
            try:
                result.append(self.settings.snapshot())
            finally:
                finished.set()
        with patch.object(self.settings, "profiles", return_value=[]), patch.object(self.settings, "own_google_status", return_value={}):
            with self.settings.lock:
                worker = threading.Thread(target=read_status, daemon=True)
                worker.start()
                completed_while_sending = finished.wait(1)
            worker.join(2)
        self.assertTrue(completed_while_sending, "Reading settings must not wait for archive/network lock")
        self.assertEqual(result[0]["email_provider"], "smtp")

    def test_edit_reports_busy_without_switching_inflight_delivery(self):
        errors = []
        def edit():
            try:
                self.settings.configure({"email_enabled": False})
            except ValueError as error:
                errors.append(str(error))
        with self.settings.lock:
            worker = threading.Thread(target=edit, daemon=True)
            worker.start()
            worker.join(1)
            self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ["delivery_busy"])
        self.assertFalse(self.settings.path.exists())

    def test_legacy_provider_is_not_changed_to_smtp(self):
        self.settings.path.write_text(json.dumps({"email_to": "a@example.com"}))
        self.assertEqual(self.settings.snapshot()["email_provider"], "gmail")

    def test_legacy_consent_preserved_until_explicitly_disabled(self):
        self.settings.path.write_text(json.dumps({"email_to":"a@example.com", "drive_folder_id":"folder"}))
        self.assertTrue(enabled(self.settings.read(), "email"))
        self.settings.configure({"email_enabled":False, "drive_enabled":False})
        self.assertFalse(enabled(self.settings.read(), "email"))
        self.assertEqual(self.settings.read()["email_to"], "a@example.com")

    def test_connection_does_not_enable_delivery(self):
        with patch.object(self.settings,"profiles",return_value=[{"id":"work","email":"a@example.com"}]):
            value = self.settings.configure({"google_profile":"work"})
        self.assertFalse(value["email_enabled"])
        self.assertFalse(value["drive_enabled"])

    def test_account_change_does_not_redirect_pending_sends(self):
        self.settings.path.write_text(json.dumps({"google_profile": "personal", "email_enabled": True,
            "email_to": "a@example.com", "drive_enabled": True, "drive_folder_id": "folder"}))
        with patch.object(self.settings, "profiles", return_value=[{"id": "work", "email": "b@example.com"}]):
            value = self.settings.configure({"google_profile": "work"})
        self.assertFalse(value["email_enabled"])
        self.assertFalse(value["drive_enabled"])

    def test_activation_records_cutoff(self):
        self.settings.configure({"email_provider":"gmail","email_to":"a@example.com","email_enabled":True})
        self.assertTrue(self.settings.read()["email_enabled_at"])

    def test_no_ambient_google_fallback(self):
        with self.assertRaisesRegex(ValueError,"google_not_connected"):
            self.settings.executable()

    def test_abandoned_google_login_expires_without_logging_out(self):
        process = Mock()
        process.poll.return_value = None
        self.settings.login = process
        self.settings.login_started = 1
        with patch("delivery_settings.time.monotonic", return_value=302):
            result = self.settings.google_status()
        self.assertEqual(result["state"], "google_login_timeout")
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=2)

    def test_password_never_in_settings_or_snapshot(self):
        value = self.settings.configure({"smtp_password":"secret-test-value"})
        self.settings.passwords.set.assert_called_once_with("secret-test-value")
        self.assertNotIn("secret-test-value", self.settings.path.read_text())
        self.assertNotIn("secret-test-value", json.dumps(value))

    def test_legacy_smtp_secret_is_not_exposed(self):
        self.settings.path.write_text(json.dumps({"smtp": {"host": "smtp.example.com", "password": "legacy-secret"}}))
        self.assertNotIn("legacy-secret", json.dumps(self.settings.snapshot()))

    def test_plaintext_smtp_rejected(self):
        with self.assertRaisesRegex(ValueError,"smtp_tls_required"):
            self.settings.configure({"smtp":{"security":"none"}})

    def test_header_injection_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid_email"):
            self.settings.configure({"email_to":"a@example.com\r\nBcc:b@example.com"})

    def test_disconnect_preserves_smtp_and_local_files(self):
        self.settings.path.write_text(json.dumps({"email_provider":"smtp","email_enabled":True,"drive_enabled":True}))
        value = self.settings.disconnect()
        self.assertTrue(value["email_enabled"])
        self.assertFalse(value["drive_enabled"])

    def test_smtp_check_never_sends(self):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        with patch.object(self.settings,"smtp_client",return_value=client):
            self.assertEqual(self.settings.smtp_check()["state"],"connected")
        client.noop.assert_called_once()
        client.send_message.assert_not_called()

    def test_smtp_draft_check_never_saves_consent_or_credentials(self):
        self.settings.path.write_text(json.dumps({"email_enabled": False, "email_to": "original@example.com"}))
        before = self.settings.path.read_bytes()
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        with patch.object(self.settings, "smtp_client", return_value=client):
            result = self.settings.smtp_check({"email_enabled": True,
                "smtp": {"host": "smtp.example.com", "port": 587, "security": "starttls", "username": "sender"},
                "smtp_password": "draft-test-password"})
        self.assertEqual(result["state"], "connected")
        self.assertEqual(before, self.settings.path.read_bytes())
        self.settings.passwords.set.assert_not_called()
        client.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
