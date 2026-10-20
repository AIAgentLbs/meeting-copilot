import unittest
import tempfile
from pathlib import Path

from teams_participants import teams_one_to_one_name, teams_participant_labels
from server import Handler, MeetingFrames


class TeamsParticipantTests(unittest.TestCase):
    def test_capture_warning_reaches_copilot_even_when_transcript_is_truncated(self):
        context = Handler._transcript_text({
            "capture_warnings": [{"reason": "system-audio-lost"}],
            "segments": [{"speaker": "Голос не подтверждён", "text": "a" * 300}],
        }, max_chars=20)
        self.assertIn("нельзя приписывать Майку", context)
        self.assertTrue(context.endswith("a" * 20))

    def test_main_tile_name_and_icon(self):
        observations = [
            {"text": "teams.live.com/light-meetings/launch", "y": .92},
            {"text": "Maxim Vyatkin S", "x": .028, "y": .066, "width": .044},
            {"text": "MC", "x": .88, "y": .07, "width": .03},
            {"text": "Some Slide", "x": .3, "y": .5, "width": .1},
        ]
        self.assertEqual(teams_participant_labels(observations), ["Maxim Vyatkin"])

    def test_unrelated_browser_content_and_mention_are_not_a_roster(self):
        self.assertEqual(teams_participant_labels([
            {"text": "Maxim Vyatkin", "x": .028, "y": .066, "width": .044},
            {"text": "mail.google.com", "y": .92},
        ]), [])

    def test_one_to_one_requires_repeated_consistent_evidence(self):
        frame = {"participant_platform": "teams", "participant_labels": ["Maxim Vyatkin"]}
        self.assertEqual(teams_one_to_one_name([frame]), "")
        self.assertEqual(teams_one_to_one_name([frame, frame]), "Maxim Vyatkin")
        other = {"participant_platform": "teams", "participant_labels": ["Other Person"]}
        self.assertEqual(teams_one_to_one_name([frame, frame, other]), "")
        typo = {"participant_platform": "teams", "participant_labels": ["Maxim Vyakin"]}
        self.assertEqual(teams_one_to_one_name([frame, frame, typo]), "Maxim Vyatkin")

    def test_annotation_names_remote_not_microphone_and_marks_capture_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            frames = MeetingFrames(Path(directory) / "frames.json")
            frames.items = [{
                "meeting_id": "test", "participant_platform": "teams",
                "participant_labels": ["Maxim Vyatkin"],
            }] * 2
            annotated = frames.annotate({
                "meeting_id": "test",
                "capture_warnings": [{"started_at": "2026-09-27T11:20:40Z", "reason": "system-audio-lost"}],
                "segments": [
                    {"source": "system", "voice_id": "remote-1", "timestamp": "2026-09-27T11:09:00Z", "text": "hello"},
                    {"source": "microphone", "timestamp": "2026-09-27T11:10:00Z", "text": "hi"},
                    {"source": "microphone", "timestamp": "2026-09-27T11:30:00Z", "text": "uncertain"},
                ],
            })
            remote, mic, lost = annotated["segments"]
            self.assertEqual(remote["speaker"], "Maxim Vyatkin")
            self.assertNotIn("speaker", mic)
            self.assertEqual(lost["speaker_identity"], "unverified")
            self.assertEqual(lost["source"], "microphone")

    def test_multiple_acoustic_voices_are_not_renamed_as_one_person(self):
        with tempfile.TemporaryDirectory() as directory:
            frames = MeetingFrames(Path(directory) / "frames.json")
            frames.items = [{"meeting_id": "test", "participant_platform": "teams", "participant_labels": ["Maxim Vyatkin"]}] * 2
            annotated = frames.annotate({"meeting_id": "test", "segments": [
                {"source": "system", "voice_id": "remote-1", "timestamp": "2026-09-27T11:09:00Z", "text": "a"},
                {"source": "system", "voice_id": "remote-2", "timestamp": "2026-09-27T11:10:00Z", "text": "b"},
            ]})
            self.assertTrue(all(not segment.get("speaker") for segment in annotated["segments"]))
