"""Executive report opening must be useful and source-grounded."""

import tempfile
import unittest
from pathlib import Path

from archive import MeetingArchive


class ReportBriefTests(unittest.TestCase):
    def test_people_summary_topics_and_actions_precede_toc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = MeetingArchive(root / "recordings", root / "archive", root / "reports", root / "config")
            detail = {
                "meeting_id": "sample", "title": "Prima product review",
                "started_at": "2026-09-25T10:00:00+02:00", "duration_seconds": 1800,
                "participants": [{"name": "Ana Silva", "identities": [
                    {"kind": "email", "value": "ana@example.com"}
                ], "public_facts": [{"text": "Founder of Prima", "url": "https://example.com/ana"}]}],
                "transcript": [
                    {"speaker": "Ana Silva", "text": "We should ship the pilot next week.",
                     "timestamp": "2026-09-25T10:01:00+02:00"},
                    {"speaker": "Спикер 1", "text": "Okay", "timestamp": "2026-09-25T10:02:00+02:00"},
                ],
                "meeting_chat": [{"sender": "Ana Silva", "text": "Telegram: @ana_silva",
                                  "displayed_at": "10:03"}],
                "journal": [
                    {"category": "DECISION", "text": "Запустить пилот.", "created_at": "2026-09-25T10:04:00+02:00"},
                    {"category": "COMMITMENT", "text": "Анна пришлёт план до 30.09.",
                     "created_at": "2026-09-25T10:05:00+02:00"},
                ],
            }
            page = archive._report_html(detail, [])
        self.assertLess(page.index('id="overview"'), page.index('class="toc"'))
        self.assertLess(page.index('id="followups"'), page.index('class="toc"'))
        self.assertIn("Основной спикер по объёму распознанной речи: <strong>Ana Silva</strong>", page)
        self.assertIn("ana@example.com", page)
        self.assertIn("@ana_silva", page)
        self.assertIn("Публично: Founder of Prima", page)
        self.assertIn("https://example.com/ana", page)
        self.assertIn("Анна пришлёт план до 30.09.", page)
        self.assertIn("Запустить пилот.", page)

    def test_unknown_names_are_not_invented(self):
        people, main = MeetingArchive._front_participants({
            "participants": [], "meeting_chat": [],
            "transcript": [{"speaker": "Спикер 1", "text": "Привет"}],
        })
        self.assertEqual(people, [])
        self.assertEqual(main, "Не определён по записи")

    def test_named_speaker_is_not_declared_main_when_unknown_voice_dominates(self):
        people, main = MeetingArchive._front_participants({
            "participants": [], "meeting_chat": [],
            "transcript": [
                {"speaker": "Ana Silva", "text": "Hello"},
                {"speaker": "Спикер 1", "text": "This is a much longer speech from another voice."},
            ],
        })
        self.assertEqual(people[0]["name"], "Ana Silva")
        self.assertEqual(main, "Не определён по записи")

    def test_meet_account_labels_are_listed_without_claiming_voice_identity(self):
        people, main = MeetingArchive._front_participants({
            "participants": [], "meeting_chat": [], "transcript": [],
            "frames": [
                {"participant_labels": ["Dmitry Brich", "performance sports", "mf"],
                 "speaker": "mf", "speaker_confidence": "meet-active-tile"},
                {"participant_labels": ["Dmitry Brich", "performance sports", "mf"],
                 "speaker": "", "speaker_confidence": ""},
            ],
        })
        self.assertEqual({item["name"] for item in people}, {"Dmitry Brich", "performance sports", "mf"})
        self.assertEqual(main, "Не определён по записи")

    def test_spoken_address_corroborates_account_but_not_speaker(self):
        people, main = MeetingArchive._front_participants({
            "participants": [], "meeting_chat": [],
            "frames": [{"participant_labels": ["Emerson Moraes", "Michael S"]}] * 2,
            "transcript": [{"speaker": "Спикер 1", "text": "Emerson, давай обсудим."}],
        })
        emerson = next(item for item in people if item["name"] == "Emerson Moraes")
        self.assertIn("имя звучит в разговоре", emerson["seen"])
        self.assertEqual(main, "Не определён по записи")

    def test_followup_requires_actual_action(self):
        self.assertEqual(
            MeetingArchive._followup_sentence("Майк уточнил: аутрич по Бразилии будет на португальском."),
            "",
        )
        self.assertEqual(
            MeetingArchive._followup_sentence("Участник ещё не договорился с Sobral по трансляции."),
            "",
        )
        self.assertEqual(
            MeetingArchive._followup_sentence(
                "Статус неясен. Запрошен отдельный звонок с Дмитрием, дата не названа.\\nИсточник: встреча"
            ),
            "Запрошен отдельный звонок с Дмитрием, дата не названа.",
        )


if __name__ == "__main__":
    unittest.main()
