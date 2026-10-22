"""MEETONTRACK-94: a call followed right away by another one.

Shaped like the 2026-10-22 case: a 60-minute Chrome call with 44 live lines and
a system-audio warning 70 seconds before it ended; the next call starts two
minutes later; the recorder writes the 406-line final transcript while the next
call is still recording. All text is synthetic.
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from archive import MeetingArchive
from delivery_health import DeliveryHealth


def iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class FinalTranscriptAfterNextCallTests(unittest.TestCase):
    sent_automatically = True

    def setUp(self, days_ago: float = 0):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / "config"
        self.config.mkdir()
        (self.config / "delivery.json").write_text(json.dumps({"email_enabled": True, "email_to": "synthetic@example.test"}))
        self.archive = MeetingArchive(self.root / "recordings", self.root / "archive", self.root / "reports", self.config)
        self.start = (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=3)).replace(microsecond=0)
        self.end = self.start + timedelta(seconds=3650)
        self.dropout = self.start + timedelta(seconds=3580)
        self.first = self.recording("2026.10.22-1601 Google Chrome Helper (Ap", self.start, self.end)
        self.next_start = self.start + timedelta(seconds=3774)
        self.second = self.recording("2026.10.22-1703 Google Chrome Helper (Ap", self.next_start, None)
        (self.second / ".recording.json").write_text("{}")  # The next call is recording.
        live = [{"source": "system", "voice_id": "remote-1", "provisional": False,
                 "timestamp": iso(self.start + timedelta(seconds=39 + index * 80)),
                 "end_timestamp": iso(self.start + timedelta(seconds=45 + index * 80)),
                 "text": f"Live line {index}"} for index in range(44)]
        self.live = {"meeting_id": "FIRST-CALL", "meeting": "Google Chrome Helper (Ap", "status": "finished",
                     "started_at": iso(self.start), "updated_at": iso(self.end), "latest_at": live[-1]["timestamp"],
                     "segments": live, "recording_dir": str(self.first),
                     "capture_warnings": [{"reason": "system-audio-lost", "started_at": iso(self.dropout)}]}
        self.archive.sync_transcript(self.live)
        self.archive.sync_transcript({"meeting_id": "NEXT-CALL", "meeting": "Google Chrome Helper (Ap",
                                      "status": "recording", "started_at": iso(self.next_start),
                                      "updated_at": iso(self.next_start), "recording_dir": str(self.second),
                                      "segments": [{"source": "system", "timestamp": iso(self.next_start + timedelta(seconds=5)),
                                                    "text": "Next call line"}]})
        # The final transcript arrives half an hour after the call, while the next one records.
        lines = [{"speaker": "me" if index % 3 == 0 else "them", "start_ms": index * 8780,
                  "end_ms": index * 8780 + 4000, "text": f"Final line {index}"} for index in range(405)]
        lines.append({"speaker": "them", "start_ms": 3564160, "end_ms": 3565360, "text": "Final goodbye"})
        self.write_final(lines)
        self.sent: list[str] = []

    def recording(self, name: str, started: datetime, ended: datetime | None) -> Path:
        directory = self.root / "recordings" / name
        directory.mkdir(parents=True)
        meta = {"app": "Google Chrome Helper (Aperitif)", "audio_channels": {"mic": 0, "system": 1},
                "files": {"mic": "audio.m4a", "system": "audio.m4a"}, "started": iso(started),
                "trigger": "mic-activity", "transcription_input": "per-track",
                "system_recoveries": [{"at": iso(started + timedelta(seconds=50)), "status": "restarted"}]}
        if ended:
            meta.update(ended=iso(ended), duration_seconds=int((ended - started).total_seconds()) - 1,
                        stop_reason="call-ended")
        (directory / "meta.json").write_text(json.dumps(meta))
        (directory / "audio.m4a").write_bytes(b"synthetic")
        return directory

    def write_final(self, lines: list[dict]) -> None:
        (self.first / "transcript.json").write_text(json.dumps({
            "created_at": iso(self.end + timedelta(minutes=31)), "engine": "fluidaudio", "language": "auto",
            "model": "synthetic-model", "segments": lines}))

    def next_call_ends(self) -> None:
        (self.second / ".recording.json").unlink(missing_ok=True)

    def stored(self, meeting_id: str = "FIRST-CALL") -> dict:
        return json.loads((self.root / "archive" / meeting_id / "meeting.json").read_text())

    def finalize(self) -> None:
        def deliver(detail, meta, **kwargs):
            self.sent.append(detail["meeting_id"])
            return {"mail_status": "sent"}
        with patch.object(self.archive, "_print_pdf", side_effect=lambda html, pdf: pdf.write_bytes(b"%PDF synthetic")), \
             patch.object(self.archive, "deliver", side_effect=deliver):
            self.archive.finalize_history()

    def test_final_transcript_replaces_live_and_report_follows_when_next_call_ends(self):
        self.finalize()
        stored = self.stored()
        self.assertEqual(len(stored["segments"]), 406)
        self.assertEqual(stored["segments"][-1]["text"], "Final goodbye")
        self.assertFalse((self.root / "reports/FIRST-CALL/report.json").exists(),
                         "No report while the next call is still recording")
        self.next_call_ends()
        self.finalize()
        report = json.loads((self.root / "reports/FIRST-CALL/report.json").read_text())
        self.assertEqual(self.sent, ["FIRST-CALL"])
        self.assertEqual(report["mail_status"], "sent")
        self.assertNotIn("delivery_on_request", report)
        self.assertEqual(len(self.stored("NEXT-CALL")["segments"]), 1, "The next call is left alone")

    def test_dropout_in_the_last_minute_is_explained_not_flagged(self):
        self.next_call_ends()
        self.finalize()
        detail = self.archive.detail("FIRST-CALL")
        self.assertEqual(detail["library_status"], "report_ready")
        self.assertEqual(detail["audio_gap"], {"started_at": self.dropout.isoformat(), "count": 1,
                                               "ended_at": "", "seconds": 70})
        summary = next(item for item in self.archive.list_meetings() if item["meeting_id"] == "FIRST-CALL")
        self.assertEqual(summary["audio_gap"], detail["audio_gap"])
        self.assertNotEqual(summary["library_status"], "needs_attention")

    def test_audio_gap_only_counts_the_part_inside_this_meeting(self):
        detail = {"started_at": iso(self.start), "ended_at": iso(self.end), "capture_warnings": [
            {"started_at": iso(self.start - timedelta(seconds=60)), "ended_at": iso(self.start + timedelta(seconds=30))},
            {"started_at": iso(self.end + timedelta(seconds=60)), "ended_at": iso(self.end + timedelta(seconds=90))}]}
        self.assertEqual(MeetingArchive._audio_gap(detail), {
            "started_at": self.start.isoformat(), "count": 1,
            "ended_at": (self.start + timedelta(seconds=30)).isoformat(), "seconds": 30})
        detail["capture_warnings"] = detail["capture_warnings"][1:]  # Only after this meeting ended.
        self.assertIsNone(MeetingArchive._audio_gap(detail))

    def test_final_speech_inside_the_dropout_clears_the_warning(self):
        lines = json.loads((self.first / "transcript.json").read_text())["segments"]
        lines.append({"speaker": "them", "start_ms": 3610000, "end_ms": 3620000, "text": "Still talking"})
        self.write_final(lines)
        self.finalize()
        self.assertEqual(self.stored()["capture_warnings"], [])
        self.assertIsNone(self.archive.detail("FIRST-CALL")["audio_gap"])

    def test_one_short_utterance_only_narrows_a_long_dropout(self):
        self.live["capture_warnings"] = [{"reason": "system-audio-lost", "started_at": iso(self.start + timedelta(seconds=2400))}]
        self.archive.sync_transcript(self.live)
        lines = json.loads((self.first / "transcript.json").read_text())["segments"]
        self.write_final([line for line in lines if not 2400000 < line["start_ms"]]
                         + [{"speaker": "them", "start_ms": 2500000, "end_ms": 2501000, "text": "One word"}])
        self.finalize()
        self.assertEqual(self.archive.detail("FIRST-CALL")["audio_gap"]["started_at"],
                         (self.start + timedelta(seconds=2501)).isoformat())

    def test_later_live_export_never_replaces_final_and_repeat_passes_change_nothing(self):
        self.next_call_ends()
        self.finalize()
        self.archive.sync_transcript(self.live)  # A restart re-reads an old live file.
        stored = self.stored()
        self.assertEqual(len(stored["segments"]), 406)
        path = self.root / "archive/FIRST-CALL/meeting.json"
        before = path.read_bytes()
        self.finalize()
        self.finalize()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.sent, ["FIRST-CALL"], "One report, sent once")


    def test_final_read_by_the_live_file_keeps_its_names_and_still_gets_its_report(self):
        from canonical_transcript import canonical_segments
        named = canonical_segments(self.live)
        for segment in named:
            if segment["source"] == "system":
                segment.update(speaker="Visual Name", speaker_confidence="visual-voice-map")
        self.archive.sync_transcript({**self.live, "segments": named})  # The next call then started.
        self.next_call_ends()
        self.finalize()
        stored = self.stored()
        self.assertTrue(stored["final_transcript"])
        self.assertEqual(stored["segments"][-1]["speaker"], "Visual Name")
        self.assertTrue((self.root / "reports/FIRST-CALL/report.json").exists())
        self.assertEqual(self.sent, ["FIRST-CALL"] if self.sent_automatically else [])

    def test_a_merged_report_waits_until_every_chunk_has_its_final_transcript(self):
        # A reconnect 30 s later is the same call: its chunk sorts first by folder name.
        early = self.start - timedelta(minutes=30)
        chunk = self.recording("2026.10.22-1530 Google Chrome Helper (Ap", early, self.start - timedelta(seconds=30))
        (chunk / "transcript.json").write_text(json.dumps({"engine": "fluidaudio", "segments": [
            {"speaker": "them", "start_ms": 1000, "end_ms": 3000, "text": "Earlier chunk final"}]}))
        self.archive.sync_transcript({**self.live, "meeting": "Synthetic sync"})  # Same title: one call.
        self.archive.sync_transcript({**self.live, "meeting": "Synthetic sync", "meeting_id": "EARLY-CHUNK", "started_at": iso(early),
                                      "updated_at": iso(self.start - timedelta(seconds=30)), "capture_warnings": [],
                                      "recording_dir": str(chunk), "segments": [
                                          {"source": "system", "timestamp": iso(early + timedelta(seconds=1)), "text": "Live chunk"}]})
        self.next_call_ends()
        self.finalize()
        self.assertEqual(self.sent, ["FIRST-CALL"] if self.sent_automatically else [])
        texts = [item["text"] for item in self.archive.report_detail("FIRST-CALL")["transcript"]]
        self.assertIn("Earlier chunk final", texts)
        self.assertNotIn("Live chunk", texts)


    def test_a_failing_report_is_tried_again_every_30_minutes_not_every_minute(self):
        self.next_call_ends()
        clock = [5000.0]
        with patch("archive.time.monotonic", lambda: clock[0]), \
             patch.object(self.archive, "_print_pdf", side_effect=RuntimeError("Chrome не создал PDF")) as printer:
            self.archive.finalize_history()
            self.archive.finalize_history()
            self.assertEqual(printer.call_count, 1)
            clock[0] += 1801
            self.archive.finalize_history()
            self.assertEqual(printer.call_count, 2)
        self.finalize()  # Printing works again: the report is created and sent.
        self.assertEqual(self.sent, ["FIRST-CALL"] if self.sent_automatically else [])


class OldMeetingRepairTests(FinalTranscriptAfterNextCallTests):
    sent_automatically = False

    def setUp(self):
        super().setUp(days_ago=10)
        self.next_call_ends()

    def test_old_meeting_gets_a_report_that_is_sent_only_on_request(self):
        self.finalize()
        path = self.root / "reports/FIRST-CALL/report.json"
        report = json.loads(path.read_text())
        self.assertTrue(report["delivery_on_request"])
        self.assertEqual(self.sent, [])
        # A report made while the call was still recording no longer waits for its end.
        path.write_text(json.dumps({**report, "mail_status": "waiting_for_end", "generated_while_recording": True}))
        (self.root / "archive/FIRST-CALL/meeting.json").touch()
        self.finalize()
        self.assertEqual(json.loads(path.read_text())["mail_status"], "pending")
        settings = json.loads((self.config / "delivery.json").read_text())
        with patch.object(self.archive, "deliver") as deliver:
            self.archive.retry_pending_deliveries()
            # A refresh that sends nothing (speaker rename) keeps it on request.
            with patch.object(self.archive, "_print_pdf", side_effect=lambda html, pdf: pdf.write_bytes(b"%PDF synthetic")):
                self.archive.generate_report("FIRST-CALL", deliver=False)
            self.archive.retry_pending_deliveries()
        deliver.assert_not_called()
        self.assertTrue(json.loads(path.read_text())["delivery_on_request"])
        health = DeliveryHealth(self.root / "reports", self.config / "health.json").refresh(
            settings, now=datetime.now(timezone.utc) + timedelta(hours=1))
        self.assertEqual(health["issue_count"], 0)
        self.assertEqual(health["notifications"], [])
        # A send the person asked for that failed is shown, not hidden as "on request".
        failed = json.loads(path.read_text())
        path.write_text(json.dumps({**failed, "mail_status": "failed"}))
        health = DeliveryHealth(self.root / "reports", self.config / "health.json").refresh(
            settings, now=datetime.now(timezone.utc) + timedelta(hours=1))
        self.assertEqual(health["issue_count"], 1)

    # The inherited cases also hold for an old meeting, without any sending.
    def test_final_transcript_replaces_live_and_report_follows_when_next_call_ends(self):
        self.finalize()
        self.assertEqual(len(self.stored()["segments"]), 406)
        self.assertEqual(self.sent, [])

    def test_later_live_export_never_replaces_final_and_repeat_passes_change_nothing(self):
        self.finalize()
        self.archive.sync_transcript(self.live)
        self.assertEqual(len(self.stored()["segments"]), 406)


if __name__ == "__main__":
    unittest.main()
