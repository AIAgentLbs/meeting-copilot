import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

from google_oauth import GoogleOAuth, validate_client, AUTH_URI, TOKEN_URI, PREFIX
from google_api import delivery, read
from delivery_settings import DeliverySettings, PasswordStore

CLIENT = {"installed": {"client_id": "test-client.apps.googleusercontent.com",
                       "client_secret": "synthetic-client-secret", "auth_uri": AUTH_URI, "token_uri": TOKEN_URI}}


class MemoryStore:
    def __init__(self):
        self.value = ""
    def get(self):
        return self.value
    def set(self, value):
        self.value = value
    def delete(self):
        self.value = ""


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.oauth = GoogleOAuth(self.store)
        self.addCleanup(self.stop)

    def stop(self):
        self.oauth._cancel.set()
        if self.oauth._worker:
            self.oauth._worker.join(6)

    def test_reject_web_service_account_and_non_google_endpoints(self):
        for value in ({"web": CLIENT["installed"]}, {"type": "service_account"}, [],
                      {"installed": {**CLIENT["installed"], "token_uri": "https://attacker.example/token"}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_client(value)
        self.assertEqual(self.store.value, "")

    def test_import_stores_secret_only_in_store_and_status_is_redacted(self):
        result = self.oauth.import_client(CLIENT)
        self.assertTrue(result["client_configured"])
        self.assertNotIn("synthetic-client-secret", json.dumps(result))
        self.assertIn("synthetic-client-secret", self.store.value)
        self.assertEqual(result["state"], "authorization_required")

    def test_connected_client_replacement_requires_disconnect(self):
        self.oauth._save({"client": CLIENT, "credentials": {"refresh_token": "test"}})
        changed = {"installed": {**CLIENT["installed"], "client_secret": "different"}}
        with self.assertRaisesRegex(ValueError, "disconnect_before_replace"):
            self.oauth.import_client(changed)
        self.oauth.disconnect()
        self.oauth.import_client(changed)
        self.assertNotIn("refresh_token", self.store.value)

    def test_disconnect_clears_credentials_and_forget_removes_client(self):
        self.oauth._save({"client": CLIENT, "credentials": {"refresh_token": "test"}, "account": "a@example.com"})
        self.oauth.disconnect()
        self.assertNotIn("test", self.store.value.replace("test-client", "client"))
        self.assertTrue(self.oauth.status()["client_configured"])
        self.oauth.disconnect(forget=True)
        self.assertEqual(self.store.value, "")

    def flow(self, identity="a@example.com", granted=None):
        self.oauth.import_client(CLIENT)
        self.flow_obj = Mock()
        self.flow_obj.credentials.granted_scopes = granted if granted is not None else [PREFIX + "gmail.send"]
        self.flow_obj.credentials.refresh_token = "synthetic-refresh"
        self.flow_obj.credentials.token = "synthetic-access"
        self.flow_obj.credentials.to_json.return_value = json.dumps({"refresh_token": "synthetic-refresh"})
        self.flow_obj.authorization_url.side_effect = lambda **kw: ("https://accounts.google.com/o/oauth2/auth?" +
                                                                   urlencode({"state": kw["state"]}), kw["state"])
        dep = patch("google_oauth.dependencies", return_value=(Mock(), Mock(from_client_config=Mock(return_value=self.flow_obj)), Mock(), Mock()))
        dep.start(); self.addCleanup(dep.stop)
        who = patch.object(self.oauth, "_identity", return_value=identity)
        who.start(); self.addCleanup(who.stop)
        result = self.oauth.start("a@example.com", ["mail"])
        return parse_qs(urlsplit(result["authorization_url"]).query)["state"][0]

    def callback(self, state, **kwargs):
        with urlopen(self.flow_obj.redirect_uri + "?" + urlencode({"state": state, **kwargs}), timeout=5) as r:
            self.assertEqual(r.status, 200)

    def test_real_loopback_rejects_state_then_accepts_one_code(self):
        state = self.flow()
        self.assertTrue(self.flow_obj.redirect_uri.startswith("http://127.0.0.1:"))
        try:
            self.callback("wrong", code="synthetic-code")
            self.fail("Wrong state accepted")
        except HTTPError as error:
            error.close()
        self.flow_obj.fetch_token.assert_not_called()
        self.callback(state, code="synthetic-code")
        self.oauth._worker.join(3)
        self.assertEqual(self.oauth.status()["state"], "connected")
        self.assertEqual(self.oauth.status()["account"], "a@example.com")
        self.flow_obj.fetch_token.assert_called_once_with(code="synthetic-code", timeout=20)

    def test_wrong_account_does_not_persist_tokens(self):
        state = self.flow(identity="wrong@example.com")
        self.callback(state, code="code")
        self.oauth._worker.join(3)
        self.assertEqual(self.oauth.status()["state"], "account_mismatch")
        self.assertNotIn("synthetic-refresh", self.store.value)

    def test_missing_scope_does_not_claim_connected(self):
        state = self.flow(granted=[])
        self.flow_obj.credentials.scopes = []
        self.callback(state, code="code")
        self.oauth._worker.join(3)
        self.assertEqual(self.oauth.status()["state"], "permission_missing")

    def test_consent_denied_does_not_exchange(self):
        state = self.flow()
        self.callback(state, error="access_denied")
        self.oauth._worker.join(3)
        self.assertEqual(self.oauth.status()["state"], "google_consent_denied")
        self.flow_obj.fetch_token.assert_not_called()

    def test_disconnect_cancels_pending_login(self):
        self.flow()
        self.oauth.disconnect()
        self.oauth._worker.join(3)
        self.assertFalse(self.oauth._worker.is_alive())
        self.flow_obj.fetch_token.assert_not_called()

    def test_timeout_is_bounded(self):
        self.flow()
        with patch("google_oauth.time.monotonic", return_value=time.monotonic()+301):
            self.oauth._worker.join(3)
        self.assertEqual(self.oauth.status()["state"], "google_login_timeout")

    def test_import_does_not_enable_delivery_or_touch_external_registry(self):
        with tempfile.TemporaryDirectory() as root:
            settings = DeliverySettings(Path(root))
            settings.oauth = self.oauth
            settings.home = Path(root)
            result = settings.import_google(CLIENT)
            self.assertEqual(result["google_profile"], "custom")
            self.assertFalse(result["email_enabled"])
            self.assertFalse(result["drive_enabled"])
            self.assertEqual(result["email_provider"], "smtp")
            self.assertNotIn("synthetic-client-secret", settings.path.read_text())
            self.assertFalse((Path(root)/".config/gws-profiles").exists())

    def test_windows_store_names_do_not_collide(self):
        a = PasswordStore(Path("test"))
        b = PasswordStore(Path("test"), "test.google", "google-oauth.dpapi")
        self.assertNotEqual(a.path, b.path)

    def test_real_library_generates_pkce_and_local_redirect(self):
        try:
            from google_oauth import dependencies
            dependencies()
        except ValueError:
            self.skipTest("Run with the packaged OAuth dependencies")
        self.oauth.import_client(CLIENT)
        result = self.oauth.start("a@example.com", ["mail"])
        params = parse_qs(urlsplit(result["authorization_url"]).query)
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertGreaterEqual(len(params["code_challenge"][0]), 43)
        self.assertEqual(urlsplit(params["redirect_uri"][0]).hostname, "127.0.0.1")
        self.assertEqual(params["access_type"], ["offline"])
        self.assertNotIn("synthetic-client-secret", result["authorization_url"])

    def test_auth_material_roundtrip_does_not_enable_context(self):
        from google_context import GoogleContext
        with tempfile.TemporaryDirectory() as root:
            settings = DeliverySettings(Path(root))
            settings.oauth = self.oauth
            settings.home = Path(root)
            settings.import_google(CLIENT)
            self.oauth._save({"client": CLIENT, "credentials": {"refresh_token": "synthetic"},
                              "permissions": ["context"], "account": "a@example.com"})
            context = GoogleContext(Path(root)/"google-context.json")
            context.delivery_settings = settings
            self.assertEqual(context.enabled_sources(), [])
            self.assertEqual(context.status()["auth"], "connected")
            context.connect()
            self.assertEqual(context.enabled_sources(), [])
            context.configure({"calendar": False, "gmail": True, "drive": False})
            self.assertEqual(context.enabled_sources(), ["gmail"])
            context.disconnect()
            self.assertEqual(context.enabled_sources(), [])
            self.assertTrue(self.oauth.status()["client_configured"])

    def test_no_permission_no_network(self):
        with self.assertRaisesRegex(ValueError, "permission_missing"):
            self.oauth.token("mail")

    def test_transport_bounds_redacts_errors_and_never_replays_send(self):
        requests = MagicMock(RequestException=OSError)
        session = requests.Session.return_value.__enter__.return_value
        response = session.request.return_value
        with patch("google_oauth.dependencies", return_value=(requests, None, None, None)), patch.object(self.oauth, "token", return_value="synthetic-access"):
            for status, chunks, expected in [
                (401, [], "authorization_expired"), (403, [], "permission_missing"),
                (429, [], "rate_limited"), (503, [], "timeout_outcome_unknown"),
                (302, [], "google_api_failed"),
                (200, [b"x" * (2 * 1024 * 1024 + 1)], "invalid_response"),
                (200, [b"invalid synthetic secret"], "invalid_response"),
            ]:
                with self.subTest(status=status, expected=expected):
                    session.reset_mock(); response.status_code = status
                    response.iter_content.return_value = iter(chunks)
                    with self.assertRaisesRegex(ValueError, "^" + expected + "$"):
                        self.oauth.request("mail", "POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send")
                    session.request.assert_called_once()
                    self.assertFalse(session.request.call_args.kwargs["allow_redirects"])
                    response.close.assert_called()
            response.status_code = 200
            response.iter_content.return_value = iter([b'{"id":"synthetic-ack"}'])
            self.assertEqual(self.oauth.request("mail", "POST", "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"), {"id": "synthetic-ack"})

    def test_refresh_saves_rotated_token_and_redacts_failures(self):
        self.oauth._save({"permissions": ["mail"], "credentials": {"refresh_token": "old"}})
        requests, cls, request = MagicMock(), Mock(), Mock()
        credential = cls.from_authorized_user_info.return_value
        credential.valid = False
        credential.token = "new-token"
        credential.to_json.return_value = '{"refresh_token":"rotated"}'
        with patch("google_oauth.dependencies", return_value=(requests, None, cls, request)):
            self.assertEqual(self.oauth.token("mail"), "new-token")
            self.assertIn("rotated", self.store.value)
            refresh = credential.refresh.call_args.args[0]
            refresh(url="https://oauth2.googleapis.com/token", timeout=999)
            self.assertEqual(request.return_value.call_args.kwargs["timeout"], 20)
            credential.refresh.side_effect = RuntimeError("private token must not escape")
            with self.assertRaisesRegex(ValueError, "^authorization_expired$"):
                self.oauth.token("mail")

    def test_transport_rejects_other_hosts_credentials_and_ports(self):
        for url in ["https://attacker.example/token", "http://www.googleapis.com/", "https://user@www.googleapis.com/", "https://www.googleapis.com:8443/"]:
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, "google_invalid_endpoint"):
                self.oauth.request("mail", "GET", url)

    def test_context_adapter_is_read_only_and_encodes_ids(self):
        oauth = Mock()
        read(oauth, ["calendar", "events", "list"], {"calendarId": "primary", "singleEvents": True})
        self.assertEqual(oauth.request.call_args.args[:2], ("context", "GET"))
        self.assertEqual(oauth.request.call_args.kwargs["params"], {"singleEvents": "true"})
        with self.assertRaises(ValueError):
            read(oauth, ["drive", "files", "delete"], {})

    def test_gmail_and_drive_adapters_keep_separate_scopes(self):
        oauth = Mock()
        oauth.status.return_value = {"account": "a@example.com"}
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/"report.pdf"; path.write_bytes(b"synthetic pdf")
            delivery(oauth, ["gmail", "+send", "--to", "b@example.com", "--subject", "Test", "--body", "Synthetic", "--attach", str(path)], 20)
            self.assertEqual(oauth.request.call_args.args[0], "mail")
            delivery(oauth, ["drive", "files", "create", "--json", '{"name":"report.pdf"}', "--upload", str(path)], 20)
            self.assertEqual(oauth.request.call_args.args[0], "drive")
            self.assertIn(b"synthetic pdf", oauth.request.call_args.kwargs["data"])


if __name__ == "__main__":
    unittest.main()
