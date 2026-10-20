import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server
from ai_providers import AIService
from first_run import AIReadiness
from test_ai_providers import FakeAdapter


class AISettingsAPITests(unittest.TestCase):
    def test_list_options_save_choice_and_reject_unoffered(self):
        with tempfile.TemporaryDirectory() as directory:
            service = AIService(Path(directory) / "config.json", {}, adapters=[FakeAdapter()])
            with patch.object(server, "AI", service), patch.object(server, "AI_READINESS", AIReadiness(service)):
                httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
                threading.Thread(target=httpd.serve_forever, daemon=True).start()

                def call(method, path, payload=None, origin=None):
                    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                    headers = {"Content-Type": "application/json", **({"Origin": origin} if origin else {})}
                    connection.request(method, path, None if payload is None else json.dumps(payload), headers)
                    response = connection.getresponse()
                    raw = response.read()
                    result = response.status, json.loads(raw) if "json" in (response.getheader("Content-Type") or "") else raw
                    connection.close()
                    return result
                try:
                    status, body = call("GET", "/api/ai")
                    self.assertEqual(status, 200)
                    self.assertEqual(body["providers"], [{"provider": "fake", "label": "Fake"}])
                    self.assertEqual(body["purposes"]["live_analysis"]["state"], "needs_choice")
                    status, body = call("GET", "/api/ai/options?provider=fake")
                    self.assertEqual([m["id"] for m in body["options"]["models"]], ["m1", "m2"])
                    choice = {"provider": "fake", "model": "m1", "effort": "y", "speed": "quick"}
                    self.assertEqual(call("POST", "/api/ai/choice", {"purpose": "live_analysis", "choice": choice}, "https://example.test")[0], 403)
                    status, body = call("POST", "/api/ai/choice", {"purpose": "live_analysis", "choice": choice})
                    self.assertEqual((status, body["status"]["state"]), (200, "ready"))
                    status, body = call("POST", "/api/ai/choice", {"purpose": "live_analysis", "choice": {**choice, "model": "absent"}})
                    self.assertEqual(status, 400)
                    self.assertIn("absent", body["error"])
                    self.assertEqual(call("GET", "/api/ai")[1]["purposes"]["live_analysis"]["choice"], choice)
                finally:
                    httpd.shutdown()
                    httpd.server_close()


if __name__ == "__main__":
    unittest.main()
