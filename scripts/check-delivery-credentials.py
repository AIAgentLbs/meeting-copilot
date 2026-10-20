"""Native credential-store acceptance using disposable, synthetic credentials.

Never opens the owner's production SMTP item. The unique test item is deleted
in a finally block; output contains only platform and pass/fail, never a secret.
"""
from pathlib import Path
import secrets
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "copilot/web"))
from delivery_settings import PasswordStore
from google_oauth import GoogleOAuth, AUTH_URI, TOKEN_URI


def main():
    with tempfile.TemporaryDirectory(prefix="meetontrack-credential-test-") as directory:
        store = PasswordStore(directory, "com.aiagentlbs.meetontrack.test." + uuid.uuid4().hex)
        value = secrets.token_urlsafe(48)
        try:
            assert store.get() == ""
            store.set(value)
            assert store.get() == value
            second = secrets.token_urlsafe(48)
            store.set(second)
            assert store.get() == second
            if store.path.exists():
                assert value.encode() not in store.path.read_bytes()
                assert second.encode() not in store.path.read_bytes()
            print(f"{sys.platform}: native credential roundtrip passed")
        finally:
            store.delete()
        assert store.get() == ""
        print("Disposable credential removed; production credential untouched")
        oauth_store = PasswordStore(directory, "com.aiagentlbs.meetontrack.test.oauth." + uuid.uuid4().hex, "oauth-test.dpapi")
        oauth = GoogleOAuth(oauth_store)
        try:
            oauth.import_client({"installed": {"client_id": "synthetic.apps.googleusercontent.com",
                "client_secret": secrets.token_urlsafe(48), "auth_uri": AUTH_URI, "token_uri": TOKEN_URI}})
            restored = GoogleOAuth(oauth_store)
            assert restored.status()["client_configured"]
            assert restored.status()["state"] == "authorization_required"
            restored.disconnect()
            assert restored.status()["client_configured"]
        finally:
            oauth.disconnect(forget=True)
        assert oauth_store.get() == ""
        print(f"{sys.platform}: native OAuth JSON store/import/reload/disconnect/forget passed")


if __name__ == "__main__":
    main()
