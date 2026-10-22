"""MEETONTRACK-98: Chrome printing a long report with many frames.

On 2026-10-22 Chrome needed about 20 s for such reports under the server's
load; the old fixed 20 s window then failed every one of them, again every
minute. Time and Chrome are faked here, so the test runs instantly.
"""

import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import archive
from archive import MeetingArchive


class SlowChrome:
    """Writes the PDF after `delay` seconds of the fake clock, then exits 3 s later."""

    def __init__(self, clock: list[float], delay: float, command: list[str]):
        self.clock, self.delay, self.started = clock, delay, clock[0]
        self.target = Path(next(re.sub("^--print-to-pdf=", "", a) for a in command if a.startswith("--print-to-pdf=")))

    def poll(self):
        elapsed = self.clock[0] - self.started
        if elapsed >= self.delay and not self.target.exists():
            self.target.write_bytes(b"%PDF" + b"0" * 10000)
        return 0 if elapsed >= self.delay + 3 else None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


class PrintPdfTests(unittest.TestCase):
    def print_with(self, delay: float) -> Path:
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        html, pdf = folder / "index.html", folder / "meeting-report.pdf"
        html.write_text("<p>synthetic</p>")
        clock = [1000.0]
        self.profiles = folder / "tmp"
        self.profiles.mkdir()

        def sleep(seconds):
            clock[0] += seconds
        with patch.object(archive.Path, "is_file", lambda self: True if "Google Chrome" in str(self) else Path.exists(self)), \
             patch.object(archive.time, "sleep", sleep), patch.object(archive.time, "monotonic", lambda: clock[0]), \
             patch.object(archive.subprocess, "Popen", lambda command, **_: SlowChrome(clock, delay, command)), \
             patch.object(archive.tempfile, "tempdir", str(self.profiles)):
            MeetingArchive._print_pdf(html, pdf)
        return pdf

    def test_a_report_chrome_needs_25_seconds_for_still_gets_its_pdf(self):
        self.assertTrue(self.print_with(25).read_bytes().startswith(b"%PDF"))

    def test_chrome_that_never_writes_a_pdf_still_fails_plainly(self):
        with self.assertRaisesRegex(archive.ReportPdfError, "Chrome не создал PDF"):
            self.print_with(10_000)

    def test_chrome_profile_is_removed_after_each_print(self):
        self.print_with(5)
        self.assertEqual(list(self.profiles.iterdir()), [])

    def test_start_removes_only_this_apps_leftover_profiles(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(folder, ignore_errors=True))
        (folder / f"{archive.PRINT_PROFILE_PREFIX}old1" / "Default").mkdir(parents=True)
        (folder / f"{archive.PRINT_PROFILE_PREFIX}old2").mkdir()
        (folder / "other-app-report-1").mkdir()
        (folder / f"{archive.PRINT_PROFILE_PREFIX}note.txt").write_text("not a folder")
        with patch.object(archive.tempfile, "tempdir", str(folder)):
            self.assertEqual(MeetingArchive.remove_print_leftovers(), 2)
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         [f"{archive.PRINT_PROFILE_PREFIX}note.txt", "other-app-report-1"])


class PrintOutsideTheLockTests(unittest.TestCase):
    """A slow print must not stall the library, and one meeting prints once at a time."""

    def setUp(self):
        from test_final_after_next_call import FinalTranscriptAfterNextCallTests
        case = FinalTranscriptAfterNextCallTests("test_dropout_in_the_last_minute_is_explained_not_flagged")
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.next_call_ends()
        self.case, self.archive = case, case.archive
        self.printing, self.release = threading.Event(), threading.Event()
        self.prints = 0

        def slow_print(html, pdf):
            self.prints += 1
            self.printing.set()
            self.assertTrue(self.release.wait(10))
            pdf.write_bytes(b"%PDF synthetic")
        patcher = patch.object(self.archive, "_print_pdf", side_effect=slow_print)
        patcher.start()
        self.addCleanup(patcher.stop)
        delivery = patch.object(self.archive, "deliver", return_value={"mail_status": "sent"})
        delivery.start()
        self.addCleanup(delivery.stop)

    def start(self) -> threading.Thread:
        worker = threading.Thread(target=self.archive.generate_report, args=("FIRST-CALL",))
        worker.start()
        return worker

    def test_the_library_answers_while_chrome_prints(self):
        worker = self.start()
        self.assertTrue(self.printing.wait(5))
        answered = []
        # Renaming takes the archive lock, like settings, resends and summaries.
        reader = threading.Thread(target=lambda: answered.append((self.archive.list_meetings(),
                                                                   self.archive.rename_meeting("NEXT-CALL", "Renamed"))))
        reader.start()
        reader.join(5)
        self.assertTrue(answered, "The library waited for Chrome")
        self.assertTrue(self.archive.delivery_health() is not None)
        self.release.set()
        worker.join(10)
        self.assertTrue((self.case.root / "reports/FIRST-CALL/report.json").exists())

    def test_a_second_request_for_the_same_meeting_waits_for_the_first(self):
        first = self.start()
        self.assertTrue(self.printing.wait(5))
        second = self.start()
        second.join(0.5)
        self.assertEqual(self.prints, 1, "Two Chrome prints of one meeting at once")
        self.release.set()
        first.join(10)
        second.join(10)
        self.assertEqual(self.prints, 2)

    def test_text_changed_during_the_print_is_printed_again_before_saving(self):
        worker = self.start()
        self.assertTrue(self.printing.wait(5))
        stored = json.loads((self.case.root / "archive/FIRST-CALL/meeting.json").read_text())
        stored["segments"].append({"source": "system", "timestamp": stored["segments"][-1]["timestamp"],
                                   "text": "Added while printing"})
        (self.case.root / "archive/FIRST-CALL/meeting.json").write_text(json.dumps(stored))
        self.release.set()
        worker.join(10)
        self.assertEqual(self.prints, 2)
        report = json.loads((self.case.root / "reports/FIRST-CALL/report.json").read_text())
        self.assertEqual(report["source_signature"], self.archive.source_signature(self.archive.report_detail("FIRST-CALL")))

    def backdate(self, marker: Path) -> None:
        from datetime import datetime, timedelta, timezone
        failure = json.loads(marker.read_text())
        marker.write_text(json.dumps({**failure, "failed_at": (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()}))

    def fail_once(self, meeting_id: str) -> None:
        with patch.object(self.archive, "_print_pdf", side_effect=archive.ReportPdfError("Chrome не создал PDF")):
            with self.assertRaises(archive.ReportPdfError):
                self.archive.generate_report(meeting_id)

    def test_chunks_of_one_call_share_one_report_job_and_one_failure(self):
        from datetime import timedelta
        from test_final_after_next_call import iso
        case = self.case
        early = case.start - timedelta(minutes=30)
        chunk = case.recording("2026.10.22-1530 Google Chrome Helper (Ap", early, case.start - timedelta(seconds=30))
        self.archive.sync_transcript({**case.live, "meeting": "Synthetic sync"})  # Same title: one call.
        self.archive.sync_transcript({**case.live, "meeting": "Synthetic sync", "meeting_id": "EARLY-CHUNK",
                                      "started_at": iso(early), "updated_at": iso(case.start - timedelta(seconds=30)),
                                      "capture_warnings": [], "recording_dir": str(chunk), "segments": [
                                          {"source": "system", "timestamp": iso(early + timedelta(seconds=1)), "text": "Chunk"}]})
        self.assertEqual(self.archive.report_identity("EARLY-CHUNK"), "FIRST-CALL")
        first = threading.Thread(target=self.archive.generate_report, args=("EARLY-CHUNK",))
        first.start()
        self.assertTrue(self.printing.wait(5))
        second = self.start()
        second.join(0.5)
        self.assertEqual(self.prints, 1, "Two prints into one report folder at once")
        self.release.set()
        first.join(10)
        second.join(10)
        self.assertEqual(self.prints, 2)
        self.fail_once("EARLY-CHUNK")
        self.assertTrue((case.root / "reports/FIRST-CALL/report-failure.json").exists())
        self.assertFalse((case.root / "reports/EARLY-CHUNK/report-failure.json").exists())

    def test_a_failed_refresh_of_a_current_report_clears_itself_after_30_minutes(self):
        self.release.set()
        self.archive.finalize_history()  # Imports the final transcript and creates the report.
        self.assertEqual(self.prints, 1)
        marker = self.case.root / "reports/FIRST-CALL/report-failure.json"
        self.fail_once("FIRST-CALL")  # The person's button, while the saved report is still current.
        self.backdate(marker)
        prints = self.prints
        self.archive.finalize_history()
        self.assertFalse(marker.exists(), "The report on disk is current: the failure must not stay forever")
        self.assertEqual(self.prints, prints)

    def test_an_expired_failure_without_any_report_is_tried_again(self):
        marker = self.case.root / "reports/FIRST-CALL/report-failure.json"
        self.fail_once("FIRST-CALL")
        self.backdate(marker)
        self.release.set()
        self.archive.finalize_history()
        self.assertFalse(marker.exists())
        self.assertTrue((self.case.root / "reports/FIRST-CALL/report.json").exists())


if __name__ == "__main__":
    unittest.main()
