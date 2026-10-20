"""Provider layer: discovery from fake CLIs/servers, shared config.json store, call building.

Every model id, effort and tier below is a fixture invented for the test; production
code must learn them from discovery.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import ai_providers
from ai_providers import AIService, AISettings, ClaudeAdapter, CodexAdapter, AntigravityAdapter, OllamaAdapter

PY = sys.executable

FAKE_CODEX = r'''
import json, sys
if sys.argv[1:] == ["--version"]:
    print("codex-cli 9.9.9"); sys.exit(0)
pages = {None: ([{"id": "fixture-a", "displayName": "Fixture A", "hidden": False,
                  "supportedReasoningEfforts": [{"reasoningEffort": "e1"}, {"reasoningEffort": "e2"}],
                  "defaultReasoningEffort": "e1", "serviceTiers": [{"id": "tier-x", "name": "Quick"}]},
                 {"id": "fixture-hidden", "hidden": True, "supportedReasoningEfforts": []}], "p2"),
         "p2": ([{"id": "fixture-b", "displayName": "Fixture B", "supportedReasoningEfforts": [],
                  "serviceTiers": []}], None)}
for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if mid is None: continue
    if method == "initialize": result = {"userAgent": "fake"}
    elif method == "model/list":
        data, nxt = pages[(msg.get("params") or {}).get("cursor")]
        result = {"data": data, "nextCursor": nxt}
    elif method == "account/read": result = {"account": ACCOUNT, "requiresOpenaiAuth": True}
    elif method == "config/read": result = {"config": {"model": "fixture-b", "model_reasoning_effort": None, "service_tier": None}}
    else: result = {}
    print(json.dumps({"method": "noise/notification", "params": {}}), flush=True)
    print(json.dumps({"id": mid, "result": result}), flush=True)
'''

FAKE_CLAUDE = r'''
import json, sys
args = sys.argv[1:]
if args == ["--version"]: print("9.9.9 (Claude Code)"); sys.exit(0)
if args[:2] == ["auth", "status"]:
    print(json.dumps({"loggedIn": True, "subscriptionType": "fixture-plan"})); sys.exit(0)
assert "--setting-sources" in args, args
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("type") == "control_request":
        print(json.dumps({"type": "system", "subtype": "hook_started"}), flush=True)
        print(json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": msg["request_id"], "response": {
            "models": [{"value": "alias-one", "displayName": "Alias One", "supportedEffortLevels": ["lo", "hi"], "supportsFastMode": True},
                       {"value": "plain", "displayName": "Plain"}],
            "account": {"subscriptionType": "Fixture Plan"},
            "fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"}}}), flush=True)
'''

FAKE_AGY = r'''
import sys
if sys.argv[1:] == ["--version"]: print("9.9.9"); sys.exit(0)
if sys.argv[1:] == ["models"]:
    print("Fetching available models...")
    print("fam-one-lo\tFam One (Lo)"); print("fam-one-hi\tFam One (Hi)"); print("solo\tSolo Model")
'''


def fake_cli(directory, name, source, **values):
    path = Path(directory) / name
    for key, value in values.items():
        source = source.replace(key, value)
    path.write_text(f"#!{PY}\n" + source)
    path.chmod(0o755)
    return path


class CodexDiscoveryTests(unittest.TestCase):
    def test_pages_models_skips_hidden_and_reads_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "codex", FAKE_CODEX, ACCOUNT='{"type": "chatgpt", "planType": "fixture-plan"}')
            found = CodexAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "available", found)
        self.assertEqual(found["plan"], "fixture-plan")
        self.assertEqual([m["id"] for m in found["models"]], ["fixture-a", "fixture-b"])
        first = found["models"][0]
        self.assertEqual(first["efforts"], ["e1", "e2"])
        self.assertEqual(first["speeds"], [{"id": "tier-x", "label": "Quick"}])
        self.assertEqual(found["current"]["model"], "fixture-b")

    def test_api_key_account_gets_no_fast_tier_with_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "codex", FAKE_CODEX, ACCOUNT='{"type": "apiKey"}')
            first = CodexAdapter(lambda: binary).discover()["models"][0]
        self.assertEqual(first["speeds"], [])
        self.assertIn("sign", first["speed_reason"].lower())

    def test_signed_out_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "codex", FAKE_CODEX, ACCOUNT="None")
            found = CodexAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "unavailable")
        self.assertIn("sign", found["reason"].lower())

    def test_missing_binary_and_hang_degrade_with_reason(self):
        self.assertEqual(CodexAdapter(lambda: None).discover()["state"], "unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            hang = fake_cli(tmp, "codex", "import time\ntime.sleep(30)\n")
            with patch.object(ai_providers, "DISCOVERY_TIMEOUT", 1):
                found = CodexAdapter(lambda: hang).discover()
        self.assertEqual(found["state"], "unavailable")
        self.assertIn("respond", found["reason"])

    def test_call_uses_choice_and_keeps_safety_flags(self):
        choice = {"provider": "codex", "model": "fixture-a", "effort": "e2", "speed": "tier-x"}
        event = '{"type":"thread.started","thread_id":"t1"}\n{"type":"item.completed","item":{"type":"agent_message","text":"OK"}}'
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, event, "")) as run:
            reply = CodexAdapter(lambda: "/fake/codex").call(choice, "prompt", files=False, env={}, timeout=5, keep_session=True)
        args = run.call_args.args[0]
        self.assertEqual((reply.text, reply.model, reply.session), ("OK", "fixture-a", "t1"))
        self.assertEqual(args[args.index("-m") + 1], "fixture-a")
        self.assertIn('model_reasoning_effort="e2"', args)
        self.assertIn('service_tier="tier-x"', args)
        self.assertEqual(args[args.index("--sandbox") + 1], "read-only")
        self.assertEqual(args[args.index("--ask-for-approval") + 1], "never")
        self.assertIn("--ignore-user-config", args)
        self.assertIn("shell_tool", args)
        self.assertLess(args.index("-m"), args.index("exec"))


class ClaudeTests(unittest.TestCase):
    def test_initialize_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "claude", FAKE_CLAUDE)
            found = ClaudeAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "available", found)
        self.assertEqual(found["plan"], "Fixture Plan")
        one, plain = found["models"]
        self.assertEqual((one["id"], one["efforts"], [s["id"] for s in one["speeds"]]), ("alias-one", ["lo", "hi"], ["fastMode"]))
        self.assertEqual((plain["efforts"], plain["speeds"]), ([], []))
        self.assertTrue(plain["speed_reason"])

    def test_call_parses_reported_model(self):
        stream = "\n".join(json.dumps(x) for x in (
            {"type": "system", "subtype": "init", "model": "reported-model", "session_id": "s1"},
            {"type": "result", "subtype": "success", "is_error": False, "result": "OK", "session_id": "s1"}))
        choice = {"provider": "claude", "model": "alias-one", "effort": "hi", "speed": "fastMode"}
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stream, "")) as run:
            reply = ClaudeAdapter(lambda: "/fake/claude").call(choice, "p", files=False, env={}, timeout=5)
        args = run.call_args.args[0]
        self.assertEqual((reply.text, reply.model), ("OK", "reported-model"))
        self.assertEqual(args[args.index("--model") + 1], "alias-one")
        self.assertEqual(args[args.index("--effort") + 1], "hi")
        self.assertEqual(json.loads(args[args.index("--settings") + 1]), {"fastMode": True})
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--no-session-persistence", args)


class AntigravityTests(unittest.TestCase):
    def test_effort_comes_from_id_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "agy", FAKE_AGY)
            found = AntigravityAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "available", found)
        self.assertEqual([(m["id"], m["label"], m["efforts"]) for m in found["models"]],
                         [("fam-one", "Fam One", ["lo", "hi"]), ("solo", "Solo Model", [])])
        self.assertTrue(found["models"][0]["speed_reason"])

    def test_call_rebuilds_full_id(self):
        out = json.dumps({"event": "init", "init": {"model": "fam-one-hi"}}) + "\n" + json.dumps(
            {"event": "result", "result": {"status": "SUCCESS", "response": "OK\n", "conversation_id": "c1"}})
        with patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, out, "")) as run:
            reply = AntigravityAdapter(lambda: "/fake/agy").call(
                {"provider": "antigravity", "model": "fam-one", "effort": "hi", "speed": ""}, "p", files=False, env={}, timeout=5)
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("--model") + 1], "fam-one-hi")
        self.assertEqual((reply.text, reply.model), ("OK", "fam-one-hi"))


class OllamaTests(unittest.TestCase):
    def test_not_running_is_unavailable(self):
        found = OllamaAdapter("http://127.0.0.1:9").discover()
        self.assertEqual(found["state"], "unavailable")
        self.assertIn("not running", found["reason"])

    def test_tags_and_thinking_levels(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, payload):
                body = json.dumps(payload).encode(); self.send_response(200); self.end_headers(); self.wfile.write(body)
            def do_GET(self): self.reply({"models": [{"name": "local-a"}, {"name": "local-b"}]})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/show":
                    self.reply({"thinking": {"values": ["t1", "t2"], "default": "t1"}} if body["model"] == "local-a" else {"thinking": {"values": [False]}})
                else:
                    self.reply({"model": body["model"], "message": {"content": "OK " + str(body.get("think"))}})
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            adapter = OllamaAdapter(f"http://127.0.0.1:{server.server_port}")
            found = adapter.discover()
            self.assertEqual([(m["id"], m["efforts"]) for m in found["models"]], [("local-a", ["t1", "t2"]), ("local-b", [])])
            reply = adapter.call({"provider": "ollama", "model": "local-a", "effort": "t2", "speed": ""}, "p", files=False, env={}, timeout=5)
            self.assertEqual((reply.text, reply.model), ("OK t2", "local-a"))
        finally:
            server.shutdown(); server.server_close()


class FakeAdapter:
    name, label = "fake", "Fake"

    def __init__(self, state="available"):
        self.state, self.calls, self.discoveries = state, [], 0

    def discover(self, env=None):
        self.discoveries += 1
        if self.state != "available":
            return {"provider": self.name, "label": self.label, "state": "unavailable", "reason": "fixture offline", "models": []}
        return {"provider": self.name, "label": self.label, "state": "available", "reason": "", "models": [
            {"id": "m1", "label": "M1", "efforts": ["x", "y"], "speeds": [{"id": "quick", "label": "Quick"}], "speed_reason": ""},
            {"id": "m2", "label": "M2", "efforts": [], "speeds": [], "speed_reason": "no tiers"}]}

    def call(self, choice, prompt, **options):
        self.calls.append((choice, prompt, options))
        return ai_providers.Reply("READY", choice["model"] + "-reported", "")


@contextmanager
def chosen_codex(directory, server, purpose="live_analysis"):
    """A real CodexAdapter with fixture discovery and a saved choice, patched into server.AI."""
    adapter = CodexAdapter(lambda: "/fake/codex")
    offered = {"provider": "codex", "label": "Codex", "state": "available", "reason": "",
               "models": [{"id": "fixture-model", "label": "F", "efforts": ["fixture-effort"], "speeds": [], "speed_reason": "none"}]}
    service = AIService(Path(directory) / "config.json", {}, adapters=[adapter])
    with patch.object(adapter, "discover", return_value=offered), patch.object(server, "AI", service):
        service.save(purpose, {"provider": "codex", "model": "fixture-model", "effort": "fixture-effort", "speed": ""})
        yield service


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        self.adapter = FakeAdapter()
        self.service = AIService(self.path, {}, adapters=[self.adapter])

    def test_missing_choice_needs_choice_and_call_refuses(self):
        self.assertEqual(self.service.status("summary_rewrite")["state"], "needs_choice")
        with self.assertRaisesRegex(RuntimeError, "AI_CHOICE"):
            self.service.run("summary_rewrite", "p")

    def test_save_preserves_other_sections_and_mode(self):
        swift_written = {"auto_record": {"enabled": True, "min_duration_seconds": 30},
                         "live_transcription": {"enabled": False}, "recordings_dir": "~/x", "unknown": [1, 2.5, None]}
        self.path.write_text(json.dumps(swift_written, indent=2, sort_keys=True))
        self.path.chmod(0o640)
        self.service.save("live_analysis", {"provider": "fake", "model": "m1", "effort": "y", "speed": "quick"})
        saved = json.loads(self.path.read_text())
        self.assertEqual({k: v for k, v in saved.items() if k != "ai"}, swift_written)
        self.assertEqual(saved["ai"]["purposes"]["live_analysis"], {"provider": "fake", "model": "m1", "effort": "y", "speed": "quick"})
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.service.save("summary_rewrite", {"provider": "fake", "model": "m2", "effort": "", "speed": ""})
        self.assertEqual(set(json.loads(self.path.read_text())["ai"]["purposes"]), {"live_analysis", "summary_rewrite"})

    def test_shared_config_contract_with_swift_writer(self):
        """fixture_shared_config.json is shaped like Swift Config.write output (sorted keys,
        pretty-printed, escaped slashes). Swift Config.update keeps unknown top-level keys
        (Config.swift:550-566), so `ai` survives Swift writes; Python must equally keep
        every key outside `ai` and must leave the other purposes alone."""
        fixture = json.loads((Path(__file__).with_name("fixture_shared_config.json")).read_text())
        self.path.write_text(json.dumps(fixture))
        self.service.save("summary_rewrite", {"provider": "fake", "model": "m2", "effort": "", "speed": ""})
        saved = json.loads(self.path.read_text())
        self.assertEqual({k: v for k, v in saved.items() if k != "ai"}, {k: v for k, v in fixture.items() if k != "ai"})
        self.assertEqual(saved["ai"]["purposes"]["live_analysis"], fixture["ai"]["purposes"]["live_analysis"])
        schema = json.loads((Path(__file__).resolve().parents[2] / "docs/config.schema.json").read_text())
        allowed = set(schema["properties"]["ai"]["properties"]["purposes"]["propertyNames"]["enum"])
        required = schema["$defs"]["choice"]["required"]
        for purpose, choice in saved["ai"]["purposes"].items():
            self.assertIn(purpose, allowed)
            self.assertEqual(sorted(choice), sorted(required))
        self.assertTrue(set(ai_providers.PURPOSES) <= allowed)

    def test_new_file_is_private(self):
        self.service.save("live_translation", {"provider": "fake", "model": "m2", "effort": "", "speed": ""})
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_malformed_config_is_never_overwritten(self):
        self.path.write_text("{not json")
        with self.assertRaises(ValueError):
            self.service.save("live_translation", {"provider": "fake", "model": "m2", "effort": "", "speed": ""})
        self.assertEqual(self.path.read_text(), "{not json")

    def test_rejects_choices_the_provider_does_not_offer(self):
        for bad in ({"provider": "fake", "model": "absent", "effort": "", "speed": ""},
                    {"provider": "fake", "model": "m1", "effort": "", "speed": ""},
                    {"provider": "fake", "model": "m1", "effort": "z", "speed": ""},
                    {"provider": "fake", "model": "m2", "effort": "", "speed": "quick"},
                    {"provider": "nobody", "model": "m2", "effort": "", "speed": ""}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.service.save("live_analysis", bad)
        with self.assertRaises(ValueError):
            self.service.save("no_such_purpose", {"provider": "fake", "model": "m2", "effort": "", "speed": ""})

    def test_stored_choice_no_longer_offered_is_unavailable_with_reason(self):
        self.path.write_text(json.dumps({"ai": {"purposes": {"frame_relevance": {"provider": "fake", "model": "gone", "effort": "", "speed": ""}}}}))
        status = self.service.status("frame_relevance")
        self.assertEqual(status["state"], "unavailable")
        self.assertIn("gone", status["reason"])
        with self.assertRaisesRegex(RuntimeError, "AI_UNAVAILABLE"):
            self.service.run("frame_relevance", "p")
        offline = AIService(self.path, {}, adapters=[FakeAdapter("down")])
        self.path.write_text(json.dumps({"ai": {"purposes": {"frame_relevance": {"provider": "fake", "model": "m2", "effort": "", "speed": ""}}}}))
        self.assertIn("fixture offline", offline.status("frame_relevance")["reason"])

    def test_run_routes_choice_and_caches_discovery(self):
        self.service.save("live_analysis", {"provider": "fake", "model": "m1", "effort": "x", "speed": ""})
        reply = self.service.run("live_analysis", "hello", files=True)
        self.service.run("live_analysis", "again")
        self.assertEqual(reply.model, "m1-reported")
        self.assertEqual(self.adapter.calls[0][0]["effort"], "x")
        self.assertTrue(self.adapter.calls[0][2]["files"])
        self.assertEqual(self.adapter.discoveries, 1)

    def test_concurrent_writers_do_not_lose_updates(self):
        purposes = list(ai_providers.PURPOSES)
        threads = [threading.Thread(target=self.service.save, args=(p, {"provider": "fake", "model": "m2", "effort": "", "speed": ""}))
                   for p in purposes * 3]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(set(json.loads(self.path.read_text())["ai"]["purposes"]), set(purposes))


class SessionOwnershipTests(unittest.TestCase):
    def test_a_session_is_resumed_only_by_the_choice_that_opened_it(self):
        import server
        with tempfile.TemporaryDirectory() as tmp, chosen_codex(tmp, server):
            for key, expected in (("another-choice", ""), (server.AI.choice_key("live_analysis"), "old-thread")):
                session = server.CodexSession(Path(tmp) / "s.json")
                session.thread_id, session.thread_key = "old-thread", key
                session.folder_generation = server.LOCAL_CONTEXT.generation()
                session.google_generation = server.GOOGLE_CONTEXT._generation
                seen = []
                def model(prompt, planning=False):
                    seen.append(session.thread_id)
                    return "answer"
                with patch.object(session, "_run_ai", side_effect=model), \
                     patch.object(server.GOOGLE_CONTEXT, "augment", return_value=""), \
                     patch.object(server.LOCAL_CONTEXT, "augment", return_value=""):
                    session.ask("q", "", "m", "", {"repositories": []})
                self.assertEqual(seen[-1], expected)


class NoHardcodedModelsTests(unittest.TestCase):
    def test_production_sources_hold_no_model_ids(self):
        import re
        pattern = re.compile(r"gpt-[0-9]|claude-(opus|sonnet|haiku)|gemini-[0-9]")
        web = Path(__file__).resolve().parent
        hits = [f"{p.name}:{n}" for p in sorted(web.iterdir()) if p.suffix in {".py", ".js", ".html"} and not p.name.startswith("test_")
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
