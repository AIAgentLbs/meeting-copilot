import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from archive import MeetingArchive
from question_quality import useful_question


class QuestionQualityTests(unittest.TestCase):
    def test_conversational_noise_is_not_a_register_question(self):
        for text in ("Ну или, ну ты закончил, да?", "Вы уже закончили?", "А меня слышно?",
                     "Вам меня слышно?", "Можно вопрос?", "Есть вопросы?", "Ты готов?",
                     "Да?", "Ок?", "Can you hear me?", "Are you done?", "Any questions?"):
            with self.subTest(text=text):
                self.assertFalse(useful_question(text))

    def test_short_and_task_specific_questions_survive(self):
        for text in ("Какой срок?", "Сроки?", "Бюджет?", "Кто отвечает?", "Сколько стоит?",
                     "Закончили проверку документов?", "Ты закончил подготовку отчёта, да?",
                     "Готовы подписать договор?", "Есть вопросы по интеграции?",
                     "Слышали о проекте?", "Как проверить, что микрофон работает?",
                     "When is the deadline?", "Are you done with the compliance review?",
                     "Can you hear the customer objections?"):
            with self.subTest(text=text):
                self.assertTrue(useful_question(text))

    def test_capture_requires_semantic_classification_and_real_quote(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = server.MeetingJournal(Path(temp) / "journal.json")
            for quote, expected in (("Ну или, ну ты закончил, да?", 0), ("Какой срок?", 1)):
                transcript = {"meeting_id": "fixture", "segments": [{"text": quote, "speaker_id": "remote"}]}
                data = {"direction": "incoming", "evidence": quote}
                self.assertEqual(journal.capture_questions(transcript, "QUESTION_CAPTURE: " + json.dumps(data)), 0)
                data["kind"] = "procedural"
                self.assertEqual(journal.capture_questions(transcript, "QUESTION_CAPTURE: " + json.dumps(data)), 0)
                data["kind"] = "substantive"
                self.assertEqual(journal.capture_questions(transcript, "QUESTION_CAPTURE: " + json.dumps(data)), expected)

    def test_legacy_noise_is_hidden_without_deleting_originals_or_manual_items(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "journal.json"
            entries = [{"id": "old", "meeting_id": "fixture", "source": "transcript",
                        "category": "OPEN_QUESTION", "text": "Ну или, ну ты закончил, да?"},
                       {"id": "owner", "meeting_id": "fixture", "source": "user",
                        "category": "OPEN_QUESTION", "text": "Ты готов?"}]
            path.write_text(json.dumps({"items": entries}), encoding="utf-8")
            journal = server.MeetingJournal(path)
            self.assertEqual([item["id"] for item in journal.snapshot("fixture")], ["owner"])
            self.assertEqual(json.loads(path.read_text())["items"], entries)
            self.assertIsNone(journal.add("ASK", "Меня слышно?", "fixture", "Test", "copilot"))
            self.assertIsNone(journal.add("ASK", "Можно вопрос?\nОснование: нужна передача слова.",
                                          "fixture", "Test", "copilot"))

    def test_chat_keeps_originals_but_register_excludes_connection_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = server.MeetingJournal(Path(temp) / "journal.json")
            chat = server.MeetingChat(Path(temp) / "chat.json")
            messages = [{"sender": "Anna", "text": text} for text in
                        ("Меня слышно?", "Ну ты закончил, да?", "Какой срок?")]
            with patch.object(server, "JOURNAL", journal):
                self.assertEqual(chat.add_many(messages, "fixture", "Test", "", "export"), 3)
            self.assertEqual(len(chat.snapshot("fixture")), 3)
            self.assertEqual([item["text"] for item in journal.snapshot("fixture")], ["Какой срок?"])

    def test_history_filters_legacy_noise_without_changing_transcript(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "config"
            config.mkdir()
            original = [{"category": "OPEN_QUESTION", "source": "transcript",
                         "meeting_id": "fixture", "text": "Ну ты закончил, да?"},
                        {"category": "INCOMING_QUESTION", "source": "transcript",
                         "meeting_id": "fixture", "text": "Какой срок?"}]
            path = config / "journal.json"
            path.write_text(json.dumps({"items": original}), encoding="utf-8")
            archive = MeetingArchive(root / "recordings", root / "archive", root / "reports", config)
            segments = [{"text": original[0]["text"], "timestamp": "2026-10-02T10:00:00Z"}]
            archive.sync_transcript({"meeting_id": "fixture", "segments": segments})
            detail = archive.detail("fixture")
            self.assertEqual([item["text"] for item in detail["journal"]], ["Какой срок?"])
            self.assertEqual(detail["transcript"][0]["text"], segments[0]["text"])
            self.assertEqual(json.loads(path.read_text())["items"], original)


if __name__ == "__main__":
    unittest.main()
