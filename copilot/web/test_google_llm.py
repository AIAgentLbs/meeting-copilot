import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from google_context import GoogleContext


class GoogleLLMTests(unittest.TestCase):
    def test_session_searches_google_before_answer_without_manual_query(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = GoogleContext(Path(directory) / "google.json", "/fake/gws")
            provider.configure({"calendar": True, "gmail": True, "drive": True})
            with patch.object(provider, "status", return_value={"auth": "connected", "account": "synthetic@example.com"}):
                provider.connect()
            session = server.CodexSession(Path(directory) / "session.json")
            calls = []
            def model(prompt, planning=False):
                calls.append((prompt, planning))
                if planning:
                    return '{"query":"Acme","sources":["gmail","calendar","drive"]}'
                if provider.connected():
                    self.assertIn("Source decision", prompt)
                else:
                    self.assertNotIn("Source decision", prompt)
                self.assertIn("/synthetic/repo", prompt)
                self.assertIn("Preserve exact Google source links", prompt)
                return "FACT — Source decision"
            with patch.object(provider, "status", return_value={"auth": "connected", "account": "synthetic@example.com"}), patch.object(server, "GOOGLE_CONTEXT", provider), patch.object(session, "_run_codex", side_effect=model), patch.object(provider, "_search_source", return_value={"state": "ok", "items": [provider._item("drive", "Decision", "https://docs.google.com/document/d/synthetic", "Source decision")], "limited": False}) as search:
                scope = {"kind": "all", "repositories": [{"name": "Example", "path": "/synthetic/repo"}]}
                self.assertIn("FACT", session.ask("What did Acme agree?", "Acme call", "Test", "one", scope))
                self.assertEqual(search.call_count, 3)
                self.assertTrue(calls[0][1])
                provider.disconnect()
                calls.clear()
                session.ask("Next question", "Next speech", "Test", "one", scope)
                self.assertEqual(len(calls), 1)
                self.assertFalse(calls[0][1])
