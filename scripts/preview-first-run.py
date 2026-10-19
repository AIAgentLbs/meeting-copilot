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
    server.GOOGLE_CONTEXT.executable = None
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), server.Handler)
    print(f"Preview: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Synthetic folder for UI connection: {sample}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
