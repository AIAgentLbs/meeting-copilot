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
                    self.assertEqual(body["choice"]["state"], "needs_choice")
                    status, body = call("GET", "/api/ai/options?provider=fake")
                    self.assertEqual([m["id"] for m in body["options"]["models"]], ["m1", "m2", "m3"])
                    choice = {"provider": "fake", "model": "m1", "effort": "y", "speed": "quick"}
                    self.assertEqual(call("POST", "/api/ai/choice", {"choice": choice}, "https://example.test")[0], 403)
                    status, body = call("POST", "/api/ai/choice", {"choice": choice})
                    self.assertEqual((status, body["status"]["state"]), (200, "ready"))
                    status, body = call("POST", "/api/ai/choice", {"choice": {**choice, "model": "absent"}})
                    self.assertEqual(status, 400)
                    self.assertIn("absent", body["error"])
                    body = call("GET", "/api/ai")[1]
                    self.assertEqual(body["choice"]["choice"], choice)
                    self.assertEqual({p["choice"]["model"] for p in body["purposes"].values()}, {"m1"})
                    call("POST", "/api/getting-started/check-ai", {})
                    self.assertNotEqual(call("GET", "/api/ai")[1]["check"]["purposes"]["live_analysis"]["state"], "unchecked")
                    call("POST", "/api/ai/choice", {"choice": {**choice, "speed": "standard"}})
                    # a changed choice is never shown with the old check result
                    self.assertEqual(call("GET", "/api/ai")[1]["check"]["purposes"]["live_analysis"]["state"], "unchecked")
                finally:
                    httpd.shutdown()
                    httpd.server_close()

    def test_panel_shows_the_check_snapshot_for_the_saved_choice(self):
        source = (Path(server.__file__).parent / "getting-started.js").read_text(encoding="utf-8")
        self.assertIn("checked = (aiState.check?.purposes || {})[purpose]", source)
        self.assertIn('await api("/api/ai/choice", {choice: draft}); await loadAI(true);', source)
        self.assertIn("if (aiState.check) current.ai = aiState.check;", source)
        self.assertNotIn("drafts[", source)  # one choice, no per-task rows


if __name__ == "__main__":
    unittest.main()
