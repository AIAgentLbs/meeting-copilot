"""Exercise real TLS SMTP transport on loopback with only synthetic mail.

Run with: uv run --no-project --python 3.12 --with aiosmtpd==1.4.6
    python scripts/check-smtp-transport.py
No internet SMTP service, owner mailbox, production credentials or report is used.
"""
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
from unittest.mock import patch

from aiosmtpd.controller import Controller

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "copilot/web"))
from delivery_settings import DeliverySettings


class Sink:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope.content)
        return "250 accepted synthetic message"


def run():
    with tempfile.TemporaryDirectory(prefix="meetontrack-smtp-test-") as directory:
        root = Path(directory)
        certificate, key = root / "cert.pem", root / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(certificate), "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        key.chmod(0o600)
        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(certificate, key)
        client_context = ssl.create_default_context(cafile=str(certificate))
        for mode in ("starttls", "tls"):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            sink = Sink()
            # aiosmtpd's auth_require_tls detects STARTTLS, not the outer TLS
            # listener used for SMTPS. The latter accepts only TLS connections.
            options = {"auth_required": True, "auth_require_tls": mode == "starttls",
                "auth_callback": lambda mechanism, login, password: login == b"synthetic" and password == b"test-only"}
            options.update({"tls_context": server_context, "require_starttls": True} if mode == "starttls"
                           else {"ssl_context": server_context})
            controller = Controller(sink, hostname="127.0.0.1", port=port, **options)
            controller.start()
            try:
                settings = DeliverySettings(root / mode)
                draft = {"smtp": {"host": "127.0.0.1", "port": port,
                         "security": mode, "username": "synthetic"}, "smtp_password": "test-only"}
                # Only certificate trust is substituted. smtplib, TLS handshake,
                # AUTH, NOOP and DATA operate over actual loopback sockets.
                with patch("delivery_settings.ssl.create_default_context", return_value=client_context):
                    assert settings.smtp_check(draft) == {"state": "connected"}
                    assert sink.messages == [] and not settings.path.exists()
                    with settings.smtp_client(draft, "test-only") as client:
                        message = EmailMessage()
                        message["From"] = "sender@example.invalid"
                        message["To"] = "recipient@example.invalid"
                        message["Subject"] = "Synthetic MeetOnTrack transport acceptance"
                        message.set_content("Synthetic test, not meeting data.")
                        message.add_attachment(b"%PDF-synthetic", maintype="application", subtype="pdf", filename="test.pdf")
                        assert client.send_message(message) == {}
                    assert len(sink.messages) == 1
                    received = BytesParser(policy=policy.default).parsebytes(sink.messages[0])
                    assert list(received.iter_attachments())[0].get_payload(decode=True) == b"%PDF-synthetic"
                    assert settings.smtp_check({**draft, "smtp_password": "incorrect"}) == {"state": "smtp_auth_failed"}
                    assert len(sink.messages) == 1
                print(f"{mode}: trusted TLS, AUTH, no-send check, PDF delivery and bad-password rejection passed")
            finally:
                controller.stop()


if __name__ == "__main__":
    run()
