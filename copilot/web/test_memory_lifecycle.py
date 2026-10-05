import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from live_translation import LiveTranslation


class MemoryLifecycleTests(unittest.TestCase):
    def test_copilot_messages_match_existing_persisted_retention_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "copilot.json"
            session = server.CodexSession(path)
            session.messages = [{"role": "assistant", "meeting_id": "one", "text": str(i)} for i in range(250)]
            session._persist_locked()
            self.assertEqual(len(session.messages), 100)
            self.assertEqual(session.messages[0]["text"], "150")
            self.assertEqual(json.loads(path.read_text())["messages"], session.messages)

    def test_archive_reuses_live_frames_without_retaining_second_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = [{"meeting_id": "one", "id": "retained"}]
            archive = server.MeetingArchive(root / "recordings", root / "archive", root / "reports", root, frames_provider=lambda: list(items))
            with patch.object(Path, "read_text", side_effect=AssertionError("frame index reread")):
                self.assertEqual(archive.frames, items)
                items.append({"meeting_id": "two", "id": "new"})
                self.assertEqual(len(archive.frames), 2)

    def test_active_capture_does_not_build_reports_or_scan_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = server.MeetingArchive(root / "recordings", root / "archive", root / "reports", root)
            marker = root / "recordings" / "active" / ".recording.json"
            marker.parent.mkdir(parents=True)
            marker.write_text("{}")
            with patch.object(archive, "report_detail", side_effect=AssertionError("active archive scan")):
                self.assertFalse(archive.needs_report("one"))

    def test_report_chain_reads_shared_indexes_once_and_refreshes_next_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = server.MeetingArchive(root / "recordings", root / "archive", root / "reports", root)
            for index in range(8):
                target = root / "archive" / str(index) / "meeting.json"
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps({"meeting_id": str(index), "meeting": "Synthetic", "status": "finished", "segments": []}))
            frames_path = root / "frames.json"
            frames_path.write_text(json.dumps({"items": [{"meeting_id": "0", "id": "first"}]}))
            original = Path.read_text
            reads = []
            def read(path, *args, **kwargs):
                if path == frames_path:
                    reads.append(path)
                return original(path, *args, **kwargs)
            with patch.object(Path, "read_text", read):
                self.assertEqual(archive.report_detail("0")["frames"][0]["id"], "first")
                self.assertEqual(len(reads), 1)
                frames_path.write_text(json.dumps({"items": [{"meeting_id": "0", "id": "second"}]}))
                self.assertEqual(archive.report_detail("0")["frames"][0]["id"], "second")
                self.assertEqual(len(reads), 2)

    def test_repository_count_reuses_unchanged_file_and_detects_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repos.json"
            path.write_text(json.dumps({"repositories": [{"name": "one"}]}))
            self.assertEqual(server.repository_count(path), 1)
            with patch.object(Path, "read_text", side_effect=AssertionError("unchanged file reread")):
                self.assertEqual(server.repository_count(path), 1)
            path.write_text(json.dumps({"repositories": [{"name": "one"}, {"name": "two"}]}))
            self.assertEqual(server.repository_count(path), 2)
    def test_unchanged_export_does_not_reparse_or_replace_speech(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live.json"
            payload = {"version": 1, "source": "meeting-copilot", "meeting_id": "one", "status": "recording", "segments": [{"source": "system", "timestamp": "2026-10-05T10:00:00Z", "text": "Original speech"}]}
            path.write_text(json.dumps(payload))
            state = server.TranscriptState(path)
            state.refresh()
            original = state.segments
            for _ in range(20):
                state.refresh()
            self.assertIs(state.segments, original)
            payload["segments"][0]["text"] = "Changed speech"
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload))
            temporary.replace(path)
            state.refresh()
            self.assertEqual(state.snapshot()["segments"][0]["text"], "Changed speech")

    def test_recovery_change_invalidates_unchanged_live_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "live.json"
            path.write_text(json.dumps({"version": 1, "source": "meeting-copilot", "meeting_id": "one", "status": "finished", "segments": []}))
            with patch.object(server, "RECOVERED_TRANSCRIPTS_ROOT", root):
                state = server.TranscriptState(path)
                state.refresh()
                (root / "one.json").write_text(json.dumps({"meeting_id": "one", "segments": [{"source": "system", "timestamp": "2026-10-05T10:00:00Z", "text": "Recovered tail"}]}))
                state.refresh()
                self.assertEqual(state.snapshot()["segments"][0]["text"], "Recovered tail")

    def test_annotations_are_not_recomputed_for_unchanged_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = server.TranscriptState(root / "live.json")
            frames = server.MeetingFrames(root / "frames.json")
            archive = server.MeetingArchive(root / "recordings", root / "archive", root / "reports", root)
            translator = LiveTranslation()
            self.addCleanup(lambda: translator.pool.shutdown(wait=True, cancel_futures=True))
            with patch.object(server, "TRANSCRIPT", state), patch.object(server, "FRAMES", frames), patch.object(server, "ARCHIVE", archive), patch.object(server, "TRANSLATIONS", translator):
                before = server.annotated_snapshot()
                after = server.annotated_snapshot()
                self.assertEqual(before["segments"], after["segments"])
                self.assertEqual(server.ANNOTATED_CACHE.builds, 1)

    def test_state_title_uses_existing_frame_index_without_disk_reparse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = server.MeetingArchive(root / "recordings", root / "archive", root / "reports", root)
            self.assertEqual(archive.display_title({"meeting_id": "one", "meeting": "Zoom"}, frames=[{"window_title": "Customer call"}]), "Customer call")

    def test_old_meeting_translation_results_released(self):
        translator = LiveTranslation()
        self.addCleanup(lambda: translator.pool.shutdown(wait=True, cancel_futures=True))
        with patch.object(translator, "_language", return_value=("ru", 1.0)):
            for meeting in range(8):
                snapshot = {"meeting_id": str(meeting), "status": "recording", "segments": [{"source": "system", "timestamp": "2026-10-05T10:00:00Z", "text": "Meaningful synthetic speech"}]}
                translator.annotate(snapshot)
                deadline = time.monotonic() + 2
                while translator.pending and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(len(translator.results), 1)

    def test_translation_work_queue_is_bounded(self):
        translator = LiveTranslation()
        self.addCleanup(lambda: translator.pool.shutdown(wait=True, cancel_futures=True))
        from threading import Event
        release = Event()
        self.addCleanup(release.set)
        with patch.object(translator, "_language", side_effect=lambda _: (release.wait(1), ("ru", 1.0))[1]):
            translator.annotate({"meeting_id": "one", "segments": [{"source": "system", "timestamp": str(i), "text": "Meaningful synthetic speech"} for i in range(100)]})
            self.assertLessEqual(len(translator.pending), 4)
            release.set()
