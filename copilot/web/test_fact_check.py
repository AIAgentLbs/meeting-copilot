"""Live fact checks: claim extraction, verdicts the app can stand behind, the web switch, storage.

No live network: pages are fetched through a stub, and the AI is a stub service. Every model id
below is a fixture.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_providers
import fact_check
from ai_providers import AIChoiceError, AIService, ClaudeAdapter, CodexAdapter, OllamaAdapter, Result, Reply
from archive import MeetingArchive
from fact_check import FactChecks, parse_claims, settle, strip_claims, verify

HIGGSFIELD = "у Higgsfield есть свои модели генерации"
TRANSCRIPT = {"meeting_id": "m1", "meeting": "Demo call", "segments": [
    {"source": "microphone", "speaker": "Mikhail", "timestamp": "2026-10-22T10:01:00+02:00",
     "text": f"Смотрите, {HIGGSFIELD}, и это важно."},
    {"source": "system", "speaker": "Anna", "voice_id": "remote-1", "timestamp": "2026-10-22T10:02:00+02:00",
     "text": "Компания основана в 2023 году"},
    {"source": "system", "timestamp": "2026-10-22T10:03:00+02:00", "provisional": True,
     "text": "У них сто миллионов пользователей"},
]}
CLAIM = {"claim": "У Higgsfield есть собственные модели генерации видео", "quote": HIGGSFIELD,
         "query": "Higgsfield модели", "segment": {"source": "microphone", "speaker": "Mikhail"},
         "timestamp": "2026-10-22T10:01:00+02:00"}


def capture(**values):
    return "CLAIM_CAPTURE: " + json.dumps(values, ensure_ascii=False)


def pages(alive):
    """fetch stub: url -> (url, text or None); only `alive` pages answer."""
    return lambda url: (url, alive.get(url))


class ExtractionTests(unittest.TestCase):
    def test_claims_need_a_quote_from_one_final_segment(self):
        answer = "\n".join([
            "FACT — Обсуждаем видео",
            capture(quote=HIGGSFIELD, claim=CLAIM["claim"], query="Higgsfield модели"),
            capture(quote="Компания основана в 2023 году", claim="Higgsfield основана в 2023 году"),
            capture(quote="У Higgsfield миллиард пользователей", claim="invented"),  # never said
            capture(quote="У них сто миллионов пользователей", claim="provisional"),  # not final yet
            "CLAIM_CAPTURE: {not json}",
        ])
        claims = parse_claims(answer, TRANSCRIPT)
        self.assertEqual([claim["claim"] for claim in claims], [CLAIM["claim"], "Higgsfield основана в 2023 году"])
        self.assertEqual(claims[0]["segment"], {"source": "microphone", "speaker": "Mikhail"})
        self.assertEqual(claims[0]["timestamp"], "2026-10-22T10:01:00+02:00")
        self.assertEqual(claims[1]["segment"]["voice_id"], "remote-1")
        self.assertEqual(strip_claims(answer).count("CLAIM_CAPTURE"), 0)  # malformed lines are dropped too
        self.assertNotIn(HIGGSFIELD, strip_claims(answer))

    def test_extraction_rules_list_known_claims(self):
        rules = fact_check.extraction_rules(["Claim A"])
        self.assertIn("CLAIM_CAPTURE", rules)
        self.assertIn("- Claim A", rules)
        self.assertNotIn("—", rules)
        self.assertNotIn("ё", rules)


class SettleTests(unittest.TestCase):
    KB = [{"id": "kb1", "title": "notes.md", "location": "/docs/notes.md:3",
           "text": "Higgsfield trains its own video generation models."}]

    def test_green_needs_a_live_url(self):
        answer = json.dumps({"verdict": "confirmed", "sources": [{"url": "https://dead.example/a", "quote": "own models"}]})
        self.assertEqual(settle(answer, [], pages({}), True), {"status": "unclear", "note": "no_source"})
        live = settle(answer, [], pages({"https://dead.example/a": "anything"}), True)
        self.assertEqual(live["status"], "confirmed")
        self.assertEqual(live["sources"][0]["url"], "https://dead.example/a")

    def test_missing_sources_or_bad_json_is_yellow(self):
        for answer in (json.dumps({"verdict": "confirmed"}), json.dumps({"verdict": "refuted", "fact": "x", "sources": []}),
                       "I think it is true", json.dumps({"verdict": "maybe"})):
            with self.subTest(answer=answer):
                self.assertEqual(settle(answer, self.KB, pages({}), True)["status"], "unclear")

    def test_red_needs_the_quote_on_the_live_page_and_the_fact(self):
        quote = "Higgsfield builds on third-party models"
        answer = json.dumps({"verdict": "refuted", "fact": "Higgsfield uses third-party models.",
                             "sources": [{"url": "https://news.example/a", "quote": quote}]})
        self.assertEqual(settle(answer, [], pages({"https://news.example/a": "unrelated page"}), True)["status"], "unclear")
        red = settle(answer, [], pages({"https://news.example/a": f"<p>{quote}.</p>"}), True)
        self.assertEqual((red["status"], red["fact"]), ("refuted", "Higgsfield uses third-party models."))
        no_fact = json.dumps({"verdict": "refuted", "sources": [{"url": "https://news.example/a", "quote": quote}]})
        self.assertEqual(settle(no_fact, [], pages({"https://news.example/a": quote}), True)["status"], "unclear")

    def test_knowledge_base_source_needs_its_quote_in_the_excerpt(self):
        good = json.dumps({"verdict": "confirmed", "sources": [{"kb": "kb1", "quote": "trains its own video generation models"}]})
        bad = json.dumps({"verdict": "confirmed", "sources": [{"kb": "kb1", "quote": "has one billion users worldwide"}]})
        unknown = json.dumps({"verdict": "confirmed", "sources": [{"kb": "kb9", "quote": "trains its own video generation models"}]})
        result = settle(good, self.KB, pages({}), False)
        self.assertEqual((result["status"], result["sources"][0]["location"]), ("confirmed", "/docs/notes.md:3"))
        self.assertEqual(settle(bad, self.KB, pages({}), False)["status"], "unclear")
        self.assertEqual(settle(unknown, self.KB, pages({}), False)["status"], "unclear")

    def test_without_web_a_cited_url_is_never_fetched(self):
        answer = json.dumps({"verdict": "confirmed", "sources": [{"url": "https://site.example", "quote": "own models"}]})
        fetched = []
        self.assertEqual(settle(answer, [], lambda url: fetched.append(url) or (url, "page"), False)["status"], "unclear")
        self.assertEqual(fetched, [])


class StubAI:
    """resolve/web_search/run like AIService; records what each check asked for."""
    def __init__(self, provider, answer):
        self.provider, self.answer, self.calls = provider, answer, []
        self.service = AIService(Path("/nonexistent/config.json"), {},
                                 adapters=[CodexAdapter(lambda: None), ClaudeAdapter(lambda: None), OllamaAdapter("127.0.0.1:1")])

    def resolve(self, purpose):
        return ai_providers.Ticket(purpose, "ready", "", {"provider": self.provider, "model": "fixture-m",
                                                          "effort": "", "speed": ""}, "k", "/fake")

    def web_search(self, choice):
        return self.service.web_search(choice)

    def run(self, purpose, prompt, ticket=None, **options):
        self.calls.append((purpose, prompt, options))
        return Reply(self.answer, "fixture-m", "")


class VerifyTests(unittest.TestCase):
    def test_provider_without_web_checks_the_knowledge_base_only(self):
        ai = StubAI("ollama", json.dumps({"verdict": "confirmed", "sources": [
            {"kb": "kb1", "quote": "trains its own video generation models"}]}))
        result = verify(dict(CLAIM), ai=ai, knowledge=lambda row: SettleTests.KB, fetch=pages({}))
        purpose, prompt, options = ai.calls[0]
        self.assertEqual((purpose, options["web"]), ("fact_check", False))
        self.assertIn("Do not use the internet", prompt)
        self.assertEqual((result["status"], result["web"], result["model"]), ("confirmed", False, "fixture-m"))

    def test_web_unavailable_line_names_what_can(self):
        service = StubAI("ollama", "").service
        self.assertEqual(service.web_search({"provider": "ollama"}), (False, ["Codex", "Claude Code"]))
        self.assertEqual(service.web_search({"provider": "codex"})[0], True)
        self.assertEqual(service.web_search({}), (False, ["Codex", "Claude Code"]))

    def test_codex_and_claude_search_the_web_only_when_asked(self):
        choice = {"provider": "codex", "model": "fixture-a", "effort": "", "speed": ""}
        event = '{"type":"item.completed","item":{"type":"agent_message","text":"OK"}}'
        for web, mode in ((True, 'web_search="live"'), (False, 'web_search="disabled"')):
            with patch.object(ai_providers, "_run", return_value=Result(0, event, "")) as run:
                CodexAdapter(lambda: "/fake/codex").call(choice, "p", executable="/fake/pkg/bin/codex", env={},
                                                          timeout=5, web=web)
            self.assertIn(mode, run.call_args.args[0])
        stream = json.dumps({"type": "result", "is_error": False, "result": "OK"})
        with patch.object(ai_providers, "_run", return_value=Result(0, stream, "")) as run:
            ClaudeAdapter(lambda: "/fake/claude").call({**choice, "provider": "claude"}, "p", executable="/fake/claude",
                                                        env={}, timeout=5, web=True)
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("--tools") + 1], "WebSearch,WebFetch")
        with self.assertRaises(AIChoiceError):
            OllamaAdapter("127.0.0.1:1").call({**choice, "provider": "ollama"}, "p", timeout=5, web=True)

    def test_higgsfield_claim_end_to_end_offline(self):
        """The owner's example: extracted from the analysis, checked with a stubbed AI and page."""
        source = "https://higgsfield.example/about"
        quote = "Higgsfield develops its own video generation models"
        ai = StubAI("codex", json.dumps({"verdict": "confirmed", "sources": [{"url": source, "quote": quote}]}))
        with tempfile.TemporaryDirectory() as directory:
            store = FactChecks(Path(directory) / "fact-checks.json",
                               lambda row: verify(row, ai=ai, knowledge=lambda row: [], fetch=pages({source: quote})))
            answer = capture(quote=HIGGSFIELD, claim=CLAIM["claim"], query="Higgsfield модели")
            self.assertEqual(store.add(TRANSCRIPT, parse_claims(answer, TRANSCRIPT)), 1)
            self.assertTrue(store.check_one())
            row = store.snapshot("m1")[0]
        self.assertEqual((row["status"], row["sources"][0]["url"], row["web"]), ("confirmed", source, True))
        self.assertEqual(row["segment"]["source"], "microphone")
        self.assertTrue(ai.calls[0][2]["web"])


class StoreTests(unittest.TestCase):
    def test_near_identical_claims_are_kept_once_per_meeting(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FactChecks(Path(directory) / "fact-checks.json")
            self.assertEqual(store.add(TRANSCRIPT, [CLAIM]), 1)
            again = {**CLAIM, "claim": "У Higgsfield есть собственные модели генерации видео!"}
            self.assertEqual(store.add(TRANSCRIPT, [again]), 0)
            self.assertEqual(store.add({**TRANSCRIPT, "meeting_id": "m2"}, [CLAIM]), 1)
            self.assertEqual(store.claims("m1"), [CLAIM["claim"]])
            years = [{**CLAIM, "claim": f"Компания Higgsfield основана в {year} году"} for year in (2023, 2021)]
            self.assertEqual(store.add(TRANSCRIPT, years), 2)  # another number is another claim

    def test_checks_are_capped_per_minute_and_wait_for_the_analysis(self):
        now, idle = [0.0], [True]
        with tempfile.TemporaryDirectory() as directory:
            store = FactChecks(Path(directory) / "fact-checks.json", clock=lambda: now[0], idle=lambda: idle[0])
            store.add(TRANSCRIPT, [{**CLAIM, "claim": f"Claim number {index} about something"} for index in "abc"])
            self.assertIsNotNone(store.next_row())
            self.assertIsNotNone(store.next_row())
            self.assertIsNone(store.next_row())  # PER_MINUTE used up
            now[0] = 61.0
            idle[0] = False
            self.assertIsNone(store.next_row())  # the live analysis is running
            idle[0] = True
            self.assertIsNotNone(store.next_row())

    def test_failures_become_yellow_and_unfinished_checks_resume_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fact-checks.json"
            FactChecks(path).add(TRANSCRIPT, [CLAIM])
            restarted = FactChecks(path, lambda row: (_ for _ in ()).throw(RuntimeError("AI_NETWORK: offline")))
            self.assertTrue(restarted.check_one())
            row = FactChecks(path).snapshot("m1")[0]
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual((row["status"], row["error"]), ("unclear", "AI_NETWORK: offline"))


class SafetyTests(unittest.TestCase):
    def test_only_public_web_addresses_are_fetched(self):
        for url in ("http://127.0.0.1/x", "http://localhost/x", "http://10.0.0.5/x", "http://169.254.169.254/latest",
                    "https://[::1]/x", "ftp://example.com/x", "https://user:pw@93.184.216.34/x", "https://93.184.216.34:8443/x"):
            with self.subTest(url=url):
                self.assertFalse(fact_check.public_url(url))
                self.assertIsNone(fact_check.fetch_text(url))
        self.assertTrue(fact_check.public_url("https://93.184.216.34/page"))  # a literal public address, no lookup


class ServerTests(unittest.TestCase):
    """The analysis pass feeds the store and the journal never sees CLAIM_CAPTURE lines."""
    def setUp(self):
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        from types import SimpleNamespace
        import server
        self.server, self.http = server, http.client
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.asked = []
        answer = "FACT — Обсуждаем видео\n" + capture(quote=HIGGSFIELD, claim=CLAIM["claim"], query="Higgsfield")
        copilot = SimpleNamespace(busy=False, bind_meeting=lambda meeting_id: None, should_analyze=lambda context, force: True,
                                  record_analysis=lambda **values: None,
                                  ask=lambda question, *rest, **options: self.asked.append(question) or answer)
        self.store = FactChecks(root / "fact-checks.json")
        self.journal = server.MeetingJournal(root / "journal.json")
        config = root / "config.json"
        config.write_text(json.dumps({"ai": {"choice": {"provider": "ollama", "model": "fixture-m", "effort": "", "speed": ""}}}))
        stubs = {
            "TRANSCRIPT": SimpleNamespace(snapshot=lambda: dict(TRANSCRIPT, segments=list(TRANSCRIPT["segments"]))),
            "ARCHIVE": MeetingArchive(root / "recordings", root / "archive", root / "reports", root),
            "FRAMES": SimpleNamespace(annotate=lambda snapshot: snapshot, visual_context=lambda meeting_id: ""),
            "MEETING_CHAT": SimpleNamespace(snapshot=lambda meeting_id: []),
            "PLANS": SimpleNamespace(snapshot=lambda snapshot: None, apply_analysis=lambda snapshot, answer: 0),
            "REPOSITORIES": SimpleNamespace(resolve=lambda *args, **kwargs: {"kind": "all", "repositories": []}),
            "COPILOT": copilot, "JOURNAL": self.journal, "FACT_CHECKS": self.store,
            "AI": AIService(config, {}, adapters=[CodexAdapter(lambda: None), ClaudeAdapter(lambda: None),
                                                  OllamaAdapter("127.0.0.1:1")]),
        }
        for name, value in stubs.items():
            patcher = patch.object(server, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def test_analysis_captures_claims_without_leaking_them(self):
        conn = self.http.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=5)
        conn.request("POST", "/api/analyze", json.dumps({"force": True}), {"Content-Type": "application/json"})
        result = json.loads(conn.getresponse().read())
        conn.close()
        self.assertTrue(result["ok"], result)
        self.assertIn("CLAIM_CAPTURE", self.asked[0])
        self.assertNotIn("CLAIM_CAPTURE", result["answer"])
        self.assertEqual([item["claim"] for item in self.store.snapshot("m1")], [CLAIM["claim"]])
        self.assertFalse(any("CLAIM_CAPTURE" in item["text"] for item in self.journal.snapshot("m1")))
        state = self.server.fact_check_state("m1")
        self.assertEqual((state["web"], state["provider"], state["web_providers"]), (False, "Ollama", ["Codex", "Claude Code"]))
        self.assertEqual(state["items"][0]["status"], "checking")


class ArchiveTests(unittest.TestCase):
    def test_report_shows_settled_checks_and_old_signatures_do_not_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = MeetingArchive(root / "recordings", root / "archive", root / "reports", root / "config")
            detail = {"meeting_id": "m1", "title": "Demo", "started_at": "2026-10-22T10:00:00Z", "duration_seconds": 60,
                      "transcript": [], "journal": [], "meeting_chat": []}
            before = archive.source_signature(detail)
            self.assertEqual(archive.source_signature({**detail, "fact_checks": []}), before)
            rows = [{**CLAIM, "id": "a", "status": "refuted", "fact": "Higgsfield uses partner models.",
                     "sources": [{"kind": "web", "url": "https://news.example/a", "quote": "q"}]},
                    {**CLAIM, "id": "b", "claim": "Pending claim", "status": "checking"}]
            self.assertNotEqual(archive.source_signature({**detail, "fact_checks": rows}), before)
            page = archive._report_html({**detail, "fact_checks": rows}, [])
        self.assertIn("Проверка фактов", page)
        self.assertIn("На самом деле: Higgsfield uses partner models.", page)
        self.assertIn('href="https://news.example/a"', page)
        self.assertIn("Вы", page)
        self.assertNotIn("Pending claim", page)


if __name__ == "__main__":
    unittest.main()
