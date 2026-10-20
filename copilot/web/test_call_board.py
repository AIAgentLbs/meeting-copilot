import json
import tempfile
import unittest
from pathlib import Path

from server import MeetingJournal, parse_journal_blocks


class CallBoardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "journal.json"
        self.journal = MeetingJournal(self.path)
        self.transcript = {"meeting_id": "one", "meeting": "Test", "segments": [
            {"text": "Майк, когда вы сможете начать пилот?", "speaker_id": "remote-1"},
            {"text": "Мы сможем начать пилот в следующий понедельник", "speaker_id": "self"},
        ]}

    def tearDown(self):
        self.temp.cleanup()

    def test_status_is_durable_meeting_scoped_and_manual_wins(self):
        item = self.journal.add("ASK", "Когда стартуем?", "one", "Test", "copilot")
        self.journal.set_status("one", item["id"], "clarify")
        reloaded = MeetingJournal(self.path)
        self.assertEqual(reloaded.snapshot("one")[0]["status"], "clarify")
        with self.assertRaises(ValueError):
            reloaded.set_status("other", item["id"], "resolved")
        update = 'SIGNAL_UPDATE: ' + json.dumps({"id": item["id"], "status": "resolved",
                                               "evidence": self.transcript["segments"][1]["text"]})
        reloaded.apply_analysis(self.transcript, update)
        self.assertEqual(reloaded.snapshot("one")[0]["status"], "clarify")

    def test_automatic_resolution_requires_real_current_speech(self):
        item = self.journal.add("RISK", "Срок неизвестен", "one", "Test", "copilot")
        for evidence, expected in [("Подготовка обещает завтра", 0),
                                   (self.transcript["segments"][1]["text"], 1)]:
            answer = 'SIGNAL_UPDATE: ' + json.dumps({"id": item["id"], "status": "resolved", "evidence": evidence})
            self.assertEqual(self.journal.apply_analysis(self.transcript, answer), expected)
        self.assertEqual(self.journal.snapshot("one")[0]["status"], "resolved")

    def test_question_direction_and_deduplication_require_speech(self):
        quote = self.transcript["segments"][0]["text"]
        answer = 'QUESTION_CAPTURE: ' + json.dumps({"kind": "substantive", "direction": "incoming", "evidence": quote})
        self.assertEqual(self.journal.capture_questions(self.transcript, answer), 1)
        self.assertEqual(self.journal.capture_questions(self.transcript, answer), 0)
        self.assertEqual(self.journal.snapshot("one")[0]["category"], "INCOMING_QUESTION")
        self.assertEqual(self.journal.capture_questions(self.transcript,
                         'QUESTION_CAPTURE: {"direction":"incoming","evidence":"Какой ваш адрес электронной почты?"}'), 0)
        self.journal.add_answer("INCOMING_QUESTION — Придуманный вопрос?", "one", "Test")
        self.assertEqual(len(self.journal.snapshot("one")), 1)

    def test_owner_question_is_not_incoming_and_user_request_is_not_actionable(self):
        self.transcript["segments"].append({"text": "Когда вы сможете передать данные?", "speaker_id": "self"})
        answer = 'QUESTION_CAPTURE: ' + json.dumps({"kind": "substantive", "direction": "incoming", "evidence": self.transcript["segments"][-1]["text"]})
        self.journal.capture_questions(self.transcript, answer)
        self.assertEqual(self.journal.snapshot("one")[0]["category"], "OPEN_QUESTION")
        item = self.journal.add("QUESTION", "Что они сказали?", "one", "Test", "user")
        with self.assertRaises(ValueError):
            self.journal.set_status("one", item["id"], "resolved")
        self.assertEqual(parse_journal_blocks("OBJECTION — Нет ресурсов\n\nASK — Какой срок?"),
                         [("OBJECTION", "Нет ресурсов"), ("ASK", "Какой срок?")])
