"""The Chat tab holds only the owner's conversation; auto-analysis feeds Call overview only."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server

TRANSCRIPT = {"meeting_id": "m1", "meeting": "Test", "segments": [
    {"text": "Мы начнем пилот в понедельник", "speaker_id": "remote-1"},
]}


class OwnerChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.session = server.CodexSession(self.root / "session.json")
        self.journal = server.MeetingJournal(self.root / "journal.json")
        self.patches = [patch.object(server.GOOGLE_CONTEXT, "augment", return_value=""),
                        patch.object(server.LOCAL_CONTEXT, "augment", return_value="")]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        self.temp.cleanup()

    def ask(self, answer, **kwargs):
        with patch.object(self.session, "_run_ai", return_value=answer):
            return self.session.ask(kwargs.pop("question", "q"), "", "Test", "m1", {}, **kwargs)

    def test_analysis_reaches_call_overview_but_never_the_chat(self):
        risk = self.journal.add("RISK", "Срок неизвестен", "m1", "Test", "copilot")
        update = "SIGNAL_UPDATE: " + json.dumps({"id": risk["id"], "status": "resolved",
                                                "evidence": TRANSCRIPT["segments"][0]["text"]})
        answer = f"ASK — Кто отвечает за пилот?\nCOMMITMENT — Пилот в понедельник\n{update}"
        raw = self.ask(answer, kind="insight", show_user=False)
        # The same steps /api/analyze runs on the raw answer.
        self.assertEqual(self.journal.apply_analysis(TRANSCRIPT, raw), 1)
        self.journal.add_answer(server.strip_protocol(raw), "m1", "Test")
        board = {item["category"]: item for item in self.journal.snapshot("m1")}
        self.assertEqual(board["RISK"]["status"], "resolved")
        self.assertIn("Кто отвечает за пилот?", board["ASK"]["text"])
        self.assertNotIn("SIGNAL_UPDATE", json.dumps(self.journal.snapshot("m1"), ensure_ascii=False))
        self.assertEqual(self.session.snapshot("m1")["messages"], [])
        self.assertEqual(server.CodexSession(self.session.path).snapshot("m1")["messages"], [])

    def test_owner_questions_and_answers_show_without_protocol_lines(self):
        self.ask("Пилот стартует в понедельник.\nSIGNAL_UPDATE: {\"id\":\"x\",\"status\":\"resolved\"}",
                 question="Когда пилот?")
        messages = self.session.snapshot("m1")["messages"]
        self.assertEqual([(item["role"], item["text"]) for item in messages],
                         [("user", "Когда пилот?"), ("assistant", "Пилот стартует в понедельник.")])
        self.assertTrue(all(item.get("at") for item in messages), "new messages carry a time for ordering with notes")

    def test_stored_auto_analysis_is_hidden_on_read_and_kept_on_disk(self):
        stored = [
            {"role": "user", "text": "Что они сказали?", "kind": "answer", "meeting_id": "m1"},
            {"role": "assistant", "text": "Про пилот.\nPLAN_UPDATE: {\"id\":\"p\",\"status\":\"clarify\"}",
             "kind": "answer", "meeting_id": "m1"},
            {"role": "assistant", "text": "RISK — Нет бюджета\nSIGNAL_UPDATE: {\"id\":\"r\",\"status\":\"clarify\"}",
             "kind": "insight", "meeting_id": "m1"},
        ]
        path = self.root / "legacy.json"
        path.write_text(json.dumps({"version": 1, "meeting_id": "m1", "messages": stored}), encoding="utf-8")
        messages = server.CodexSession(path).snapshot("m1")["messages"]
        self.assertEqual([item["text"] for item in messages], ["Что они сказали?", "Про пилот."])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["messages"], stored, "stored data is not deleted")


if __name__ == "__main__":
    unittest.main()
