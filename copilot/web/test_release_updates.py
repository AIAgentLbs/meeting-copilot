import json
from pathlib import Path
import tempfile
import threading
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import unittest

from release_updates import ReleaseUpdates, select_release, installed_release


def release(version, platform="macos", prerelease=True, **extra):
    tag = ("windows-" if platform == "windows" else "") + "v" + version
    asset = (f"meeting-copilot-windows-v{version}-x64.zip" if platform == "windows"
             else "meeting-copilot-macos.zip")
    return dict(tag_name=tag, draft=False, prerelease=prerelease,
                html_url=f"https://github.com/AIAgentLbs/meetontrack/releases/tag/{tag}",
                body="Changes\n<script>alert(1)</script>", assets=[{"name": asset}], **extra)


class ReleaseSelectionTests(unittest.TestCase):
    def test_newest_matching_platform_not_first_or_lexicographic(self):
        data = [release("0.2.0", "windows"), release("0.1.9"), release("0.1.10")]
        self.assertEqual(select_release(data, "0.1.9", "macos", "technical-beta")["version"], "0.1.10")

    def test_stable_channel_never_advertises_beta(self):
        self.assertIsNone(select_release([release("1.1.0")], "1.0.0", "macos", "stable"))

    def test_same_windows_beta_or_older_version_is_not_an_update(self):
        self.assertIsNone(select_release([release("0.1.4", "windows"), release("0.1.3", "windows")],
                                         "0.1.4-windows-beta.1", "windows", "technical-beta"))

    def test_drafts_wrong_asset_untrusted_links_and_malformed_versions_are_rejected(self):
        valid = release("2.0.0")
        for bad in [dict(valid, draft=True), dict(valid, assets=[]),
                    dict(valid, html_url="https://example.com/installer"),
                    dict(valid, tag_name="vlatest")]:
            with self.subTest(bad=bad):
                self.assertIsNone(select_release([bad], "1.0.0", "macos", "technical-beta"))

    def test_windows_manifest_is_found_next_to_web_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "web").mkdir()
            (root / "release.json").write_text(json.dumps({"version": "0.1.4-windows-beta.1", "channel": "technical-beta"}))
            self.assertEqual(installed_release(root / "web", "windows")["version"], "0.1.4-windows-beta.1")


class ReleaseMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "updates.json"
        self.calls = []
        self.now = 1000000

    def tearDown(self):
        self.tmp.cleanup()

    def monitor(self, fetch=None):
        def feed():
            self.calls.append(True)
            return [release("0.1.10")]
        return ReleaseUpdates(self.path, {"version": "0.1.9", "channel": "technical-beta", "platform": "macos"},
                              fetch=fetch or feed, clock=lambda: self.now)

    def test_polling_snapshots_never_fetch_and_checks_are_every_fifteen_minutes(self):
        monitor = self.monitor()
        for _ in range(20):
            monitor.snapshot()
        self.assertEqual(self.calls, [])
        monitor.check()
        monitor.check()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(monitor.snapshot()["latest"]["version"], "0.1.10")
        self.now += 899
        monitor.check()
        self.assertEqual(len(self.calls), 1)
        self.now += 1
        monitor.check()
        self.assertEqual(len(self.calls), 2)

    def test_dismissal_survives_restart_without_hiding_release_notes(self):
        monitor = self.monitor()
        monitor.check()
        self.assertTrue(monitor.snapshot()["notify"])
        monitor.configure({"dismiss": "0.1.10"})
        restarted = self.monitor()
        self.assertFalse(restarted.snapshot()["notify"])
        self.assertIn("Changes", restarted.snapshot()["latest"]["notes"])

    def test_disabled_checks_do_not_contact_network_but_manual_check_works(self):
        monitor = self.monitor()
        monitor.configure({"enabled": False})
        monitor.check()
        self.assertEqual(self.calls, [])
        monitor.check(force=True)
        self.assertEqual(len(self.calls), 1)

    def test_failures_keep_previous_notice_and_back_off(self):
        monitor = self.monitor()
        monitor.check()
        monitor.fetch = lambda: (_ for _ in ()).throw(OSError("offline"))
        self.now += 901
        monitor.check()
        self.assertEqual(monitor.snapshot()["latest"]["version"], "0.1.10")
        self.assertTrue(monitor.snapshot()["error"])
        monitor.fetch = lambda: self.fail("retry must wait")
        monitor.check()

    def test_failure_retry_is_five_minutes_then_exponential_bounded_at_one_hour(self):
        calls = []
        def offline():
            calls.append(True)
            raise OSError("offline")
        monitor = self.monitor(offline)
        for delay in [300, 600, 1200, 2400, 3600, 3600]:
            monitor.check()
            self.assertEqual(monitor.next_check - self.now, delay)
            count = len(calls)
            self.now += delay - 1
            monitor.check()
            self.assertEqual(len(calls), count)
            self.now += 1
        monitor.fetch = lambda: [release("0.1.10")]
        monitor.check()
        self.assertFalse(monitor.snapshot()["error"])
        self.assertEqual(monitor.next_check - self.now, 900)

    def test_restart_checks_without_waiting_for_old_cached_timestamp(self):
        monitor = self.monitor()
        monitor.check()
        restarted = self.monitor()
        restarted.check()
        self.assertEqual(len(self.calls), 2)

    def test_unknown_installed_version_does_not_offer_downgrade(self):
        monitor = ReleaseUpdates(self.path, {"version": "", "channel": "technical-beta", "platform": "macos"},
                                 fetch=lambda: self.fail("unknown version must not contact server"))
        monitor.check(force=True)
        self.assertFalse(monitor.snapshot()["notify"])

    def test_corrupt_cache_cannot_stop_background_checks(self):
        for timestamp in ["bad", 10 ** 400]:
            self.path.write_text(json.dumps({"checked_at": timestamp, "enabled": "bad", "latest": {"version": "latest"}}))
            monitor = self.monitor()
            monitor.check()
            self.assertTrue(monitor.snapshot()["notify"])

    def test_manual_requests_are_single_flight_with_immediate_checking_state(self):
        started, finish = threading.Event(), threading.Event()
        calls = []
        def fetch():
            calls.append(True)
            started.set()
            finish.wait(2)
            return [release("0.1.10")]
        monitor = self.monitor(fetch)
        try:
            worker = monitor.request_check()
            self.assertTrue(started.wait(1))
            self.assertTrue(monitor.snapshot()["checking"])
            for _ in range(20):
                monitor.request_check()
            self.assertEqual(len(calls), 1)
        finally:
            finish.set()
            worker.join(3)
            self.assertFalse(worker.is_alive())

    def test_http_settings_and_checks_preserve_origin_guard(self):
        import server
        monitor = self.monitor()
        with patch.object(server, "UPDATES", monitor):
            http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{http.server_port}"
            try:
                with urlopen(base + "/api/updates") as response:
                    self.assertEqual(json.load(response)["updates"]["version"], "0.1.9")
                request = Request(base + "/api/updates/settings", data=b'{"enabled":false}',
                                  headers={"Content-Type": "application/json", "Origin": "https://evil.example"})
                with self.assertRaises(HTTPError) as failure:
                    urlopen(request)
                self.assertEqual(failure.exception.code, 403)
                failure.exception.close()
                request.remove_header("Origin")
                with urlopen(request) as response:
                    self.assertFalse(json.load(response)["updates"]["enabled"])
                with urlopen(base + "/updates.js") as response:
                    self.assertEqual(response.status, 200)
            finally:
                http.shutdown()
                http.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
