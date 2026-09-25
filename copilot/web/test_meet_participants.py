"""Meet participant labels must come from video tiles, not captions or page text."""

import tempfile
import unittest
from pathlib import Path

from meet_participants import meet_active_speaker, meet_participant_labels


class MeetParticipantTests(unittest.TestCase):
    def test_tile_rows_exclude_single_caption_and_browser_text(self):
        observations = [
            {"text": "Chrome", "x": 0.2, "y": 0.95, "width": 0.1},
            {"text": "mf", "x": 0.31, "y": 0.56, "width": 0.02},
            {"text": "Dmitry Brich", "x": 0.42, "y": 0.56, "width": 0.07},
            {"text": "Douglas Jorge", "x": 0.13, "y": 0.28, "width": 0.07},
            {"text": "performance sports", "x": 0.23, "y": 0.28, "width": 0.09},
            {"text": "Emerson Moraes", "x": 0.51, "y": 0.28, "width": 0.08},
            {"text": "Michael S", "x": 0.61, "y": 0.28, "width": 0.06},
            {"text": "Emerson Moraes", "x": 0.35, "y": 0.22, "width": 0.08},
        ]
        self.assertEqual(meet_participant_labels(observations), [
            "Douglas Jorge", "performance sports", "Emerson Moraes", "Michael S",
            "mf", "Dmitry Brich",
        ])

    def test_blue_active_tile_maps_to_its_account(self):
        from PIL import Image, ImageDraw

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "meet.png"
            image = Image.new("RGB", (1000, 600), (22, 22, 22))
            ImageDraw.Draw(image).rectangle((500, 100, 900, 500), outline=(168, 191, 227), width=4)
            image.save(path)
            observations = [
                {"text": "Dmitry Brich", "x": 0.20, "y": 0.17, "width": 0.10},
                {"text": "Michael S", "x": 0.53, "y": 0.17, "width": 0.09},
            ]
            self.assertEqual(meet_active_speaker(path, observations), "Michael S")

    def test_language_picker_is_not_a_participant_row(self):
        observations = [
            {"text": name, "x": 0.2, "y": 0.2 + index * 0.05, "width": 0.1}
            for index, name in enumerate(("Dutch", "English (UK)", "Filipino", "French", "German"))
        ]
        observations.extend([
            {"text": "talian", "x": 0.3, "y": 0.4, "width": 0.1},
            {"text": "as Jorge", "x": 0.5, "y": 0.4, "width": 0.1},
        ])
        self.assertEqual(meet_participant_labels(observations), [])


if __name__ == "__main__":
    unittest.main()
