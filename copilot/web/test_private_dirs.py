"""MEETONTRACK-84: a folder made by an elevated run must not lock out the normal session."""
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from private_dirs import private_dir

HERE = Path(__file__).parent


class PrivateDirTests(unittest.TestCase):
    def test_every_private_folder_goes_through_the_helper(self):
        # mkdir(mode=0o700) on Windows/Python 3.13 writes the owner-only ACL that broke the archive.
        offenders = [f"{path.name}:{number}"
                     for path in sorted(HERE.glob("*.py"))
                     if not path.name.startswith("test_") and path.name != "private_dirs.py"
                     for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                     if re.search(r"mkdir\([^)]*0o700", line)]
        self.assertEqual(offenders, [])

    def test_windows_folder_inherits_instead_of_owner_only_mode(self):
        with tempfile.TemporaryDirectory() as tmp, patch("private_dirs.WINDOWS", True), \
                patch.object(Path, "mkdir", autospec=True, side_effect=Path.mkdir) as mkdir:
            private_dir(Path(tmp) / "archive" / "meeting")
        self.assertTrue(mkdir.called)
        self.assertTrue(all("mode" not in call.kwargs for call in mkdir.call_args_list))

    def test_windows_locked_folder_is_moved_aside_and_made_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "archive"
            archive.mkdir()
            (archive / "kept.json").write_text("{}")
            real = os.scandir

            def locked(path):
                if Path(path) == archive and (archive / "kept.json").exists():
                    raise PermissionError(5, "Access is denied", str(path))
                return real(path)
            # The ctypes rename is Windows-only (proven on Windows); the flow is checked here.
            with patch("private_dirs.WINDOWS", True), patch("private_dirs.os.scandir", side_effect=locked), \
                    patch("private_dirs._move_aside", side_effect=os.rename):
                self.assertEqual(private_dir(archive, recover=True), archive)
            self.assertEqual(list(archive.iterdir()), [])
            aside = [item for item in Path(tmp).iterdir() if item.name.startswith("archive.inaccessible-")]
            self.assertEqual(len(aside), 1)
            self.assertTrue((aside[0] / "kept.json").exists())

    def test_windows_settings_folder_is_never_replaced(self):
        # Replacing ~/.config/meeting-copilot would silently drop other writers' keys.
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "meeting-copilot"
            config.mkdir()
            denied = PermissionError(5, "Access is denied", str(config))
            with patch("private_dirs.WINDOWS", True), patch("private_dirs.os.scandir", side_effect=denied), \
                    patch("private_dirs._move_aside") as move:
                private_dir(config)
            move.assert_not_called()

    def test_archive_recovers_its_own_roots_only(self):
        import archive
        with tempfile.TemporaryDirectory() as tmp, patch("archive.private_dir") as made:
            root = Path(tmp)
            archive.MeetingArchive(root / "recordings", root / "archive", root / "reports", root / "config")
        recovered = {call.args[0].name for call in made.call_args_list if call.kwargs.get("recover")}
        self.assertEqual(recovered, {"archive", "reports"})

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_posix_folder_stays_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = private_dir(Path(tmp) / "keys")
            self.assertEqual(folder.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
