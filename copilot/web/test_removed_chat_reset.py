import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server


class RemovedChatResetTests(unittest.TestCase):
    def test_retired_reset_request_cannot_erase_persisted_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "copilot.json"
            session = server.CodexSession(path)
            session.meeting_id = "synthetic-meeting"
            session.messages = [{"role": "user", "meeting_id": "synthetic-meeting", "text": "Keep this synthetic question"}]
            session._persist_locked()
            before = path.read_bytes()
            with patch.object(server, "COPILOT", session):
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                try:
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=3)
                    connection.request("POST", "/api/reset", "{}", {"Content-Type": "application/json"})
                    response = connection.getresponse()
                    status = response.status
                    response.read()
                    connection.close()
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    worker.join(timeout=3)
            self.assertEqual(status, 404)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(server.CodexSession(path).snapshot("synthetic-meeting")["messages"]), 1)
