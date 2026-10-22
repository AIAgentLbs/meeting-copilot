import tempfile
import unittest
from pathlib import Path

from server import MeetingFrames
from speaker_edits import SpeakerEdits


def frame(at, speaker):
    return {"meeting_id": "m", "captured_at": f"2026-10-22T10:{at}Z",
            "speaker": speaker, "speaker_confidence": "visual-active-speaker"}


def phrase(at, voice="remote-1", until=None, text="x", source="system"):
    segment = {"source": source, "timestamp": f"2026-10-22T10:{at}Z", "text": text}
    if voice and source == "system":
        segment["voice_id"] = voice
    if until:
        segment["end_timestamp"] = f"2026-10-22T10:{until}Z"
    return segment


class VisualSpeakerTests(unittest.TestCase):
    def annotate(self, items, segments, field="speaker"):
        with tempfile.TemporaryDirectory() as directory:
            frames = MeetingFrames(Path(directory) / "frames.json")
            frames.items = items
            annotated = frames.annotate({"meeting_id": "m", "segments": segments})
            # Same path as the live UI: speaker labels are grouped after annotation.
            labelled = SpeakerEdits(Path(directory) / "archive").annotate(annotated)
            return [s.get(field) for s in labelled["segments"] if s.get("source") == "system"]

    def test_single_undiarized_voice_is_named_per_phrase(self):
        items = [frame("00:00", "Alice"), frame("01:00", "Bob")]
        segments = [phrase("00:00", until="00:04"), phrase("00:58", until="01:03"), phrase("00:05")]
        self.assertEqual(self.annotate(items, segments), ["Alice", "Bob", "Alice"])
        self.assertEqual(self.annotate(items, segments, "speaker_label"), ["Alice", "Bob", "Alice"])

    def test_own_highlighted_tile_is_not_a_second_remote_speaker(self):
        names = self.annotate(
            [frame("00:00", "Bob"), frame("00:55", "Mike")],
            [phrase("00:00", until="00:04"),
             phrase("00:10", until="01:00", source="microphone"),  # long own turn
             phrase("01:05"), phrase("03:00")])
        self.assertEqual(names, ["Bob", "Bob", "Bob"])

    def test_self_introduction_names_only_its_phrase_on_shared_channel(self):
        names = self.annotate(
            [frame("00:00", "Alice"), frame("01:00", "Bob")],
            [phrase("00:00", until="00:04"), phrase("00:58", until="01:03"),
             phrase("01:05", text="My name is Carol")])
        self.assertEqual(names, ["Alice", "Bob", "Carol"])

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

    def test_floating_window_toolbar_caption_is_not_the_speaker(self):
        with tempfile.TemporaryDirectory() as directory:
            result = MeetingFrames._speaker_from_frame(self.blank_frame(directory), [
                {"text": "°. app.zoom.us", "y": 0.866, "x": 0.084},
                {"text": "Mike Shishkin", "x": 0.066, "y": 0.113, "width": 0.18},
                {"text": "Unmute", "x": 0.02, "y": 0.03, "width": 0.05},
            ])
        self.assertEqual(result[0], "Mike Shishkin")

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
