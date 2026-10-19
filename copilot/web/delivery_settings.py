"""Explicit delivery consent, account selection and protected SMTP credentials."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import smtplib
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from contextlib import contextmanager


def read_json(path):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".delivery-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def enabled(settings, channel):
    if settings.get("enabled") is False:
        return False
    flag = settings.get(f"{channel}_enabled")
    if isinstance(flag, bool):
        return flag
    # Preserve pre-existing, owner-configured installations; new installs are off.
    return bool(settings.get("email_to") if channel == "email" else
                settings.get("drive_folder_id") or settings.get("drive_remote") or settings.get("drive_local_path")
                if channel == "drive" else settings.get("telegram_account") and settings.get("telegram_config"))


def email(value, optional=False):
    value = str(value or "").strip()
    if optional and not value:
        return ""
    if len(value) > 254 or not re.fullmatch(r"[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+", value):
        raise ValueError("invalid_email")
    return value


class PasswordStore:
    """macOS Keychain or Windows user-bound DPAPI; never plaintext/argv/logs."""
    def __init__(self, root, service="com.aiagentlbs.meetontrack.smtp", filename="smtp-password.dpapi"):
        self.path = Path(root) / filename
        self.service = service.encode("utf-8")

    def _mac(self, password=None, delete=False):
        sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        service, account = self.service, b"smtp"
        length, data, item = ctypes.c_uint32(), ctypes.c_void_p(), ctypes.c_void_p()
        sec.SecKeychainFindGenericPassword.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.c_uint32, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
        sec.SecKeychainItemFreeContent.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        sec.SecKeychainItemModifyAttributesAndData.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]
        sec.SecKeychainAddGenericPassword.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p,
            ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_void_p]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        sec.SecKeychainItemDelete.argtypes = [ctypes.c_void_p]
        status = sec.SecKeychainFindGenericPassword(None, len(service), service, len(account), account,
                                                  ctypes.byref(length), ctypes.byref(data), ctypes.byref(item))
        try:
            if delete:
                if status == -25300:
                    return
                if status or sec.SecKeychainItemDelete(item):
                    raise ValueError("credential_store_unavailable")
                return
            if password is None:
                if status == -25300:
                    return ""
                if status:
                    raise ValueError("credential_store_unavailable")
                return ctypes.string_at(data, length.value).decode()
            encoded = password.encode()
            if status == 0:
                status = sec.SecKeychainItemModifyAttributesAndData(item, None, len(encoded), encoded)
            elif status == -25300:
                status = sec.SecKeychainAddGenericPassword(None, len(service), service, len(account), account,
                                                         len(encoded), encoded, None)
            if status:
                raise ValueError("credential_store_unavailable")
        finally:
            if data:
                sec.SecKeychainItemFreeContent(None, data)
            if item:
                cf.CFRelease(item)

    def _windows(self, value, decrypt=False):
        class Blob(ctypes.Structure):
            _fields_ = [("size", ctypes.c_uint32), ("data", ctypes.POINTER(ctypes.c_ubyte))]
        buf = ctypes.create_string_buffer(value)
        source = Blob(len(value), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
        target = Blob()
        fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
        if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise ValueError("credential_store_unavailable")
        try:
            return ctypes.string_at(target.data, target.size)
        finally:
            ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
            ctypes.windll.kernel32.LocalFree(target.data)

    def get(self):
        if sys.platform == "darwin":
            return self._mac()
        if os.name == "nt":
            return self._windows(self.path.read_bytes(), True).decode() if self.path.exists() else ""
        raise ValueError("credential_store_unavailable")

    def set(self, value):
        if sys.platform == "darwin":
            self._mac(value)
        elif os.name == "nt":
            protected = self._windows(value.encode())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".smtp-")
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(protected)
                os.replace(name, self.path)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
        else:
            raise ValueError("credential_store_unavailable")

    def delete(self):
        if sys.platform == "darwin":
            self._mac(delete=True)
        elif os.name == "nt":
            self.path.unlink(missing_ok=True)
        else:
            raise ValueError("credential_store_unavailable")


class DeliverySettings:
    def __init__(self, root, lock=None):
        self.home = Path.home()
        self.root = Path(root)
        self.path = self.root / "delivery.json"
        self.lock = lock or threading.RLock()
        self.login_lock = threading.RLock()
        self.passwords = PasswordStore(root)
        from google_oauth import GoogleOAuth
        store_id = hashlib.sha256(str(self.root.resolve()).encode()).hexdigest()[:16]
        self.oauth = GoogleOAuth(PasswordStore(root, "com.aiagentlbs.meetontrack.google." + store_id, "google-oauth.dpapi"))
        self.login = None
        self.login_started = 0
        self.login_error = ""

    def _expire_login(self):
        with self.login_lock:
            self._expire_login_locked()

    def _expire_login_locked(self):
        if self.login is not None and self.login.poll() is None and time.monotonic() - self.login_started >= 300:
            self.login.terminate()
            try:
                self.login.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.login.kill()
                self.login.wait(timeout=2)
            self.login_error = "google_login_timeout"

    def read(self):
        return read_json(self.path)

    @contextmanager
    def _edit(self):
        # Preserve identity/consent serialization with delivery, but return an
        # actionable busy response instead of hanging the settings form.
        if not self.lock.acquire(timeout=0.25):
            raise ValueError("delivery_busy")
        try:
            yield
        finally:
            self.lock.release()

    def profiles(self):
        registry = read_json(self.home / ".config/gws-profiles/accounts.json")
        result = [{"id": key, "email": value.get("email", "")} for key, value in registry.items()
                  if key in {"personal", "work"} and isinstance(value, dict)]
        own = self.own_google_status()
        if own.get("client_configured"):
            result.append({"id": "custom", "email": own.get("account", "")})
        return result

    def own_google_status(self):
        try:
            return self.oauth.status()
        except (ValueError, OSError):
            return {"state": "credential_store_unavailable", "client_configured": False}

    def import_google(self, value):
        with self._edit():
            self.oauth.import_client(value)
            changes = {"google_profile": "custom", "drive_enabled": False}
            if self.read().get("email_provider", "gmail") == "gmail":
                changes["email_enabled"] = False
            return self.configure(changes)

    def profile(self):
        raw = self.read()
        selected = raw.get("google_profile")
        if selected in {"personal", "work", "custom"}:
            return selected
        account = raw.get("google_account")
        return next((p["id"] for p in self.profiles() if account and p["email"] == account), "")

    def executable(self):
        profile = self.profile()
        if not profile:
            raise ValueError("google_not_connected")
        if profile == "custom":
            raise ValueError("google_native_connector")
        name = "gws-" + profile
        path = shutil.which(name)
        local = self.home / ".local/bin" / name
        if not path and local.is_file():
            path = str(local)
        if not path:
            raise ValueError("google_connector_missing")
        return path

    def snapshot(self):
        # The shared archive lock can be held by a slow provider request. Atomic
        # settings reads/status must not freeze the form for the entire upload.
        self._expire_login()
        raw = self.read()
        return {"email_enabled": enabled(raw, "email"), "drive_enabled": enabled(raw, "drive"),
                # A fresh form suggests SMTP, without opting in to delivery.
                # Legacy configurations without a provider still mean Gmail.
                "telegram_enabled": enabled(raw, "telegram"), "email_provider": raw.get("email_provider", "gmail" if raw else "smtp"),
                "email_to": raw.get("email_to", ""), "google_profile": self.profile(),
                "google_account": raw.get("google_account", ""), "drive_folder_id": raw.get("drive_folder_id", ""),
                "profiles": self.profiles(), "smtp": {key: value for key, value in raw.get("smtp", {}).items()
                    if key in {"host", "port", "security", "username", "from"}},
                "smtp_password_saved": raw.get("smtp_password_saved", False),
                "login_pending": self.login is not None and self.login.poll() is None,
                "own_google": self.own_google_status(),
                "telegram_configured": bool(raw.get("telegram_account") and raw.get("telegram_config")),
                "local_reports": str(self.home / ".local/share/meeting-copilot/reports")}

    def configure(self, payload):
        with self._edit():
            raw = self.read()
            raw.setdefault("email_provider", "gmail" if raw else "smtp")
            for channel in ("email", "drive", "telegram"):
                key = channel + "_enabled"
                if key in payload and type(payload[key]) is not bool:
                    raise ValueError("invalid_enabled")
                value = payload.get(key, enabled(raw, channel))
                if value and not enabled(raw, channel):
                    # Connecting does not silently backfill historical reports.
                    from datetime import datetime, timezone
                    raw[channel + "_enabled_at"] = datetime.now(timezone.utc).isoformat()
                raw[key] = value
            raw.pop("enabled", None)
            if "email_to" in payload:
                raw["email_to"] = email(payload["email_to"], optional=True)
            if "email_provider" in payload:
                if payload["email_provider"] not in {"gmail", "smtp"}:
                    raise ValueError("invalid_email_provider")
                raw["email_provider"] = payload["email_provider"]
            if "google_profile" in payload:
                profile = str(payload["google_profile"])
                selected = next((p for p in self.profiles() if p["id"] == profile), None)
                if profile and not selected:
                    raise ValueError("google_connector_missing")
                if profile != self.profile():
                    # Selecting/checking another identity is not consent to
                    # route queued reports through it. Explicit Save can opt in.
                    if "drive_enabled" not in payload:
                        raw["drive_enabled"] = False
                    if "email_enabled" not in payload and raw.get("email_provider", "gmail") == "gmail":
                        raw["email_enabled"] = False
                raw["google_profile"] = profile
                raw["google_account"] = selected["email"] if selected else ""
            if "drive_folder_id" in payload:
                folder = str(payload["drive_folder_id"]).strip()
                if folder.startswith("https://drive.google.com/drive/folders/"):
                    folder = folder.split("/folders/", 1)[1].split("?", 1)[0].strip("/")
                if folder and not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", folder):
                    raise ValueError("invalid_drive_folder")
                raw["drive_folder_id"] = folder
            if "smtp" in payload:
                value = payload["smtp"]
                if not isinstance(value, dict):
                    raise ValueError("invalid_smtp")
                host = str(value.get("host", "")).strip()
                if host and not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
                    raise ValueError("invalid_smtp_host")
                mode = value.get("security", "starttls")
                if mode not in {"starttls", "tls"}:
                    raise ValueError("smtp_tls_required")
                try:
                    port = int(value.get("port") or (465 if mode == "tls" else 587))
                except (TypeError, ValueError):
                    raise ValueError("invalid_smtp_port") from None
                if not 1 <= port <= 65535:
                    raise ValueError("invalid_smtp_port")
                user = str(value.get("username", ""))
                if len(user) > 254 or any(c in user for c in "\r\n\0"):
                    raise ValueError("invalid_smtp_user")
                raw["smtp"] = {"host": host, "port": port, "security": mode,
                               "username": user, "from": email(value.get("from"), optional=True)}
                old_smtp = self.read().get("smtp", {})
                if (old_smtp.get("host"), old_smtp.get("username")) != (host, user):
                    raw["smtp_password_saved"] = False
            if raw["email_enabled"] and not raw.get("email_to"):
                raise ValueError("recipient_required")
            if raw["drive_enabled"] and not raw.get("drive_folder_id"):
                raise ValueError("drive_folder_required")
            password = payload.get("smtp_password", "")
            if not isinstance(password, str) or len(password) > 4096:
                raise ValueError("invalid_smtp_password")
            if raw["email_enabled"] and raw.get("email_provider") == "smtp":
                smtp = raw.get("smtp", {})
                if not smtp.get("host") or not smtp.get("from") or not smtp.get("username"):
                    raise ValueError("smtp_settings_required")
                if not password and not raw.get("smtp_password_saved"):
                    raise ValueError("smtp_password_required")
            if password:
                self.passwords.set(password)
                raw["smtp_password_saved"] = True
            write_json(self.path, raw)
            return self.snapshot()

    def google_status(self):
        if self.profile() == "custom":
            try:
                return self.oauth.check()
            except ValueError as error:
                return {"state": str(error)}
        self._expire_login()
        if self.login_error:
            return {"state": self.login_error}
        if self.login is not None and self.login.poll() is None:
            return {"state": "connecting"}
        try:
            result = subprocess.run([self.executable(), "whoami"], capture_output=True, text=True, timeout=20)
            if result.returncode:
                return {"state": "authorization_required"}
            account = result.stdout.strip().splitlines()[-1]
            expected = self.read().get("google_account")
            if not expected or account.lower() != expected.lower():
                return {"state": "account_mismatch"}
            return {"state": "connected", "account": account}
        except (ValueError, OSError, subprocess.TimeoutExpired) as error:
            return {"state": str(error) if isinstance(error, ValueError) else "google_unavailable"}

    def connect(self, payload=None):
        if self.profile() == "custom":
            payload = payload or {}
            return self.oauth.start(payload.get("account", ""), payload.get("permissions"))
        with self._edit():
            if self.google_status()["state"] == "connected":
                return self.google_status()
            if self.login is None or self.login.poll() is not None:
                self.login = subprocess.Popen([self.executable(), "auth", "login", "--full"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.login_started = time.monotonic()
                self.login_error = ""
            return {"state": "connecting"}

    def disconnect(self):
        with self._edit():
            if self.profile() == "custom":
                self.oauth.disconnect()
            raw = self.read()
            raw.update(google_profile="", google_account="", drive_enabled=False)
            if raw.get("email_provider", "gmail") == "gmail":
                raw["email_enabled"] = False
            write_json(self.path, raw)
            if self.login is not None and self.login.poll() is None:
                self.login.terminate()
                try:
                    self.login.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.login.kill()
                    self.login.wait(timeout=2)
            self.login_error = ""
            # Do not log out a shared account used by other applications.
            return self.snapshot()

    def smtp_client(self, raw=None, password=None):
        raw = self.read() if raw is None else raw
        settings = raw.get("smtp", {})
        if password is None:
            if not raw.get("smtp_password_saved"):
                raise ValueError("smtp_password_required")
            password = self.passwords.get()
        if not password:
            raise ValueError("smtp_password_required")
        context = ssl.create_default_context()
        client = (smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=30, context=context)
                  if settings["security"] == "tls" else smtplib.SMTP(settings["host"], settings["port"], timeout=30))
        try:
            if settings["security"] == "starttls":
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(settings["username"], password)
            return client
        except Exception:
            client.close()
            raise

    def smtp_check(self, payload=None):
        try:
            raw, password = None, None
            if payload is not None:
                # Validate a draft in memory. Checking must not save routing,
                # credentials or channel consent, nor start queued deliveries.
                value = payload.get("smtp", {})
                if not isinstance(value, dict):
                    raise ValueError("invalid_smtp")
                host = str(value.get("host", "")).strip()
                mode = value.get("security", "starttls")
                port = int(value.get("port") or (465 if mode == "tls" else 587))
                user = str(value.get("username", ""))
                if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host) or mode not in {"starttls", "tls"} or not 1 <= port <= 65535:
                    raise ValueError("invalid_smtp")
                if not user or len(user) > 254 or any(c in user for c in "\r\n\0"):
                    raise ValueError("invalid_smtp")
                old = self.read()
                old_smtp = old.get("smtp", {})
                password = payload.get("smtp_password") or None
                if password is not None and (not isinstance(password, str) or len(password) > 4096):
                    raise ValueError("invalid_smtp_password")
                saved_matches = old.get("smtp_password_saved") and (old_smtp.get("host"), old_smtp.get("username")) == (host, user)
                raw = {"smtp": {"host": host, "port": port, "security": mode, "username": user},
                       "smtp_password_saved": bool(saved_matches)}
            with (self.smtp_client() if raw is None else self.smtp_client(raw, password)) as client:
                client.noop()
            return {"state": "connected"}
        except smtplib.SMTPAuthenticationError:
            return {"state": "smtp_auth_failed"}
        except (OSError, smtplib.SMTPException, ValueError, KeyError):
            return {"state": "smtp_connection_failed"}
