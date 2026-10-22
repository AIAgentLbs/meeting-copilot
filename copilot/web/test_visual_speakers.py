import tempfile
import unittest
from pathlib import Path

from server import MeetingFrames


def frame(at, speaker):
    return {"meeting_id": "m", "captured_at": f"2026-10-22T10:{at}Z",
            "speaker": speaker, "speaker_confidence": "visual-active-speaker"}


def phrase(at, voice="remote-1"):
    return {"source": "system", "voice_id": voice, "timestamp": f"2026-10-22T10:{at}Z", "text": "x"}


class VisualSpeakerTests(unittest.TestCase):
    def annotate(self, items, segments):
        with tempfile.TemporaryDirectory() as directory:
            frames = MeetingFrames(Path(directory) / "frames.json")
            frames.items = items
            return [s.get("speaker") for s in frames.annotate({"meeting_id": "m", "segments": segments})["segments"]]

    def test_single_undiarized_voice_is_named_per_phrase(self):
        names = self.annotate([frame("00:00", "Alice"), frame("01:00", "Bob")],
                              [phrase("00:02"), phrase("01:03"), phrase("00:05")])
        self.assertEqual(names, ["Alice", "Bob", "Alice"])

    def test_diarized_voices_keep_one_name_per_voice(self):
        names = self.annotate(
            [frame("00:00", "Alice"), frame("01:00", "Bob")],
            [phrase("00:02", "remote-1"), phrase("01:03", "remote-2"),
             phrase("05:00", "remote-1"), phrase("06:00", "remote-2")])
        self.assertEqual(names, ["Alice", "Bob", "Alice", "Bob"])

    def blank_frame(self, directory):
        from PIL import Image
        path = Path(directory) / "frame.jpg"
        Image.new("RGB", (400, 300), (40, 40, 40)).save(path)
        return path

    def test_floating_zoom_window_names_active_speaker(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MeetingFrames._speaker_from_frame(self.blank_frame(directory), [
                {"text": "°. app.zoom.us", "y": 0.866, "x": 0.084},
                {"text": "Mike Shishkin", "x": 0.066, "y": 0.113, "width": 0.18},
            ])
        self.assertEqual(result, ("Mike Shishkin", "zoom-floating-speaker"))

    def test_full_zoom_window_toolbar_is_not_a_speaker(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MeetingFrames._speaker_from_frame(self.blank_frame(directory), [
                {"text": "app.zoom.us/wc/81234567890/start", "y": 0.95, "x": 0.1},
                {"text": "Unmute", "x": 0.02, "y": 0.03, "width": 0.05},
                {"text": "Video", "x": 0.08, "y": 0.03, "width": 0.05},
            ])
        self.assertEqual(result, ("", ""))


if __name__ == "__main__":
    unittest.main()
