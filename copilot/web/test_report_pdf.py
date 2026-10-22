"""MEETONTRACK-98: Chrome printing a long report with many frames.

On 2026-10-22 Chrome needed about 20 s for such reports under the server's
load; the old fixed 20 s window then failed every one of them, again every
minute. Time and Chrome are faked here, so the test runs instantly.
"""

import re
import tempfile
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

        def sleep(seconds):
            clock[0] += seconds
        with patch.object(archive.Path, "is_file", lambda self: True if "Google Chrome" in str(self) else Path.exists(self)), \
             patch.object(archive.time, "sleep", sleep), patch.object(archive.time, "monotonic", lambda: clock[0]), \
             patch.object(archive.subprocess, "Popen", lambda command, **_: SlowChrome(clock, delay, command)):
            MeetingArchive._print_pdf(html, pdf)
        return pdf

    def test_a_report_chrome_needs_25_seconds_for_still_gets_its_pdf(self):
        self.assertTrue(self.print_with(25).read_bytes().startswith(b"%PDF"))

    def test_chrome_that_never_writes_a_pdf_still_fails_plainly(self):
        with self.assertRaisesRegex(RuntimeError, "Chrome не создал PDF"):
            self.print_with(10_000)


if __name__ == "__main__":
    unittest.main()
