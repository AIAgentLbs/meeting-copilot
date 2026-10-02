"""Installer regressions in temporary directories; no real app/provider changes."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="meeting-installer-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "fixture & test"
        self.root.mkdir()
        self.mock = self.root / "mock-bin"
        self.mock.mkdir()
        self.package = self.root / "package.zip"
        files = {
            "Meeting Copilot Capture.app/Contents/MacOS/MeetingCopilotCapture": "synthetic-app",
            "payload/web/server.py": "print('synthetic-server')\n",
            "payload/bin/meeting-copilot": "#!/bin/sh\nexit 0\n",
            "payload/config/SESSION.md": "synthetic-session\n",
            "payload/config/delivery.json.example": "{}\n",
            "payload/config/refresh-repos.py": "from pathlib import Path\np=Path(__file__).parent/'repos.json'\np.write_text('{\"repositories\": []}')\n",
        }
        for name in ("ZoomWindowFinder", "ZoomFrameInspector", "DetectSpeechLanguage"):
            files[f"payload/bin/{name}.swift"] = "// synthetic helper\n"
        with zipfile.ZipFile(self.package, "w") as handle:
            for name, body in files.items():
                handle.writestr(name, body)
        self.env = os.environ | {
            "PATH": f"{self.mock}:/usr/bin:/bin:/usr/sbin:/sbin",
            "MEETING_COPILOT_ASSET_URL": "https://example.invalid/synthetic.zip",
            "MEETING_COPILOT_ASSET_SHA256": hashlib.sha256(self.package.read_bytes()).hexdigest(),
            "MEETING_COPILOT_APP_ROOT": str(self.root / "Applications"),
            "MEETING_COPILOT_SHARE_ROOT": str(self.root / "share"),
            "MEETING_COPILOT_CONFIG_ROOT": str(self.root / "config"),
            "MEETING_COPILOT_BIN_ROOT": str(self.root / "bin"),
            "MEETING_COPILOT_AGENTS_ROOT": str(self.root / "agents"),
            "MEETING_COPILOT_SKIP_LAUNCH": "1",
            "FIXTURE_PACKAGE": str(self.package), "FIXTURE_ROOT": str(self.root),
        }
        Path(self.env["MEETING_COPILOT_APP_ROOT"]).mkdir()
        (self.mock / "python3").symlink_to(sys.executable)
        self.script("uname", 'if [ "$1" = -s ]; then echo "${MOCK_OS:-Darwin}"; else echo "${MOCK_ARCH:-arm64}"; fi')
        self.script("sw_vers", 'echo "${MOCK_VERSION:-15.0}"')
        self.script("codex", 'exit "${MOCK_CODEX_EXIT:-0}"')
        self.script("pgrep", 'if [ "${MOCK_CAPTURE:-0}" = 1 ]; then echo 999; exit 0; fi\nif [ "${MOCK_CAPTURE_AFTER_STAGE:-0}" = 1 ] && [ -f "$FIXTURE_ROOT/compiled" ]; then echo 999; exit 0; fi\nexit 1')
        self.script("curl", 'touch "$FIXTURE_ROOT/downloaded"\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then cp "$FIXTURE_PACKAGE" "$2"; exit 0; fi; shift; done\nexit 2')
        self.script("swiftc", 'if [ "$1" = --version ]; then exit 0; fi\n[ "${MOCK_COMPILE_FAIL:-0}" = 0 ] || exit 1\ntouch "$FIXTURE_ROOT/compiled"\nwhile [ "$#" -gt 0 ]; do if [ "$1" = -o ]; then printf "synthetic-helper\\n" > "$2"; exit 0; fi; shift; done\nexit 2')
        for name in ("open", "launchctl"):
            self.script(name, 'touch "$FIXTURE_ROOT/unexpected-launch"\nexit 99')

    def script(self, name, body):
        path = self.mock / name
        path.write_text("#!/bin/bash\nset -eu\n" + body + "\n")
        path.chmod(0o755)

    def run_install(self, **environment):
        return subprocess.run(["/bin/bash", str(ROOT / "install.sh")], env=self.env | environment,
                              text=True, capture_output=True, timeout=30)

    def seed_existing(self):
        app = Path(self.env["MEETING_COPILOT_APP_ROOT"]) / "Meeting Copilot Capture.app"
        app.mkdir()
        (app / "previous").write_text("previous-app")
        share, config = Path(self.env["MEETING_COPILOT_SHARE_ROOT"]), Path(self.env["MEETING_COPILOT_CONFIG_ROOT"])
        (share / "web").mkdir(parents=True)
        (share / "web/previous").write_text("previous-web")
        (share / "recordings").mkdir()
        (share / "recordings/keep.txt").write_text("synthetic-recording")
        config.mkdir()
        (config / "delivery.json").write_text("synthetic-private-settings")
        (config / "SESSION.md").write_text("keep-session")
        (config / "active-repos.json").write_text('{"repositories": ["keep-selection"]}')
        return app, share, config

    def test_fresh_install_and_escaped_launchagent(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        share = Path(self.env["MEETING_COPILOT_SHARE_ROOT"])
        self.assertTrue((share / "web/server.py").is_file())
        self.assertTrue((share / "bin/detect-speech-language").is_file())
        agent = Path(self.env["MEETING_COPILOT_AGENTS_ROOT"]) / "com.aiagentlbs.meeting-copilot.plist"
        config = plistlib.loads(agent.read_bytes())
        self.assertEqual(config["ProgramArguments"][1], str(share / "web/server.py"))
        self.assertIn(self.env["MEETING_COPILOT_BIN_ROOT"], config["EnvironmentVariables"]["PATH"])
        self.assertFalse((self.root / "unexpected-launch").exists())

    def test_reinstall_preserves_data_and_backups(self):
        app, share, config = self.seed_existing()
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((app / "Contents/MacOS/MeetingCopilotCapture").is_file())
        self.assertEqual(len(list(app.parent.glob("Meeting Copilot Capture.backup-*.app/previous"))), 1)
        self.assertEqual(len(list(share.glob("web.backup-*/previous"))), 1)
        self.assertEqual((share / "recordings/keep.txt").read_text(), "synthetic-recording")
        self.assertEqual((config / "delivery.json").read_text(), "synthetic-private-settings")
        self.assertEqual((config / "SESSION.md").read_text(), "keep-session")
        self.assertEqual(json.loads((config / "active-repos.json").read_text())["repositories"], ["keep-selection"])

    def test_checksum_failure_never_replaces_app(self):
        app, share, _ = self.seed_existing()
        result = self.run_install(MEETING_COPILOT_ASSET_SHA256="0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stderr)
        self.assertTrue((app / "previous").is_file())
        self.assertTrue((share / "web/previous").is_file())
        self.assertFalse((self.root / "compiled").exists())

    def test_compile_failure_never_replaces_app(self):
        app, _, _ = self.seed_existing()
        result = self.run_install(MOCK_COMPILE_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((app / "previous").is_file())

    def test_running_capture_blocks_before_download(self):
        app, _, _ = self.seed_existing()
        result = self.run_install(MOCK_CAPTURE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Quit Meeting Copilot Capture", result.stderr)
        self.assertTrue((app / "previous").is_file())
        self.assertFalse((self.root / "downloaded").exists())

    def test_capture_started_during_staging_is_also_protected(self):
        app, _, _ = self.seed_existing()
        result = self.run_install(MOCK_CAPTURE_AFTER_STAGE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Quit Meeting Copilot Capture", result.stderr)
        self.assertTrue((app / "previous").is_file())

    def test_platform_and_dependency_failures_stop_before_download(self):
        for environment in ({"MOCK_OS": "Linux"}, {"MOCK_ARCH": "x86_64"},
                            {"MOCK_VERSION": "14.7"}, {"MOCK_CODEX_EXIT": "1"}):
            with self.subTest(environment=environment):
                result = self.run_install(**environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.root / "downloaded").exists())

    def test_alternate_download_requires_explicit_digest(self):
        self.env.pop("MEETING_COPILOT_ASSET_SHA256")
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("alternate asset URL requires", result.stderr)
        self.assertFalse((self.root / "downloaded").exists())


if __name__ == "__main__":
    unittest.main()
