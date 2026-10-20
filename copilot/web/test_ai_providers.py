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
import textwrap
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import ai_providers
from ai_providers import (AIChoiceError, AIService, AntigravityAdapter, ClaudeAdapter, CodexAdapter,
                          OllamaAdapter, Result)

PY = sys.executable
WEB = Path(__file__).resolve().parent
os.environ.setdefault("MEETING_COPILOT_AI_WORKDIR", tempfile.mkdtemp(prefix="meetontrack-test-workdir-"))

FAKE_CODEX = r'''
import json, sys
if sys.argv[1:] == ["--version"]:
    print("codex-cli 9.9.9"); sys.exit(0)
pages = {None: ([{"id": "fixture-a", "displayName": "Fixture A", "hidden": False, "inputModalities": ["text", "image"],
                  "supportedReasoningEfforts": [{"reasoningEffort": "e1"}, {"reasoningEffort": "e2"}],
                  "defaultReasoningEffort": "e1", "serviceTiers": [{"id": "tier-x", "name": "Quick"}]},
                 {"id": "fixture-hidden", "hidden": True, "supportedReasoningEfforts": []}], "p2"),
         "p2": ([{"id": "fixture-b", "displayName": "Fixture B", "supportedReasoningEfforts": [], "serviceTiers": []},
                 {"id": "fixture-odd", "displayName": "Odd"}], None)}
for line in sys.stdin:
    msg = json.loads(line)
    method, mid = msg.get("method"), msg.get("id")
    if mid is None: continue
    if method == "initialize": result = {"userAgent": "fake"}
    elif method == "model/list":
        data, nxt = pages[(msg.get("params") or {}).get("cursor")]
        result = {"data": data, "nextCursor": nxt}
    elif method == "account/read": result = {"account": ACCOUNT, "requiresOpenaiAuth": True}
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
assert "--setting-sources" in args and "--restricted" in args, args
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("type") == "control_request":
        print(json.dumps({"type": "system", "subtype": "hook_started"}), flush=True)
        print(json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": msg["request_id"], "response": {
            "models": [{"value": "alias-one", "displayName": "Alias One", "supportedEffortLevels": ["lo", "hi"], "supportsFastMode": True},
                       {"value": "plain", "displayName": "Plain"},
                       {"value": "vague", "displayName": "Vague", "supportsEffort": True}],
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

FLOOD = r'''
import json, sys
sys.stdin.readline()
while True:
    print(json.dumps({"method": "noise", "params": {}}), flush=True)
'''


def fake_cli(directory, name, source, **values):
    path = Path(directory) / name
    for key, value in values.items():
        source = source.replace(key, value)
    path.write_text(f"#!{PY}\n" + source)
    path.chmod(0o755)
    return path


def codex_call(choice, **options):
    event = '{"type":"thread.started","thread_id":"t1"}\n{"type":"item.completed","item":{"type":"agent_message","text":"OK"}}'
    with patch.object(ai_providers, "_run", return_value=Result(0, event, "")) as run:
        reply = CodexAdapter(lambda: "/fake/codex").call(choice, "prompt", executable="/fake/pkg/bin/codex",
                                                          env={}, timeout=5, **options)
    return reply, run.call_args.args[0]


class CodexDiscoveryTests(unittest.TestCase):
    def test_pages_models_skips_hidden_and_reads_account_and_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "codex", FAKE_CODEX, ACCOUNT='{"type": "chatgpt", "planType": "fixture-plan"}')
            found = CodexAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "available", found)
        self.assertEqual((found["plan"], found["executable"]), ("fixture-plan", str(binary)))
        self.assertEqual([m["id"] for m in found["models"]], ["fixture-a", "fixture-b", "fixture-odd"])
        first, second, odd = found["models"]
        self.assertEqual((first["efforts"], first["speeds"], first["image"]), (["e1", "e2"], [{"id": "tier-x", "label": "Quick"}], True))
        self.assertIsNone(second["image"])  # not reported: unknown, never assumed
        self.assertTrue(odd["problem"])  # no effort list at all: capability unknown

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

    def test_missing_binary_hang_and_flood_stop_at_the_deadline(self):
        self.assertEqual(CodexAdapter(lambda: None).discover()["state"], "unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            for source, reason in (("import time\ntime.sleep(30)\n", "respond"), (FLOOD, "")):
                binary = fake_cli(tmp, "codex", source)
                started = time.monotonic()
                with patch.object(ai_providers, "DISCOVERY_TIMEOUT", 1):
                    found = CodexAdapter(lambda: binary).discover()
                self.assertEqual(found["state"], "unavailable")
                self.assertIn(reason, found["reason"])
                self.assertLess(time.monotonic() - started, 5)


class CodexCallTests(unittest.TestCase):
    def test_call_uses_choice_and_a_read_only_profile_without_tools(self):
        reply, args = codex_call({"provider": "codex", "model": "fixture-a", "effort": "e2", "speed": "tier-x"},
                                 keep_session=True)
        self.assertEqual((reply.text, reply.model, reply.session), ("OK", "fixture-a", "t1"))
        self.assertEqual((args[0], args[args.index("-m") + 1]), ("/fake/pkg/bin/codex", "fixture-a"))
        self.assertIn('model_reasoning_effort="e2"', args)
        self.assertIn('service_tier="tier-x"', args)
        self.assertEqual(args[args.index("--ask-for-approval") + 1], "never")
        self.assertIn('default_permissions="meetontrack"', args)
        profile = next(a for a in args if a.startswith("permissions.meetontrack.filesystem="))
        self.assertNotIn('"write"', profile)
        self.assertIn('"/fake/pkg"="read"', profile)  # Codex re-executes its own package
        self.assertNotIn(str(Path.home()) + '"', profile)
        self.assertIn("--ignore-user-config", args)
        self.assertIn("shell_tool", args)
        self.assertNotIn("--ephemeral", args)
        self.assertLess(args.index("-m"), args.index("exec"))

    def test_roots_are_the_only_extra_readable_paths_and_standard_sends_no_tier(self):
        _, args = codex_call({"provider": "codex", "model": "fixture-a", "effort": "e1", "speed": "standard"},
                             roots=["/repos/one", "/repos/two"])
        profile = next(a for a in args if a.startswith("permissions.meetontrack.filesystem="))
        self.assertIn('"/repos/one"="read"', profile)
        self.assertIn('"/repos/two"="read"', profile)
        self.assertNotIn("shell_tool", args)  # reading repositories needs its tools, inside the profile
        self.assertFalse(any(a.startswith("service_tier") for a in args))
        self.assertIn("--ephemeral", args)

    def test_resume_keeps_the_profile(self):
        _, args = codex_call({"provider": "codex", "model": "fixture-a", "effort": "e1", "speed": "standard"},
                             roots=["/repos/one"], resume="t0")
        self.assertEqual(args[args.index("exec") + 1], "resume")
        self.assertIn('default_permissions="meetontrack"', args)
        self.assertLess(args.index('default_permissions="meetontrack"'), args.index("exec"))


class ClaudeTests(unittest.TestCase):
    def test_initialize_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "claude", FAKE_CLAUDE)
            found = ClaudeAdapter(lambda: binary).discover()
        self.assertEqual(found["state"], "available", found)
        self.assertEqual(found["plan"], "Fixture Plan")
        one, plain, vague = found["models"]
        self.assertEqual((one["id"], one["efforts"], [s["id"] for s in one["speeds"]]), ("alias-one", ["lo", "hi"], ["fastMode"]))
        self.assertEqual((plain["efforts"], plain["speeds"], plain["problem"]), ([], [], ""))
        self.assertTrue(plain["speed_reason"])
        self.assertIsNone(one["image"])
        self.assertTrue(vague["problem"])

    def run_call(self, choice, **options):
        stream = "\n".join(json.dumps(x) for x in (
            {"type": "system", "subtype": "init", "model": "reported-model", "session_id": "s1"},
            {"type": "result", "subtype": "success", "is_error": False, "result": "OK", "session_id": "s1"}))
        seen = {}

        def run(argv, prompt, env, timeout, cwd):
            seen.update(argv=argv, prompt=prompt, cwd=cwd, files=sorted(os.listdir(cwd)))
            return Result(0, stream, "")
        with patch.object(ai_providers, "_run", side_effect=run):
            reply = ClaudeAdapter(lambda: "/fake/claude").call(choice, "p", executable="/fake/claude", env={},
                                                                timeout=5, **options)
        return reply, seen

    def test_call_parses_reported_model_and_has_no_tools(self):
        reply, seen = self.run_call({"provider": "claude", "model": "alias-one", "effort": "hi", "speed": "fastMode"})
        args = seen["argv"]
        self.assertEqual((reply.text, reply.model), ("OK", "reported-model"))
        self.assertEqual(args[args.index("--model") + 1], "alias-one")
        self.assertEqual(args[args.index("--effort") + 1], "hi")
        self.assertEqual(json.loads(args[args.index("--settings") + 1]), {"fastMode": True})
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--restricted", args)
        self.assertIn("--no-session-persistence", args)
        self.assertNotEqual(seen["cwd"], str(Path.home()))

    def test_roots_become_add_dirs_and_the_only_file_tools(self):
        _, seen = self.run_call({"provider": "claude", "model": "plain", "effort": "", "speed": ""},
                                roots=["/repos/one", "/repos/two"], keep_session=True)
        args = seen["argv"]
        self.assertEqual([a for a in args if a.startswith("--add-dir")], ["--add-dir=/repos/one", "--add-dir=/repos/two"])
        self.assertEqual(args[args.index("--tools") + 1], "Read,Grep,Glob")
        self.assertIn("--restricted", args)

    def test_screenshot_is_read_from_a_directory_holding_only_a_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "frame.jpg"
            image.write_bytes(b"jpeg")
            (Path(tmp) / "secret.txt").write_text("x")
            _, seen = self.run_call({"provider": "claude", "model": "plain", "effort": "", "speed": ""}, image=image)
        self.assertEqual(seen["files"], ["frame.jpg"])
        self.assertNotEqual(seen["cwd"], tmp)
        self.assertEqual(seen["argv"][seen["argv"].index("--tools") + 1], "Read")
        self.assertNotIn(tmp, seen["prompt"])


class AntigravityTests(unittest.TestCase):
    def test_models_are_listed_but_every_purpose_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = fake_cli(tmp, "agy", FAKE_AGY)
            adapter = AntigravityAdapter(lambda: binary)
            found = adapter.discover()
            self.assertEqual([(m["id"], m["label"], m["efforts"]) for m in found["models"]],
                             [("fam-one", "Fam One", ["lo", "hi"]), ("solo", "Solo Model", [])])
            self.assertEqual(found["state"], "unavailable")
            self.assertIn("always-proceed", found["reason"])
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"ai": {"purposes": {p: {"provider": "antigravity", "model": "solo", "effort": "",
                                                                "speed": ""} for p in ai_providers.PURPOSES}}}))
            service = AIService(path, {}, adapters=[adapter])
            for purpose in ai_providers.PURPOSES:
                status = service.status(purpose)
                self.assertEqual(status["state"], "unavailable", purpose)
                self.assertIn("always-proceed", status["reason"])
        with self.assertRaises(AIChoiceError):
            adapter.call({"provider": "antigravity", "model": "solo", "effort": "", "speed": ""}, "p")


class BinaryLookupTests(unittest.TestCase):
    def test_codex_lookup_uses_the_list_shared_with_swift(self):
        listed = json.loads((WEB / "tool_locations.json").read_text())["codex"]
        self.assertIn("/Applications/ChatGPT.app/Contents/Resources/codex", listed)
        candidates = [str(path) for path in ai_providers.CODEX.candidates() if path]
        for place in listed:
            self.assertIn(os.path.expanduser(place), candidates)


class OllamaTests(unittest.TestCase):
    def test_not_running_is_unavailable(self):
        found = OllamaAdapter("http://127.0.0.1:9").discover()
        self.assertEqual(found["state"], "unavailable")
        self.assertIn("not running", found["reason"])

    @contextmanager
    def server(self, show, delay=0.0):
        chats = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, payload, status=200):
                body = json.dumps(payload).encode(); self.send_response(status); self.end_headers(); self.wfile.write(body)
            def do_GET(self): self.reply({"models": [{"name": "local-a"}, {"name": "local-b"}, {"name": "local-c"}]})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/api/show":
                    time.sleep(delay)
                    answer = show.get(body["model"])
                    return self.reply(answer) if answer is not None else self.reply({"error": "boom"}, 500)
                chats.append(body)
                self.reply({"model": body["model"], "message": {"content": f"OK {body.get('think')} {len(body['messages'])}"}})
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            yield OllamaAdapter(f"http://127.0.0.1:{httpd.server_port}"), chats
        finally:
            httpd.shutdown(); httpd.server_close()

    def test_thinking_vision_and_isolated_failures(self):
        show = {"local-a": {"thinking": {"values": ["t1", "t2"]}, "capabilities": ["completion", "vision"]},
                "local-b": {"thinking": {"values": [False]}, "capabilities": ["completion"]}}
        with self.server(show) as (adapter, _):
            found = adapter.discover()
        a, b, c = found["models"]
        self.assertEqual((a["efforts"], a["image"], b["efforts"], b["image"]), (["t1", "t2"], True, [], False))
        self.assertTrue(c["problem"])  # one model failing does not hide the others
        self.assertEqual(found["state"], "available")

    def test_thinking_without_levels_is_unknown_not_none(self):
        show = {"local-a": {"capabilities": ["completion", "thinking"]},
                "local-b": {"thinking": {}, "capabilities": ["completion"]},
                "local-c": {"capabilities": ["completion"]}}
        with self.server(show) as (adapter, _):
            a, b, c = adapter.discover()["models"]
        self.assertIn("levels", a["problem"])
        self.assertIn("levels", b["problem"])
        self.assertEqual((c["problem"], c["efforts"]), ("", []))
        state, _ = ai_providers.choice_problem({"state": "available", "models": [a]},
                                               {"provider": "ollama", "model": "local-a", "effort": "", "speed": ""})
        self.assertEqual(state, "unavailable")

    def test_one_budget_for_all_model_probes(self):
        show = {name: {"capabilities": ["completion"]} for name in ("local-a", "local-b", "local-c")}
        with self.server(show, delay=0.6) as (adapter, _), patch.object(ai_providers, "DISCOVERY_TIMEOUT", 1):
            started = time.monotonic()
            found = adapter.discover()
        self.assertLess(time.monotonic() - started, 2.5)
        self.assertTrue(found["models"][-1]["problem"])

    def test_chat_keeps_its_own_history_and_reads_no_files(self):
        choice = {"provider": "ollama", "model": "local-a", "effort": "t2", "speed": ""}
        with self.server({}) as (adapter, chats):
            first = adapter.call(choice, "one", timeout=5, keep_session=True)
            second = adapter.call(choice, "two", timeout=5, resume=first.session, keep_session=True)
            fresh = adapter.call(choice, "three", timeout=5)
            with self.assertRaises(AIChoiceError):
                adapter.call(choice, "p", timeout=5, roots=["/repos/one"])
        self.assertEqual((first.text, second.text, fresh.text), ("OK t2 1", "OK t2 3", "OK t2 1"))
        self.assertEqual(second.session, first.session)
        self.assertEqual([m["content"] for m in chats[1]["messages"]], ["one", "OK t2 1", "two"])
        self.assertEqual(fresh.session, "")


class FakeAdapter:
    name, label, reads_files = "fake", "Fake", True

    def __init__(self, state="available"):
        self.state, self.calls, self.discoveries, self.version = state, [], 0, "v1"

    def identity(self, env=None):
        return self.version

    def discover(self, env=None):
        self.discoveries += 1
        if self.state != "available":
            return {"provider": self.name, "label": self.label, "state": "unavailable", "reason": "fixture offline", "models": []}
        return {"provider": self.name, "label": self.label, "state": "available", "reason": "",
                "executable": f"/fake/{self.version}", "models": [
                    ai_providers._model("m1", "M1", ["x", "y"], [{"id": "quick", "label": "Quick"}], image=True),
                    ai_providers._model("m2", "M2", [], [], "no tiers", image=False),
                    ai_providers._model("m3", "M3", problem="fixture schema unknown")]}

    def call(self, choice, prompt, **options):
        self.calls.append((choice, prompt, options))
        return ai_providers.Reply("READY", choice["model"] + "-reported", "")


@contextmanager
def chosen_codex(directory, server, purpose="live_analysis"):
    """A real CodexAdapter with fixture discovery and a saved choice, patched into server.AI."""
    adapter = CodexAdapter(lambda: "/fake/codex")
    offered = {"provider": "codex", "label": "Codex", "state": "available", "reason": "", "executable": "/fake/codex",
               "models": [ai_providers._model("fixture-model", "F", ["fixture-effort"], [], "none")]}
    service = AIService(Path(directory) / "config.json", {}, adapters=[adapter])
    with patch.object(adapter, "discover", return_value=offered), patch.object(adapter, "identity", return_value="id"), \
            patch.object(server, "AI", service):
        service.save(purpose, {"provider": "codex", "model": "fixture-model", "effort": "fixture-effort", "speed": ""})
        yield service


M1 = {"provider": "fake", "model": "m1", "effort": "y", "speed": "quick"}
M2 = {"provider": "fake", "model": "m2", "effort": "", "speed": ""}


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "config.json"
        self.adapter = FakeAdapter()
        self.service = AIService(self.path, {}, adapters=[self.adapter])

    def write(self, purposes):
        self.path.write_text(json.dumps({"ai": {"purposes": purposes}}))

    def test_missing_or_partial_choice_needs_choice_and_call_refuses(self):
        self.assertEqual(self.service.status("summary_rewrite")["state"], "needs_choice")
        with self.assertRaises(AIChoiceError) as raised:
            self.service.run("summary_rewrite", "p")
        self.assertEqual(raised.exception.state, "needs_choice")
        self.assertTrue(str(raised.exception).startswith("AI_CHOICE"))
        self.write({"summary": {"provider": "fake", "model": "m1"}})  # e.g. migrated without effort and speed
        status = self.service.status("summary")
        self.assertEqual(status["state"], "needs_choice")
        self.assertIn("effort", status["reason"])

    def test_speed_and_effort_must_be_chosen_explicitly(self):
        for choice, state in (({**M1, "speed": ""}, "needs_choice"), ({**M1, "effort": ""}, "needs_choice"),
                              ({**M1, "speed": "standard"}, "ready"), (M1, "ready"),
                              ({**M2, "speed": "standard"}, "needs_choice"),
                              ({"provider": "fake", "model": "m3", "effort": "", "speed": ""}, "unavailable")):
            with self.subTest(choice=choice):
                self.write({"live_translation": choice})
                self.assertEqual(self.service.status("live_translation")["state"], state)

    def test_screenshots_need_a_model_reported_to_accept_images(self):
        self.write({"frame_relevance": M2})
        self.assertIn("images", self.service.status("frame_relevance")["reason"])
        self.write({"frame_relevance": M1})
        self.assertEqual(self.service.status("frame_relevance")["state"], "ready")

    def test_save_preserves_other_sections_and_writes_private_files(self):
        swift_written = {"auto_record": {"enabled": True, "min_duration_seconds": 30},
                         "live_transcription": {"enabled": False}, "recordings_dir": "~/x", "unknown": [1, 2.5, None]}
        self.path.write_text(json.dumps(swift_written, indent=2, sort_keys=True))
        self.path.chmod(0o644)
        self.service.save("live_analysis", M1)
        saved = json.loads(self.path.read_text())
        self.assertEqual({k: v for k, v in saved.items() if k != "ai"}, swift_written)
        self.assertEqual(saved["ai"]["purposes"]["live_analysis"], M1)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.service.save("summary_rewrite", M2)
        self.assertEqual(set(json.loads(self.path.read_text())["ai"]["purposes"]), {"live_analysis", "summary_rewrite"})

    def test_shared_config_contract_with_swift_writer(self):
        """fixture_shared_config.json is shaped like Swift Config.write output (sorted keys,
        pretty-printed, escaped slashes). Python must keep every key outside `ai` and must
        leave the other purposes alone; the schema lists every purpose and choice key."""
        fixture = json.loads((WEB / "fixture_shared_config.json").read_text())
        self.path.write_text(json.dumps(fixture))
        self.service.save("summary_rewrite", M2)
        saved = json.loads(self.path.read_text())
        self.assertEqual({k: v for k, v in saved.items() if k != "ai"}, {k: v for k, v in fixture.items() if k != "ai"})
        self.assertEqual(saved["ai"]["purposes"]["live_analysis"], fixture["ai"]["purposes"]["live_analysis"])
        schema = json.loads((WEB.parents[1] / "docs/config.schema.json").read_text())
        allowed = set(schema["properties"]["ai"]["properties"]["purposes"]["propertyNames"]["enum"])
        keys = set(schema["$defs"]["choice"]["properties"])
        self.assertEqual(keys, set(ai_providers.CHOICE_KEYS))
        for purpose, choice in saved["ai"]["purposes"].items():
            self.assertIn(purpose, allowed)
            self.assertEqual(set(choice), keys)  # Python always writes a complete choice
        self.assertEqual(set(ai_providers.PURPOSES), allowed)

    def test_malformed_config_is_never_overwritten(self):
        self.path.write_text("{not json")
        with self.assertRaises(ValueError):
            self.service.save("live_translation", M2)
        self.assertEqual(self.path.read_text(), "{not json")

    def test_rejects_choices_the_provider_does_not_offer(self):
        for bad in ({**M2, "model": "absent"}, {**M1, "effort": ""}, {**M1, "effort": "z"},
                    {**M2, "speed": "quick"}, {**M2, "provider": "nobody"}, {**M1, "speed": ""}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.service.save("live_analysis", bad)
        with self.assertRaises(ValueError):
            self.service.save("no_such_purpose", M2)

    def test_stored_choice_no_longer_offered_is_unavailable_with_reason(self):
        self.write({"frame_relevance": {**M2, "model": "gone"}})
        status = self.service.status("frame_relevance")
        self.assertEqual(status["state"], "unavailable")
        self.assertIn("gone", status["reason"])
        with self.assertRaisesRegex(AIChoiceError, "AI_UNAVAILABLE"):
            self.service.run("frame_relevance", "p")
        offline = AIService(self.path, {}, adapters=[FakeAdapter("down")])
        self.write({"live_translation": M2})
        self.assertIn("fixture offline", offline.status("live_translation")["reason"])

    def test_run_routes_choice_to_the_discovered_executable_and_caches_discovery(self):
        self.service.save("live_analysis", {**M1, "effort": "x"})
        reply = self.service.run("live_analysis", "hello", roots=["/r"])
        self.service.run("live_analysis", "again")
        self.assertEqual(reply.model, "m1-reported")
        self.assertEqual(self.adapter.calls[0][0]["effort"], "x")
        self.assertEqual(self.adapter.calls[0][2]["roots"], ["/r"])
        self.assertEqual(self.adapter.calls[0][2]["executable"], "/fake/v1")
        self.assertEqual(self.adapter.discoveries, 1)

    def test_executable_change_rediscovers_and_changes_the_key(self):
        self.service.save("live_analysis", M1)
        before = self.service.resolve("live_analysis")
        self.adapter.version = "v2"
        after = self.service.resolve("live_analysis")
        self.assertEqual(self.adapter.discoveries, 2)
        self.assertNotEqual(before.key, after.key)
        self.assertEqual(after.executable, "/fake/v2")

    def test_a_ticket_is_a_snapshot(self):
        self.service.save("live_analysis", M1)
        ticket = self.service.resolve("live_analysis")
        self.service.save("live_analysis", M2)
        self.service.run("live_analysis", "p", ticket=ticket)
        self.assertEqual(self.adapter.calls[-1][0], M1)

    def test_concurrent_threads_do_not_lose_updates(self):
        purposes = list(ai_providers.PURPOSES)
        threads = [threading.Thread(target=self.service.settings.set_purpose, args=(p, M2)) for p in purposes * 3]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(set(json.loads(self.path.read_text())["ai"]["purposes"]), set(purposes))

    def test_processes_python_and_native_style_writers_do_not_lose_updates(self):
        """A native-style writer (the Swift protocol: flock on config.json.lock held across
        read-modify-replace) and the Python writer, in separate processes, at once."""
        python_writer = textwrap.dedent(f"""
            import sys; sys.path.insert(0, {str(WEB)!r})
            from ai_providers import AISettings
            settings = AISettings(sys.argv[1])
            for n in range(15):
                settings.set_purpose(f"p{{sys.argv[2]}}_{{n}}", {{"provider": "x", "model": "y", "effort": "", "speed": ""}})
        """)
        native_writer = textwrap.dedent("""
            import fcntl, json, os, sys, tempfile, time
            path = sys.argv[1]
            for n in range(15):
                fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    data = json.load(open(path)) if os.path.exists(path) else {}
                    time.sleep(0.002)
                    data[f"native{sys.argv[2]}_{n}"] = n
                    handle, temp = tempfile.mkstemp(dir=os.path.dirname(path))
                    os.fchmod(handle, 0o600)
                    with os.fdopen(handle, "w") as stream:
                        json.dump(data, stream)
                    os.replace(temp, path)
                finally:
                    os.close(fd)
        """)
        workers = [subprocess.Popen([PY, "-c", source, str(self.path), str(n)])
                   for n in range(3) for source in (python_writer, native_writer)]
        self.assertEqual([w.wait(60) for w in workers], [0] * len(workers))
        saved = json.loads(self.path.read_text())
        self.assertEqual(len(saved["ai"]["purposes"]), 45)
        self.assertEqual(len([k for k in saved if k.startswith("native")]), 45)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)


class SessionOwnershipTests(unittest.TestCase):
    def test_a_session_is_resumed_only_by_the_choice_that_opened_it(self):
        import server
        with tempfile.TemporaryDirectory() as tmp, chosen_codex(tmp, server):
            current = server.AI.resolve("live_analysis").key
            for key, expected in (("another-choice", ""), (current, "old-thread")):
                session = server.CodexSession(Path(tmp) / "s.json")
                session.thread_id, session.thread_key = "old-thread", key
                session.folder_generation = server.LOCAL_CONTEXT.generation()
                session.google_generation = server.GOOGLE_CONTEXT._generation
                seen = []
                def model(prompt, planning=False):
                    seen.append((session.thread_id, session._ticket.key, session._roots))
                    return "answer"
                with patch.object(session, "_run_ai", side_effect=model), \
                     patch.object(server.GOOGLE_CONTEXT, "augment", return_value=""), \
                     patch.object(server.LOCAL_CONTEXT, "augment", return_value=""):
                    session.ask("q", "", "m", "", {"repositories": [{"name": "r", "path": "/repos/r"}]})
                self.assertEqual(seen[-1], (expected, current, ["/repos/r"]))

    def test_answers_read_only_the_scope_repositories(self):
        import server
        with tempfile.TemporaryDirectory() as tmp, chosen_codex(tmp, server):
            session = server.CodexSession(Path(tmp) / "s.json")
            event = '{"type":"item.completed","item":{"type":"agent_message","text":"FACT"}}'
            with patch.object(ai_providers, "_run", return_value=Result(0, event, "")) as run, \
                 patch.object(server.GOOGLE_CONTEXT, "augment", return_value=""), \
                 patch.object(server.LOCAL_CONTEXT, "augment", return_value=""):
                session.ask("q", "", "m", "", {"repositories": [{"name": "r", "path": "/repos/r"}]})
            argv, prompt = run.call_args.args[0], run.call_args.args[1]
        profile = next(a for a in argv if a.startswith("permissions.meetontrack.filesystem="))
        self.assertIn('"/repos/r"="read"', profile)
        self.assertNotIn(".config/meeting-copilot", profile)
        self.assertIn("<session_rules>", prompt)


class StructuredStateTests(unittest.TestCase):
    def test_screenshots_are_not_taken_or_judged_without_a_choice(self):
        import server
        with tempfile.TemporaryDirectory() as tmp:
            service = AIService(Path(tmp) / "config.json", {}, adapters=[FakeAdapter()])
            with patch.object(server, "AI", service), \
                 patch.object(server.subprocess, "run", side_effect=AssertionError("no screenshot")):
                with self.assertRaises(AIChoiceError):
                    server.FRAMES.capture({"meeting_id": "m"})
            self.assertTrue(server.FRAMES.last_error.startswith("AI_CHOICE"))

    def test_relevance_gate_does_not_call_a_missing_choice_irrelevant(self):
        from frame_relevance import frame_relevance
        def run(prompt):
            raise AIChoiceError("needs_choice", "choose")
        with self.assertRaises(AIChoiceError):
            frame_relevance("x.jpg", {"image_digest": "a"}, {}, None, run)

    def test_translation_reports_the_choice_state(self):
        from live_translation import LiveTranslation
        def run(prompt):
            raise AIChoiceError("needs_choice", "choose")
        translation = LiveTranslation(run)
        translation.meeting_id = "m"
        with patch.object(LiveTranslation, "_language", return_value=("de", 0.99)):
            translation._work(("m", "s", "t"), "Guten Tag")
        self.assertTrue(translation.error.startswith("AI_CHOICE"))
        self.assertEqual(translation.error_state, "needs_choice")


class NoHardcodedModelsTests(unittest.TestCase):
    def test_production_sources_hold_no_model_ids(self):
        import re
        pattern = re.compile(r"gpt-[0-9]|claude-(opus|sonnet|haiku)|gemini-[0-9]")
        hits = [f"{p.name}:{n}" for p in sorted(WEB.iterdir()) if p.suffix in {".py", ".js", ".html"} and not p.name.startswith("test_")
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
