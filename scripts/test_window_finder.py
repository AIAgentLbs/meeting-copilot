"""Replay synthetic macOS window metadata; never inspect the user's windows."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("swiftc"), "macOS Swift helper")
class WindowFinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.binaries = []
        for directory in ("bin", "web"):
            binary = Path(cls.tmp.name) / directory
            source = Path(__file__).resolve().parents[1] / f"copilot/{directory}/ZoomWindowFinder.swift"
            subprocess.run(["swiftc", str(source), "-o", str(binary)], check=True, capture_output=True)
            cls.binaries.append(binary)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_new_and_legacy_product_windows_are_never_selected_as_calls(self):
        def window(identity, title):
            return {"kCGWindowNumber": identity, "kCGWindowOwnerName": "Google Chrome", "kCGWindowName": title,
                    "kCGWindowLayer": 0, "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1000, "Height": 800}}
        for title in ["MeetOnTrack by aiagentlbs.com", "Meeting Copilot by aiagentlbs.com"]:
            for binary in self.binaries:
                result = subprocess.run([str(binary), "--input-json"], text=True, capture_output=True,
                                        input=json.dumps([window(1, title), window(2, "Team meeting")]), timeout=5)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stdout)["id"], 2)


if __name__ == "__main__":
    unittest.main()
