"""User-owned desktop OAuth. Secrets remain in the OS store, never JSON files.

No product Cloud project, ambient credentials, gcloud or gws dependency. The
legacy named gws path remains a separate, explicitly selected connection.
"""
from __future__ import annotations

import json
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"
PREFIX = "https://www.googleapis.com/auth/"
PERMISSIONS = {
    "mail": [PREFIX + "gmail.send"],
    # User chooses an existing destination folder, not just files created by us.
    "drive": [PREFIX + "drive"],
    "context": [PREFIX + "gmail.readonly", PREFIX + "drive.readonly",
                PREFIX + "calendar.readonly", PREFIX + "documents.readonly",
                PREFIX + "spreadsheets.readonly"],
}


def dependencies():
    vendor = Path(__file__).with_name("_vendor")
    if vendor.is_dir() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import requests
        from google_auth_oauthlib.flow import Flow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        return requests, Flow, Credentials, Request
    except ImportError:
        raise ValueError("google_dependency_missing") from None


def validate_client(value):
    if not isinstance(value, dict) or set(value) != {"installed"}:
        raise ValueError("google_desktop_json_required")
    client = value["installed"]
    if not isinstance(client, dict):
        raise ValueError("google_desktop_json_required")
    identity, secret = client.get("client_id"), client.get("client_secret")
    if (not isinstance(identity, str) or not identity.endswith(".apps.googleusercontent.com")
            or not 10 < len(identity) < 256 or any(c.isspace() for c in identity)
            or not isinstance(secret, str) or not 1 < len(secret) < 512):
        raise ValueError("google_invalid_client")
    if client.get("auth_uri") not in {AUTH_URI, "https://accounts.google.com/o/oauth2/v2/auth"} or client.get("token_uri") != TOKEN_URI:
        raise ValueError("google_invalid_endpoint")
    # Never trust imported redirect URLs, project identifiers or extra fields.
    return {"installed": {"client_id": identity, "client_secret": secret,
                          "auth_uri": AUTH_URI, "token_uri": TOKEN_URI,
                          "redirect_uris": ["http://localhost"]}}


class GoogleOAuth:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self._data = None
        self._worker = None
        self._cancel = threading.Event()
        self._error = ""
        self._url = ""

    def _load(self):
        if self._data is None:
            self._data = json.loads(self.store.get() or "{}")
        return self._data

    def _save(self, data):
        self.store.set(json.dumps(data))
        self._data = data

    def status(self):
        with self.lock:
            data = self._load()
            pending = self._worker is not None and self._worker.is_alive() and not self._cancel.is_set()
            return {"client_configured": bool(data.get("client")),
                    "state": "connecting" if pending else self._error or (
                        "connected" if data.get("credentials") else "authorization_required"),
                    "account": data.get("account", ""), "permissions": data.get("permissions", []),
                    "login_pending": pending}

    def import_client(self, value):
        client = validate_client(value)
        with self.lock:
            if self._load().get("client") == client:
                return self.status()
            if self._load().get("credentials"):
                raise ValueError("google_disconnect_before_replace")
            self._cancel.set()
            self._save({"client": client})
            self._error = ""
            return self.status()

    def disconnect(self, forget=False):
        with self.lock:
            self._cancel.set()
            client = self._load().get("client")
            if forget:
                self.store.delete()
                self._data = {}
            else:
                self._save({"client": client} if client else {})
            self._error = ""
            self._url = ""
        return self.status()

    def start(self, account, permissions):
        from delivery_settings import email
        account = email(account).lower()
        if (not isinstance(permissions, list) or not permissions
                or any(not isinstance(p, str) or p not in PERMISSIONS for p in permissions)):
            raise ValueError("google_permissions_required")
        requests, Flow, _, _ = dependencies()
        with self.lock:
            if self._worker is not None and self._worker.is_alive():
                if self._cancel.is_set():
                    raise ValueError("google_login_cancelling")
                return {**self.status(), "authorization_url": self._url}
            data = self._load()
            if not data.get("client"):
                raise ValueError("google_client_required")
            if data.get("account") and data["account"] != account:
                raise ValueError("google_disconnect_before_replace")
            scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email"]
            scopes += sorted({s for p in permissions for s in PERMISSIONS[p]})
            flow = Flow.from_client_config(data["client"], scopes=scopes,
                                           autogenerate_code_verifier=True)
            cancelled = threading.Event()
            received = {}
            state = secrets.token_urlsafe(32)

            class Callback(BaseHTTPRequestHandler):
                def setup(self):
                    super().setup()
                    self.connection.settimeout(5)

                def log_message(self, *args):
                    pass  # OAuth URLs contain codes, never log them.

                def do_GET(self):
                    parts = urlsplit(self.path)
                    query = parse_qs(parts.query)
                    valid = (parts.path == "/callback" and len(self.path) < 16384
                             and self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
                             and len(query.get("state", [])) == 1
                             and secrets.compare_digest(query["state"][0], state))
                    if valid and not cancelled.is_set() and not received:
                        received.update(code=query.get("code", [""])[0], error=query.get("error", [""])[0])
                    body = b"Return to MeetOnTrack to check connection status." if valid else b"Invalid OAuth callback."
                    self.send_response(200 if valid else 400)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            listener = HTTPServer(("127.0.0.1", 0), Callback)
            listener.timeout = 0.5
            flow.redirect_uri = f"http://127.0.0.1:{listener.server_port}/callback"
            try:
                url, _ = flow.authorization_url(state=state, access_type="offline",
                                                prompt="consent", login_hint=account)
            except Exception:
                listener.server_close()
                raise ValueError("google_login_failed") from None
            self._error, self._cancel, self._url = "", cancelled, url
            self._worker = threading.Thread(target=self._finish, args=(
                flow, listener, received, cancelled, account, sorted(set(permissions))), daemon=True)
            self._worker.start()
            return {**self.status(), "authorization_url": url}

    def _finish(self, flow, listener, received, cancelled, account, permissions):
        try:
            deadline = time.monotonic() + 300
            while not received and not cancelled.is_set() and time.monotonic() < deadline:
                listener.handle_request()
            if cancelled.is_set():
                return
            if not received:
                raise ValueError("google_login_timeout")
            if received.get("error") or not received.get("code"):
                raise ValueError("google_consent_denied")
            # State was checked at the loopback handler; library handles PKCE.
            flow.fetch_token(code=received["code"], timeout=20)
            credentials = flow.credentials
            granted = set(credentials.granted_scopes or credentials.scopes or [])
            if any(s not in granted for p in permissions for s in PERMISSIONS[p]):
                raise ValueError("permission_missing")
            if not credentials.refresh_token:
                raise ValueError("google_refresh_token_missing")
            identity = self._identity(credentials.token)
            if identity != account:
                raise ValueError("account_mismatch")
            with self.lock:
                if not cancelled.is_set():
                    self._save({"client": self._load()["client"], "account": account,
                                "permissions": permissions, "credentials": json.loads(credentials.to_json())})
        except Exception as error:
            safe = {"google_login_timeout", "google_consent_denied", "account_mismatch",
                    "google_refresh_token_missing", "permission_missing", "credential_store_unavailable"}
            with self.lock:
                if not cancelled.is_set():
                    self._error = str(error) if str(error) in safe else "google_login_failed"
        finally:
            listener.server_close()
            flow.oauth2session.close()
            received.clear()

    @staticmethod
    def _identity(token):
        requests, _, _, _ = dependencies()
        with requests.Session() as session:
            response = session.get(USERINFO, headers={"Authorization": "Bearer " + token},
                                   timeout=10, allow_redirects=False)
            if response.status_code != 200:
                raise ValueError("authorization_required")
            identity = response.json()
            if identity.get("email_verified") is not True:
                raise ValueError("account_mismatch")
            return str(identity.get("email", "")).lower()

    def token(self, permission):
        with self.lock:
            data = self._load()
            if permission not in data.get("permissions", []):
                raise ValueError("permission_missing")
            if not data.get("credentials"):
                raise ValueError("authorization_required")
            requests, _, Credentials, Request = dependencies()
            credentials = Credentials.from_authorized_user_info(data["credentials"])
            if not credentials.valid:
                try:
                    with requests.Session() as session:
                        request = Request(session=session)
                        credentials.refresh(lambda **kwargs: request(**{**kwargs, "timeout": 20}))
                    self._save({**data, "credentials": json.loads(credentials.to_json())})
                except Exception:
                    self._error = "authorization_expired"
                    raise ValueError("authorization_expired") from None
            return credentials.token

    def check(self):
        with self.lock:
            state = self.status()
            if state["state"] != "connected":
                return state
            token = self.token(state["permissions"][0])
            if self._identity(token) != state["account"]:
                raise ValueError("account_mismatch")
            return state

    def request(self, permission, method, url, *, params=None, body=None, data=None, content_type=None, timeout=20):
        # The caller builds only these API endpoints; never accept external URLs.
        host = urlsplit(url)
        if host.scheme != "https" or host.hostname not in {
                "www.googleapis.com", "gmail.googleapis.com", "docs.googleapis.com", "sheets.googleapis.com"} or host.username or host.password or host.port not in (None, 443):
            raise ValueError("google_invalid_endpoint")
        requests, _, _, _ = dependencies()
        headers = {"Authorization": "Bearer " + self.token(permission)}
        if content_type:
            headers["Content-Type"] = content_type
        response = None
        try:
            with requests.Session() as session:
                # No automatic replay: losing a send acknowledgement is ambiguous.
                response = session.request(method, url, params=params, json=body, data=data,
                                           headers=headers, timeout=timeout, allow_redirects=False, stream=True)
                if response.status_code == 401:
                    raise ValueError("authorization_expired")
                if response.status_code == 403:
                    raise ValueError("permission_missing")
                if response.status_code == 429:
                    raise ValueError("rate_limited")
                if response.status_code >= 500:
                    raise ValueError("timeout_outcome_unknown")
                if not 200 <= response.status_code < 300:
                    raise ValueError("google_api_failed")
                # Bound decompressed document/API responses as well as time spent
                # receiving chunks. Never cache an entire unbounded Drive file.
                limit, deadline = 2 * 1024 * 1024, time.monotonic() + timeout
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > limit or time.monotonic() > deadline:
                        raise ValueError("invalid_response")
                    chunks.append(chunk)
                result = json.loads(b"".join(chunks))
                if not isinstance(result, dict):
                    raise ValueError("invalid_response")
                return result
        except requests.RequestException:
            raise ValueError("timeout_outcome_unknown") from None
        except json.JSONDecodeError:
            raise ValueError("invalid_response") from None
        finally:
            if response is not None:
                response.close()
