"""Install this bounded web-only fix on an idle Mac, with backup and rollback.

Capture is never stopped. This is an operator hotfix, NOT the product updater.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FILES = ("archive.py", "delivery_retry.py", "delivery_settings.py", "telegram_delivery.py",
         "google_oauth.py", "google_api.py", "google_context.py", "server.py",
         "index.html", "delivery.js", "app.js")


def state():
    with urlopen("http://127.0.0.1:43121/api/state", timeout=5) as response:
        return json.load(response)


def idle(snapshot):
    return (snapshot.get("transcript", {}).get("status") in {"idle", "finished"}
            and snapshot.get("recording_health", {}).get("capture", {}).get("audio_recording") is False)


def ready():
    if not idle(state()):
        return False
    with urlopen("http://127.0.0.1:43121/api/delivery/job", timeout=5) as response:
        return json.load(response).get("job", {}).get("state") in {"idle", "complete", "failed"}


def atomic_copy(source, target):
    stage = target.with_name(target.name + ".hotfix")
    shutil.copy2(source, stage)
    os.replace(stage, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor", type=Path, required=True, help="Verified pure-Python OAuth/Telegram _vendor tree")
    args = parser.parse_args()
    vendor = args.vendor.resolve()
    if not (vendor / "google_auth_oauthlib/flow.py").is_file() or not (vendor / "telethon/__init__.py").is_file():
        raise SystemExit("Required vendor modules missing")
    if not ready():
        raise SystemExit("Capture is active or unknown; no files changed")
    share = Path.home() / ".local/share/meeting-copilot"
    installed = share / "web"
    backup = share / "backups" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-delivery-runtime")
    backup.mkdir(parents=True, exist_ok=False, mode=0o700)
    existing = [name for name in FILES if (installed / name).is_file()]
    for name in existing:
        shutil.copy2(installed / name, backup / name)
    # Stage beside the destination on the same filesystem for rename/rollback.
    vendor_stage = backup / "new-vendor"
    shutil.copytree(vendor, vendor_stage)
    target = f"gui/{os.getuid()}/com.aiagentlbs.meeting-copilot"
    changed = False
    vendor_moved = False
    vendor_installed = False
    try:
        if not ready():
            raise RuntimeError("A meeting started; deployment cancelled")
        if (installed / "_vendor").exists():
            os.replace(installed / "_vendor", backup / "old-vendor")
            vendor_moved = True
        os.replace(vendor_stage, installed / "_vendor")
        vendor_installed = True
        for name in FILES:
            atomic_copy(ROOT / "copilot/web" / name, installed / name)
            changed = True
        subprocess.run(["launchctl", "kickstart", "-k", target], check=True)
        for attempt in range(30):
            try:
                snapshot = state()
                assert "transcript" in snapshot
                break
            except Exception:
                if attempt == 29:
                    raise RuntimeError("Service health check failed") from None
                time.sleep(1)
        for name in FILES:
            assert hashlib.sha256((ROOT / "copilot/web" / name).read_bytes()).digest() == hashlib.sha256((installed / name).read_bytes()).digest()
        for file in vendor.rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts:
                assert hashlib.sha256(file.read_bytes()).digest() == hashlib.sha256((installed / "_vendor" / file.relative_to(vendor)).read_bytes()).digest()
        print(json.dumps({"service": "healthy", "files_verified": len(FILES),
                          "capture_restarted": False, "backup": str(backup)}))
    except Exception:
        if changed or vendor_installed or vendor_moved:
            for name in FILES:
                if name in existing:
                    atomic_copy(backup / name, installed / name)
                elif (installed / name).exists():
                    os.replace(installed / name, backup / ("failed-new-" + name))
            if vendor_installed:
                os.replace(installed / "_vendor", backup / "failed-new-vendor")
            if vendor_moved:
                os.replace(backup / "old-vendor", installed / "_vendor")
            subprocess.run(["launchctl", "kickstart", "-k", target], check=True)
        raise


if __name__ == "__main__":
    main()
