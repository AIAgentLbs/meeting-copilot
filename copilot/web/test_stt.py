import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

import stt
from stt import STTService, apply_download_event

WEB = Path(__file__).resolve().parent
FIXTURE = (WEB / "fixture_stt_options.json").read_text(encoding="utf-8")
VOCABULARY = json.loads((WEB / "stt_vocabulary.json").read_text(encoding="utf-8"))
SCHEMA = WEB.parent.parent / "docs/config.schema.json"


class FakeRunner:
    def __init__(self, stdout=FIXTURE, returncode=0, stderr="", error=None):
        self.stdout, self.returncode, self.stderr, self.error, self.calls = stdout, returncode, stderr, error, []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(stdout=self.stdout, returncode=self.returncode, stderr=self.stderr)


class FakePopen:
    def __init__(self, lines, code):
        self.lines, self.code, self.args = lines, code, None

    def __call__(self, args, **kwargs):
        self.args = args
        return SimpleNamespace(stdout=iter(line + "\n" for line in self.lines), wait=lambda: self.code)


def wait_for(read, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        items = read()
        if items and items[0]["state"] != "running":
            return items[0]
        time.sleep(0.01)
    raise AssertionError("job did not finish")


class STTTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.config = self.dir / "config.json"
        self.root = self.dir / "recordings"
        self.root.mkdir()
        self.runner = FakeRunner()
        platform = unittest.mock.patch.object(stt, "WINDOWS", False)  # fixtures model the Mac recorder
        platform.start()
        self.addCleanup(platform.stop)

    def tearDown(self):
        self.temp.cleanup()

    def service(self, **kwargs):
        return STTService(self.config, self.dir / "meetingcopilot", self.root, runner=kwargs.pop("runner", self.runner), **kwargs)


class OptionsTests(STTTestCase):
    def test_parses_fixture_and_derives_best_for_from_facts(self):
        options = self.service().options()
        self.assertTrue(options["ok"])
        self.assertEqual(self.runner.calls[0][0][1:], ["stt-options", "--json"])
        self.assertEqual(self.runner.calls[0][1]["timeout"], 60)
        local, assembly, openai = options["engines"][:3]
        batch, stream, unknown, reused = local["models"]
        self.assertEqual(batch["best_for"], ["live", "multilingual", "offline"])
        self.assertEqual(reused["best_for"], ["live", "offline"])  # one language, no detection
        self.assertEqual(stream["best_for"], ["live", "lowest_latency", "multilingual", "offline"])  # two languages
        self.assertEqual(unknown["best_for"], ["live", "offline"])
        self.assertEqual(assembly["model_template"]["best_for"], ["multilingual", "speakers"])
        self.assertEqual(openai["models"][0]["best_for"], ["multilingual"])  # speakers null = unknown, not a tag

    def test_download_bytes_and_found_elsewhere_pass_through(self):
        local, assembly = self.service().options()["engines"][:2]
        batch, stream, unknown, reused = local["models"]
        self.assertEqual([m["download_bytes"] for m in local["models"]], [0, 700000000, None, 40000000])
        self.assertEqual(reused["found_elsewhere"][0]["bytes"], 440000000)
        self.assertEqual(batch["found_elsewhere"], [])
        self.assertNotIn("speaker_models", local)
        self.assertIsNone(assembly["model_template"]["download_bytes"])

    def test_malformed_local_file_facts_become_unknown(self):
        options = json.loads(FIXTURE)
        model = options["engines"][0]["models"][0]
        model["download_bytes"], model["found_elsewhere"] = -5, [{"path": "/a", "bytes": 1}, {"path": "", "bytes": 1},
                                                                 {"path": "/b", "bytes": True}, "junk", {"bytes": 3}]
        options["engines"][0]["models"][1]["download_bytes"] = "12"
        options["engines"][0]["models"][2]["found_elsewhere"] = "nope"
        del options["engines"][0]["models"][3]["download_bytes"]
        local = self.service(runner=FakeRunner(stdout=json.dumps(options))).options()["engines"][0]
        self.assertEqual((local["models"][0]["download_bytes"], local["models"][0]["found_elsewhere"]), (None, [{"path": "/a", "bytes": 1}]))
        self.assertIsNone(local["models"][1]["download_bytes"])
        self.assertEqual(local["models"][2]["found_elsewhere"], [])
        self.assertIsNone(local["models"][3]["download_bytes"])

    def test_refresh_flag_and_cache(self):
        service = self.service()
        service.options()
        service.options()
        self.assertEqual(len(self.runner.calls), 1)
        service.options(refresh=True)
        self.assertEqual(self.runner.calls[-1][0][-1], "--refresh")

    def test_malformed_contract_and_failures_are_cached_briefly(self):
        for runner, text in ((FakeRunner(stdout=json.dumps({"contract": "other/1", "engines": []})), "contract"),
                             (FakeRunner(stdout="not json"), "malformed"),
                             (FakeRunner(returncode=2, stderr="boom"), "boom"),
                             (FakeRunner(error=subprocess.TimeoutExpired("x", 60)), "60 s"),
                             (FakeRunner(error=FileNotFoundError(2, "No such file")), "cannot run")):
            service = self.service(runner=runner)
            result = service.options()
            self.assertEqual(result["ok"], False)
            self.assertIn(text, result["error"])
            service.options()
            self.assertEqual(len(runner.calls), 1)  # failure cached
            service.cache = (time.monotonic() - 31, result)
            service.options()
            self.assertEqual(len(runner.calls), 2)  # 30 s for failures


class WindowsTests(STTTestCase):
    def test_windows_never_starts_the_recorder(self):
        popen = FakePopen([], 0)
        with unittest.mock.patch.object(stt, "WINDOWS", True), \
                unittest.mock.patch.object(stt.subprocess, "run") as run, \
                unittest.mock.patch.object(stt.subprocess, "Popen") as spawn:
            service = STTService(self.config, self.dir / "MeetingCopilotCapture.exe", self.root)
            self.assertEqual(service.options(), {"ok": False, "error": stt.WINDOWS_REASON})
            self.assertEqual(service.status()["reason"], stt.WINDOWS_REASON)
            self.assertIn(stt.WINDOWS_REASON, service.check()["error"])
            self.assertIn(stt.WINDOWS_REASON, wait_for(lambda: [service.downloads_by_id[service.start_download("m")["id"]]])["message"])
            injected = self.service(popen=popen)
            injected.options(refresh=True)
            injected.check()
        run.assert_not_called()
        spawn.assert_not_called()
        self.assertEqual(self.runner.calls, [])
        self.assertIsNone(popen.args)


class SaveChoiceTests(STTTestCase):
    def save(self, **choice):
        return self.service().save_choice({"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto", **choice})

    def stored(self):
        return json.loads(self.config.read_text())["stt"]["choice"]

    def test_rejections(self):
        cases = [
            ({"engine": "nope"}, "engine"),
            ({"engine": "fixture-no-key", "model": "x"}, "unavailable"),
            ({"model": "not-listed"}, "does not list the model"),
            ({"model": "fixture-unknown-languages"}, "unavailable"),
            ({"language": ""}, "Choose a language"),
            ({"language": "fr"}, "does not list the language"),
            ({"model": "fixture-stream-model/latin/1120ms"}, "automatic language detection"),
            ({"model": "--evil"}, "may not start"),
            ({"engine": "assemblyai", "model": ""}, "Type a model id"),
        ]
        for change, text in cases:
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, text):
                    self.save(**change)
        for bad in (None, {}, {"engine": "fluidaudio"}, {**dict.fromkeys(stt.CHOICE_KEYS, ""), "extra": ""},
                    {**dict.fromkeys(stt.CHOICE_KEYS, ""), "language": None},
                    {**dict.fromkeys(stt.CHOICE_KEYS, ""), "speaker_model": ""}):  # removed key: not accepted
            with self.assertRaisesRegex(ValueError, "exactly"):
                self.service().save_choice(bad)
        self.assertFalse(self.config.exists())

    def test_auto_only_with_auto_detect(self):
        options = json.loads(FIXTURE)
        options["engines"][0]["models"][0]["auto_detect"] = False
        service = self.service(runner=FakeRunner(stdout=json.dumps(options)))
        choice = {"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto"}
        with self.assertRaisesRegex(ValueError, "automatic language detection"):
            service.save_choice(choice)
        service.save_choice({**choice, "language": "ru"})
        self.assertEqual(self.stored()["language"], "ru")

    def test_list_engine_and_free_text_engine(self):
        self.save(model="fixture-stream-model/latin/1120ms", language="es-ES")
        self.assertEqual(self.stored(), {"engine": "fluidaudio", "model": "fixture-stream-model/latin/1120ms", "language": "es-ES"})
        status = self.save(engine="assemblyai", model="  any-typed-id ", language="pt")  # free text, facts from model_template
        self.assertEqual(self.stored(), {"engine": "assemblyai", "model": "any-typed-id", "language": "pt"})
        self.assertEqual(status["choice"]["model"], "any-typed-id")
        self.save(engine="openai", model="fixture-openai-b", language="de")  # language_entry free_text on a listed model

    def test_preserves_other_keys_and_refuses_malformed(self):
        original = json.loads((WEB / "fixture_shared_config.json").read_text())
        self.config.write_text(json.dumps({**original, "stt": {"other": 1}}))
        self.save()
        data = json.loads(self.config.read_text())
        self.assertEqual(data["stt"]["other"], 1)
        self.assertEqual({key: data[key] for key in original}, original)
        if os.name != "nt":
            self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.config.write_text("{broken")
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            self.save()
        self.assertEqual(self.config.read_text(), "{broken")
        self.config.write_text("[]")
        with self.assertRaisesRegex(ValueError, "JSON object"):
            self.save()

    def test_status_uses_cached_choice_block_only_for_the_same_choice(self):
        service = self.service()
        self.assertEqual(service.status()["state"], "needs_choice")
        choice = {"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto"}
        service.save_choice(choice)
        self.assertEqual(service.status()["state"], "")  # the cached block describes no stored choice
        with service.adopting:  # the discovery that read started has finished
            pass
        options = json.loads(FIXTURE)
        options["choice"] = {"stored": choice, "state": "ready", "reason": ""}
        service.cache = (time.monotonic(), {**options, "ok": True})
        self.assertEqual(service.status()["state"], "ready")


    def test_needs_choice_runs_discovery_which_adopts_a_downloaded_model(self):
        choice = {"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto"}
        options = {**json.loads(FIXTURE), "choice": {"stored": choice, "state": "ready", "reason": ""}}
        runner = FakeRunner(stdout=json.dumps(options))
        config = self.config

        def adopting(args, **kwargs):  # what `stt-options` does when no choice is stored yet
            config.write_text(json.dumps({"stt": {"choice": choice}, "other": 1}))
            return runner(args, **kwargs)
        service = self.service(runner=adopting)
        self.assertEqual(service.status()["state"], "needs_choice")
        deadline = time.monotonic() + 2
        while service.status()["state"] != "ready" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(service.status()["state"], "ready")
        self.assertEqual(len(runner.calls), 1)  # one run, not one per status read

    def test_unavailable_choice_is_read_again_once_the_answer_is_30_seconds_old(self):
        choice = {"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto"}
        self.config.write_text(json.dumps({"stt": {"choice": choice}}))
        answer = lambda state: json.dumps({**json.loads(FIXTURE), "choice": {"stored": choice, "state": state, "reason": "not downloaded"}})
        runner = FakeRunner(stdout=answer("unavailable"))
        service = self.service(runner=runner)
        service.options()
        self.assertEqual(service.status()["state"], "unavailable")
        self.assertEqual(len(runner.calls), 1)  # a fresh answer is trusted
        runner.stdout = answer("ready")  # the model finished downloading
        service.cache = (service.cache[0] - 31, service.cache[1])
        deadline = time.monotonic() + 2
        while service.status()["state"] != "ready" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(service.status()["state"], "ready")


BANNER_PROBE = r"""
const fs = require("fs");
const elements = {};
const stub = () => new Proxy({children: [], dataset: {}, style: {}, classList: {add() {}, remove() {}, toggle() {}}}, {
  get(target, key) {
    if (key in target) return target[key];
    if (key === "replaceChildren") return (...nodes) => { target.children = nodes; };
    if (key === "append") return (...nodes) => { target.children.push(...nodes); };
    return () => {};
  },
  set(target, key, value) { target[key] = value; return true; },
});
const listeners = {};
let responses = {};
global.document = {getElementById: id => (elements[id] ||= stub()), createElement: stub, createDocumentFragment: stub,
  createTextNode: text => ({text}), documentElement: {lang: "en"}, querySelectorAll: () => []};
global.window = {addEventListener: (name, fn) => { listeners[name] = fn; }};
global.localStorage = {getItem: () => "1", setItem() {}};
global.MutationObserver = class { observe() {} };
global.plainError = error => String(error?.message ?? error ?? "");
global.apiError = data => new Error(data?.error || "");
global.setInterval = () => 0;
global.setTimeout = () => 0;
global.fetch = async path => ({ok: true, json: async () => responses[path.split("?")[0]] || {ok: true}});
const tick = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  responses = {"/api/getting-started": {ok: true, capture_installed: true, capture_running: true, ai: {state: "ready"}},
               "/api/stt": {ok: true, choice: {state: "needs_choice", reason: ""}}};
  eval(fs.readFileSync(process.argv[2], "utf8"));
  for (let i = 0; i < 5; i++) await tick();
  const banner = elements["blocker-banner"];
  const shown = {hidden: banner.hidden, rows: banner.children.map(row => row.children[0].textContent)};
  responses["/api/stt"] = {ok: true, choice: {state: "ready", reason: ""}};
  listeners.focus();
  for (let i = 0; i < 5; i++) await tick();
  console.log(JSON.stringify({shown, after: {hidden: banner.hidden, rows: banner.children.length}}));
})();
"""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class BlockerBannerTests(unittest.TestCase):
    def test_banner_shows_for_needs_choice_and_goes_when_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            probe = Path(folder) / "probe.js"
            probe.write_text(BANNER_PROBE, encoding="utf-8")
            run = subprocess.run(["node", str(probe), str(WEB / "getting-started.js")],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertFalse(result["shown"]["hidden"])
        self.assertIn("Speech recognition is not set up", result["shown"]["rows"][0])
        self.assertEqual(result["after"], {"hidden": True, "rows": 0})


class VocabularyParityTests(unittest.TestCase):
    def test_constants_match_shared_vocabulary(self):
        self.assertEqual(stt.OPTIONS_CONTRACT, VOCABULARY["options_contract"])
        self.assertEqual(stt.CHECK_CONTRACT, VOCABULARY["check_contract"])
        self.assertEqual(list(stt.CONFIG_PATH), VOCABULARY["config_path"])
        self.assertEqual(sorted(stt.CHOICE_KEYS), VOCABULARY["choice_keys"])
        self.assertEqual(sorted(stt.STATES), VOCABULARY["states"])
        self.assertEqual(sorted(stt.LIVE_MODES), VOCABULARY["live_modes"])
        self.assertEqual(sorted(stt.MODEL_ENTRY), VOCABULARY["model_entry"])
        self.assertEqual(stt.AUTO_LANGUAGE, VOCABULARY["auto_language"])
        self.assertEqual(stt.DEFERRED_KEY, VOCABULARY["deferred_key"])
        self.assertEqual(sorted(stt.DEFERRED_KINDS), VOCABULARY["deferred_kinds"])
        self.assertEqual(sorted(stt.DOWNLOAD_EVENTS), VOCABULARY["download_events"])

    def test_no_engine_ids_in_python_or_ui(self):
        # Engines are discovered, never named in code: the vocabulary lists them so this can be enforced.
        for name in ("stt.py", "speech.js"):
            source = (WEB / name).read_text(encoding="utf-8")
            for engine in VOCABULARY["engines"]:
                self.assertIsNone(re.search(rf"\b{engine}\b", source, re.IGNORECASE), f"{engine} in {name}")

    def test_schema_lists_the_choice_keys(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8")) if SCHEMA.exists() else {}
        section = schema.get("properties", {}).get("stt")
        if not section:
            self.skipTest("docs/config.schema.json has no stt section yet")
        choice = section["properties"]["choice"]
        if "$ref" in choice:
            choice = schema["$defs"][choice["$ref"].rsplit("/", 1)[-1]]
        self.assertEqual(sorted(choice["properties"]), VOCABULARY["choice_keys"])


class DownloadTests(STTTestCase):
    def test_event_folding(self):
        job = {"item": "model", "state": "running", "fraction": 0.0, "message": ""}
        apply_download_event(job, {"event": "progress", "item": "model", "id": "m", "fraction": 0.4, "phase": "downloading",
                                   "completed_files": 3, "total_files": 9})
        self.assertEqual((job["fraction"], job["phase"], job["completed_files"], job["total_files"]), (0.4, "downloading", 3, 9))
        apply_download_event(job, {"event": "done", "item": "model", "id": "m"})
        self.assertEqual(job["fraction"], 1.0)
        apply_download_event(job, {"event": "unknown"})
        apply_download_event(job, {"event": "error", "item": "model", "id": "m", "message": "disk full"})
        self.assertEqual((job["state"], job["message"]), ("error", "disk full"))

    def test_successful_and_failed_runs(self):
        popen = FakePopen([json.dumps({"event": "progress", "item": "model", "id": "m", "fraction": 0.5}),
                           "log line", json.dumps({"event": "finished", "ok": True})], 0)
        service = self.service(popen=popen)
        service.options()
        job = service.start_download("m")
        self.assertEqual(popen.args[1:], ["stt-download", "--model", "m", "--json"])
        finished = wait_for(service.downloads)
        self.assertEqual((finished["id"], finished["state"], finished["fraction"]), (job["id"], "done", 0.5))
        self.assertIsNone(service.cache)  # downloaded state changed

        service = self.service(popen=FakePopen([json.dumps({"event": "error", "item": "model", "id": "m", "message": "offline"})], 1))
        service.start_download("m")
        self.assertEqual((wait_for(service.downloads)["state"], service.downloads()[0]["message"]), ("error", "offline"))

        service = self.service(popen=FakePopen(["Fatal: crashed"], 3))
        service.start_download("m")
        self.assertEqual(wait_for(service.downloads)["message"], "Fatal: crashed")

        with self.assertRaises(ValueError):
            service.start_download("--model")


class CheckAndKeyTests(STTTestCase):
    def test_check_with_and_without_choice(self):
        choice = {"engine": "e", "model": "m", "language": "auto"}
        reply = {"contract": "meetontrack.stt-check/1", "choice": choice, "ok": True, "steps": [], "model_used": "m", "error": ""}
        runner = FakeRunner(stdout=json.dumps(reply))
        service = self.service(runner=runner)
        self.assertTrue(service.check(choice)["ok"])
        self.assertEqual(runner.calls[0][0][1:], ["stt-check", "--json", "--engine", "e", "--model", "m", "--language", "auto"])
        self.assertEqual(runner.calls[0][1]["timeout"], 180)
        self.config.write_text(json.dumps({"stt": {"choice": choice}}))
        self.assertEqual(service.last_check()["model_used"], "m")
        service.check()
        self.assertEqual(runner.calls[1][0][1:], ["stt-check", "--json"])
        failed = self.service(runner=FakeRunner(stdout="", returncode=1, stderr="no model")).check()
        self.assertEqual((failed["ok"], failed["error"]), (False, "no model"))

    def test_key_file_is_private_and_only_for_engines_that_need_one(self):
        service = self.service()
        service.save_key("assemblyai", " secret-key \n")
        path = self.dir / "keys" / "assemblyai"
        self.assertEqual(path.read_text(), "secret-key")
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        for engine, key in (("fluidaudio", "k"), ("../x", "k"), ("assemblyai", ""), ("assemblyai", "two words")):
            with self.assertRaises(ValueError):
                service.save_key(engine, key)


class SessionTests(STTTestCase):
    def session(self, name, meta, transcript=False):
        folder = self.root / name
        folder.mkdir()
        (folder / "meta.json").write_text(json.dumps(meta))
        if transcript:
            (folder / "transcript.json").write_text("{}")
        return folder

    def test_deferred_listing(self):
        mark = {"kind": "needs_choice", "reason": "choose", "at": "2026-10-21T10:00:00Z"}
        self.session("2026.10.20-0900", {"transcription_deferred": mark})
        self.session("2026.10.21-0900", {"transcription_deferred": {**mark, "kind": "network"}})
        self.session("2026.10.19-0900", {"transcription_deferred": mark}, transcript=True)
        self.session("2026.10.18-0900", {})
        (self.root / "broken").mkdir()
        (self.root / "broken" / "meta.json").write_text("{")
        listed = self.service().deferred()
        self.assertEqual([item["session"] for item in listed], ["2026.10.21-0900", "2026.10.20-0900"])
        self.assertEqual(listed[0]["kind"], "network")

    def test_retranscribe_rejects_traversal_and_builds_arguments(self):
        folder = self.session("2026.10.21-0900", {})
        (self.dir / "outside").mkdir()
        (self.dir / "outside" / "meta.json").write_text("{}")
        service = self.service(runner=FakeRunner(stdout="", returncode=1, stderr="line 1\nline 2"))
        for bad in ("../outside", "..", ".", "", "/etc", "a/b", None, "missing", "-x"):
            with self.assertRaises(ValueError):
                service.retranscribe(bad)
        with self.assertRaisesRegex(ValueError, "one-run"):
            service.retranscribe(folder.name, {"engine": "e"})
        service.retranscribe(folder.name, {"engine": "e", "model": "m", "language": "ru"})
        finished = wait_for(service.jobs)
        self.assertEqual((finished["state"], finished["exit_code"], finished["stderr"]), ("error", 1, "line 1\nline 2"))
        self.assertEqual(service.runner.calls[0][0][1:], ["process", str(folder), "--again", "--engine", "e", "--model", "m",
                                                          "--language", "ru"])
        runner = FakeRunner(stdout="")
        service = self.service(runner=runner)
        service.retranscribe(folder.name)
        self.assertEqual(wait_for(service.jobs)["state"], "done")
        self.assertEqual(runner.calls[0][0][1:], ["process", str(folder), "--again"])


class RouteTests(STTTestCase):
    def test_status_and_choice_routes(self):
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        from unittest.mock import patch
        import server
        with patch.object(server, "STT", self.service()):
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()

            def call(method, path, payload=None):
                connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=5)
                connection.request(method, path, None if payload is None else json.dumps(payload),
                                   {"Content-Type": "application/json"})
                response = connection.getresponse()
                result = response.status, json.loads(response.read())
                connection.close()
                return result
            try:
                status, body = call("GET", "/api/stt")
                self.assertEqual((status, body["ok"], body["choice"]["state"]), (200, True, "needs_choice"))
                self.assertEqual(set(body), {"ok", "choice", "downloads", "retranscribe", "check"})
                choice = {"engine": "fluidaudio", "model": "fixture-batch-model", "language": "auto"}
                status, body = call("POST", "/api/stt/choice", {"choice": choice})
                self.assertEqual((status, body["ok"], body["status"]["choice"]), (200, True, choice))
                status, body = call("POST", "/api/stt/choice", {"choice": {**choice, "language": "fr"}})
                self.assertEqual((status, body["ok"]), (400, False))
                status, body = call("GET", "/api/stt/options")
                self.assertTrue(body["ok"] and body["engines"])
            finally:
                httpd.shutdown()
                httpd.server_close()


if __name__ == "__main__":
    unittest.main()
