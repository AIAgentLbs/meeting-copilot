#!/usr/bin/env python3
"""Preview the real UI/API with disposable state, no capture or background workers.

Use only for browser acceptance, not as an installed launcher. No real meeting,
account, repository manifest, or recording is loaded. Ctrl-C removes test state.
"""
import argparse
import json
import sys
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "copilot/web"))
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=43990)
parser.add_argument("--delivery-fixture", action="store_true", help="Synthetic report and stubbed delivery; never sends")
parser.add_argument("--updates-fixture", choices=("macos", "windows"), help="Synthetic release notice; never contacts a release feed")
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix="meetontrack-preview-") as directory:
    preview_root = Path(directory)
    config = preview_root / ".config/meeting-copilot"
    config.mkdir(parents=True)
    for name in ("repos.json", "active-repos.json"):
        (config / name).write_text(json.dumps({"repositories": [], "projects": []}))
    (config / "SESSION.md").write_text("Synthetic preview. No external inference.\n")
    (config / "config.json").write_text(json.dumps({"interface_language": "en"}))
    sample = preview_root / "sample-project"
    sample.mkdir()
    (sample / "project.md").write_text("Example project supports CSV export.\n")
    # Every module computes its user paths against disposable state at import.
    with patch("pathlib.Path.home", return_value=preview_root):
        import server
    server.RECOGNITION_GUARD.binary = preview_root / "not-installed"
    server.AI_READINESS = server.AIReadiness(preview_root / "not-installed", {})
    server.GOOGLE_CONTEXT._executable = ""
    if args.updates_fixture:
        from release_updates import ReleaseUpdates
        platform = args.updates_fixture
        prefix = "windows-" if platform == "windows" else ""
        fixture = {"tag_name": prefix + "v0.1.10", "html_url": "https://github.com/AIAgentLbs/meeting-copilot/releases/tag/" + prefix + "v0.1.10",
                   "body": "Synthetic update preview — no installation.\nImproved recording and MeetOnTrack branding.",
                   "assets": [{"name": "meeting-copilot-windows-v0.1.10-x64.zip" if platform == "windows" else "meeting-copilot-macos.zip"}]}
        server.UPDATES = ReleaseUpdates(preview_root / "updates.json", {"version": "0.1.9", "platform": platform, "channel": "technical-beta"}, fetch=lambda: [fixture])
        server.UPDATES.check(force=True)
    if args.delivery_fixture:
        # Keep synthetic OAuth import tests out of the real OS credential store.
        class PreviewSecrets:
            value = ""
            def get(self): return self.value
            def set(self, value): self.value = value
            def delete(self): self.value = ""
        server.ARCHIVE.delivery_settings.oauth.store = PreviewSecrets()
        def no_google_login(*args, **kwargs):
            raise ValueError("google_login_failed")
        server.ARCHIVE.delivery_settings.oauth.start = no_google_login
        from datetime import datetime, timedelta, timezone
        report_dir = server.ARCHIVE.reports_root / "synthetic-delivery"
        report_dir.mkdir(parents=True)
        (report_dir / "meeting-report.pdf").write_bytes(b"%PDF-synthetic-not-a-real-report")
        report = {"generated_at": datetime.now(timezone.utc).isoformat(),
                  "pdf": "/api/archive/report/synthetic-delivery/meeting-report.pdf",
                  "mail_status": "failed", "drive_status": "not_configured", "telegram_status": "not_configured"}
        (report_dir / "report.json").write_text(json.dumps(report))
        detail = {"meeting_id": "synthetic-delivery", "title": "Synthetic delivery check",
                  "started_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                  "ended_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
                  "status": "finished", "duration_seconds": 600, "transcript_count": 1, "journal_count": 0, "frame_count": 0,
                  "transcript": [], "journal": [], "frames": [], "meeting_chat": [], "participants": [],
                  "report": report, "overview": {"points": ["Synthetic report. No external send."], "questions": []}}
        def fixture_detail(identity):
            return {**detail, "report": json.loads((report_dir / "report.json").read_text())}
        server.ARCHIVE.list_meetings = lambda query="": [detail] if query.lower() in detail["title"].lower() else []
        server.ARCHIVE.detail = fixture_detail
        server.ARCHIVE.report_detail = fixture_detail
        server.ARCHIVE.deliver = lambda *a, **k: {"mail_status": "sent", "gmail_message_id": "synthetic-ack"}
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), server.Handler)
    print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Synthetic folder for UI connection: {sample}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
