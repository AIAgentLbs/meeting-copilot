import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from chat_import import parse_chat_export


class ChatImportTests(unittest.TestCase):
    def test_zoom_and_multiline(self):
        rows = parse_chat_export('17:42:01 From Анна to Everyone:\tКак связать CRM?\nИ второй вопрос\n17:43:00 Иван: Спасибо')
        self.assertEqual(rows[0]['sender'], 'Анна')
        self.assertEqual(rows[0]['displayed_at'], '17:42:01')
        self.assertIn('И второй вопрос', rows[0]['text'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(parse_chat_export('plain unstructured text'), [])

    def test_persistence_questions_and_answer_proof(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = server.MeetingJournal(Path(temp) / 'journal.json')
            chat = server.MeetingChat(Path(temp) / 'chat.json')
            messages = parse_chat_export(json.dumps([{'sender': 'Анна', 'text': 'Как связать данные с CRM?', 'time': '17:42'}]))
            with patch.object(server, 'JOURNAL', journal):
                self.assertEqual(chat.add_many(messages, 'fixture', 'Test', '', 'export'), 1)
                self.assertEqual(chat.add_many(messages, 'fixture', 'Test', '', 'export'), 0)
                question = journal.snapshot('fixture')[0]
                self.assertEqual(question['speaker'], 'Анна')
                self.assertEqual(question['source'], 'meeting_chat')
                reply = {'sender': 'Спикер', 'text': 'Передавайте Client ID в поле клиента CRM.', 'displayed_at': '17:43'}
                chat.add_many([reply], 'fixture', 'Test', '', 'export')
                update = 'SIGNAL_UPDATE: ' + json.dumps({'id': question['id'], 'status': 'resolved', 'evidence': reply['text']})
                self.assertEqual(journal.apply_analysis({'meeting_id': 'fixture', 'segments': []}, update, []), 0)
                self.assertEqual(journal.apply_analysis({'meeting_id': 'fixture', 'segments': []}, update, chat.snapshot('fixture')), 1)
                self.assertIn('17:43', journal.snapshot('fixture')[0]['evidence'])
                self.assertEqual(len(server.MeetingChat(chat.path).snapshot('fixture')), 2)


if __name__ == '__main__':
    unittest.main()
