"""Notification-only release checks. Never downloads, installs or restarts code."""
from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import re
import sys
import tempfile
import threading
import time
from urllib.request import Request, urlopen

REPOSITORY = "AIAgentLbs/meeting-copilot"
RELEASE_URL = f"https://github.com/{REPOSITORY}/releases/tag/"
INTERVAL = 86400


def version_key(value):
    match = re.fullmatch(r"(?:windows-)?v?(\d+)\.(\d+)\.(\d+)(?:-windows-beta\.\d+)?", str(value))
    return tuple(map(int, match.groups())) if match else None


def select_release(releases, current, platform, channel):
    current_key = version_key(current)
    if current_key is None or not isinstance(releases, list):
        return None
    candidates = []
    for item in releases[:100]:
        if not isinstance(item, dict) or item.get("draft") or (item.get("prerelease") and channel != "technical-beta"):
            continue
        tag = str(item.get("tag_name", ""))
        key = version_key(tag)
        if key is None or key <= current_key or tag.startswith("windows-") != (platform == "windows"):
            continue
        expected = f"meeting-copilot-windows-v{'.'.join(map(str, key))}-x64.zip" if platform == "windows" else "meeting-copilot-macos.zip"
        assets = item.get("assets")
        if not isinstance(assets, list) or not any(isinstance(asset, dict) and asset.get("name") == expected for asset in assets):
            continue
        if item.get("html_url") != RELEASE_URL + tag:
            continue
        candidates.append((key, {"version": ".".join(map(str, key)), "url": RELEASE_URL + tag,
                                  "notes": str(item.get("body") or "")[:20000], "prerelease": bool(item.get("prerelease"))}))
    return max(candidates, key=lambda entry: entry[0])[1] if candidates else None


def installed_release(web_dir: Path, platform=None):
    platform = platform or ("windows" if sys.platform == "win32" else "macos")
    try:
        data = json.loads((web_dir.parent / "release.json").read_text())
        if version_key(data.get("version")):
            return {"version": data["version"], "channel": data.get("channel", "stable"), "platform": platform}
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    if platform == "macos":
        for root in (Path("/Applications"), Path.home() / "Applications"):
            try:
                with (root / "Meeting Copilot Capture.app/Contents/Info.plist").open("rb") as handle:
                    data = plistlib.load(handle)
                value = data.get("CFBundleShortVersionString", "")
                if version_key(value):
                    return {"version": value, "channel": "technical-beta", "platform": platform}
            except (OSError, ValueError):
                pass
    return {"version": "", "channel": "stable", "platform": platform}


def fetch_releases():
    request = Request(f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100",
                      headers={"Accept": "application/vnd.github+json", "User-Agent": "MeetOnTrack-update-check"})
    with urlopen(request, timeout=10) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Release feed too large")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Invalid release feed")
    return data


class ReleaseUpdates:
    def __init__(self, path, identity, fetch=fetch_releases, clock=time.time):
        self.path, self.identity, self.fetch, self.clock = Path(path), identity, fetch, clock
        self.lock = threading.RLock()
        self.busy = False
        self.error = False
        self.data = {"enabled": True, "checked_at": 0, "dismissed": "", "latest": None}
        try:
            saved = json.loads(self.path.read_text())
            if isinstance(saved, dict):
                if isinstance(saved.get("enabled"), bool):
                    self.data["enabled"] = saved["enabled"]
                checked = saved.get("checked_at", 0)
                if isinstance(checked, (float, int)) and 0 <= checked <= self.clock():
                    self.data["checked_at"] = checked
                self.data["dismissed"] = str(saved.get("dismissed", ""))[:60]
                self.data["latest"] = saved.get("latest")
                latest = self.data["latest"]
                # Cached metadata is untrusted too; never return arbitrary external links.
                if latest:
                    tag = ("windows-" if identity["platform"] == "windows" else "") + "v" + str(latest.get("version", ""))
                    if not version_key(latest.get("version")) or latest.get("url") != RELEASE_URL + tag or not version_key(identity.get("version")) or version_key(latest["version"]) <= version_key(identity["version"]) or (latest.get("prerelease") and identity["channel"] != "technical-beta"):
                        self.data["latest"] = None
                    else:
                        self.data["latest"] = {"version": latest["version"], "url": latest["url"], "notes": str(latest.get("notes", ""))[:20000], "prerelease": bool(latest.get("prerelease"))}
        except (OSError, ValueError, TypeError, AttributeError):
            self.data["latest"] = None

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=".updates-", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w") as handle:
                json.dump(self.data, handle)
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def snapshot(self):
        with self.lock:
            latest = self.data["latest"]
            return {**self.identity, **self.data, "checking": self.busy, "error": self.error,
                    "notify": bool(self.data["enabled"] and latest and latest["version"] != self.data["dismissed"])}

    def configure(self, payload):
        with self.lock:
            if "enabled" in payload:
                if not isinstance(payload["enabled"], bool):
                    raise ValueError("enabled must be a boolean")
                self.data["enabled"] = payload["enabled"]
            if "dismiss" in payload:
                self.data["dismissed"] = str(payload["dismiss"])[:60]
            self._save()
        return self.snapshot()

    def check(self, force=False):
        with self.lock:
            if self.busy or not version_key(self.identity.get("version")):
                return
            if not force and (not self.data["enabled"] or self.clock() - float(self.data["checked_at"] or 0) < INTERVAL):
                return
            self.busy = True
        self._perform_check()

    def _perform_check(self):
        try:
            latest = select_release(self.fetch(), self.identity["version"], self.identity["platform"], self.identity["channel"])
            with self.lock:
                self.data["latest"] = latest
                self.error = False
        except Exception:
            with self.lock:
                self.error = True
        finally:
            with self.lock:
                self.busy = False
                self.data["checked_at"] = self.clock()
                try:
                    self._save()
                except OSError:
                    self.error = True

    def request_check(self):
        with self.lock:
            if self.busy or not version_key(self.identity.get("version")):
                return
            self.busy = True
        worker = threading.Thread(target=self._perform_check, daemon=True, name="release-check")
        worker.start()
        return worker

    def loop(self, stop):
        # Separate from transcript/state polling; no meeting data is sent.
        while not stop.wait(30):
            self.check()
            if stop.wait(3570):
                return
