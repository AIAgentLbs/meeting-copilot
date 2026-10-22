"""Live fact checks: claim extraction, verdicts the app can stand behind, the web switch, storage.

No live network: pages are fetched through a stub, and the AI is a stub service. Every model id
below is a fixture.
"""
import json
import tempfile
import time
import urllib.request
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

    def test_a_quote_must_be_said_as_quoted(self):
        said = {"meeting_id": "m1", "segments": [{"source": "system", "text": "Acme profit is -10 percent, and unprofitable products."}]}
        for quote in ("Acme profit is +10 percent", "and profitable products", "Acme profit is -10 percent " + "x" * 300):
            with self.subTest(quote=quote[:30]):
                self.assertEqual(parse_claims(capture(quote=quote, claim=quote), said), [])
        self.assertEqual(len(parse_claims(capture(quote="Acme profit is -10 percent", claim="c"), said)), 1)
        dated = {"meeting_id": "m1", "segments": [{"source": "system", "text": "Acme was founded in 1998. Revenue is 1,5 million."}]}
        for quote in ("Acme was founded in 1998", "Revenue is 1,5 million"):  # sentence punctuation is not the number
            with self.subTest(quote=quote):
                self.assertEqual(len(parse_claims(capture(quote=quote, claim=quote), dated)), 1)

    def test_extraction_rules_list_known_claims(self):
        rules = fact_check.extraction_rules(["Claim A"])
        self.assertIn("CLAIM_CAPTURE", rules)
        self.assertIn('["Claim A"]', rules)  # earlier claims are quoted as data, one JSON line
        self.assertNotIn("—", rules)
        self.assertNotIn("ё", rules)


class SettleTests(unittest.TestCase):
    KB = [{"id": "kb1", "title": "notes.md", "location": "/docs/notes.md:3",
           "text": "Higgsfield trains its own video generation models."}]

    def test_green_needs_a_live_url_holding_the_quote(self):
        quote = "trains its own video models"
        answer = json.dumps({"verdict": "confirmed", "sources": [{"url": "https://dead.example/a", "quote": quote}]})
        self.assertEqual(settle(answer, [], pages({}), True), {"status": "unclear", "note": "no_source"})
        self.assertEqual(settle(answer, [], pages({"https://dead.example/a": "anything"}), True)["status"], "unclear")
        live = settle(answer, [], pages({"https://dead.example/a": f"Higgsfield {quote}."}), True)
        self.assertEqual((live["status"], live["sources"][0]["url"]), ("confirmed", "https://dead.example/a"))
        empty = json.dumps({"verdict": "confirmed", "sources": [{"url": "https://source.example/", "quote": ""}]})
        self.assertEqual(settle(empty, [], pages({"https://source.example/": ""}), True)["status"], "unclear")

    def test_a_long_quote_is_never_cut_and_a_fact_must_be_text(self):
        excerpt = [{"id": "kb1", "title": "n", "location": "l", "text": "alpha " * 50}]
        long = json.dumps({"verdict": "confirmed", "sources": [{"kb": "kb1", "quote": "alpha " * 50 + "fabricated"}]})
        self.assertEqual(settle(long, excerpt, pages({}), False)["status"], "unclear")
        for fact in ([""], True, {"a": 1}):
            answer = json.dumps({"verdict": "refuted", "fact": fact, "sources": [{"kb": "kb1", "quote": "alpha alpha alpha"}]})
            with self.subTest(fact=fact):
                self.assertEqual(settle(answer, excerpt, pages({}), False)["status"], "unclear")

    def test_a_quote_matches_only_as_written(self):
        for quote, page in (("The margin is +10 percent.", "The margin is -10 percent."),
                            ("company is profitable", "the company is unprofitable")):
            answer = json.dumps({"verdict": "refuted", "fact": "x", "sources": [{"url": "https://a.example/", "quote": quote}]})
            with self.subTest(quote=quote):
                self.assertEqual(settle(answer, [], pages({"https://a.example/": page}), True)["status"], "unclear")

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

    def test_web_unavailable_line_names_only_what_is_installed_here(self):
        service = StubAI("ollama", "").service
        self.assertEqual(service.web_search({"provider": "ollama"}), (False, []))  # nothing discovered yet
        self.assertEqual(service.web_search({"provider": "codex"})[0], True)
        found = {"codex": "available", "claude": "unavailable", "ollama": "available"}  # Claude Code not signed in
        with patch.object(time, "monotonic", return_value=1000.0):
            service.cache.update({name: (1000.0, "id", {"state": state}) for name, state in found.items()})
            self.assertEqual(service.web_search({}), (False, ["Codex"]))
        with patch.object(time, "monotonic", return_value=1000.0 + service.ttl + 1):
            self.assertEqual(service.web_search({}), (False, []))  # stale discovery is not evidence

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
            opposite = [{**CLAIM, "claim": f"Higgsfield {word} develops its own video generation models"}
                        for word in ("", "never")]
            self.assertEqual(store.add(TRANSCRIPT, opposite), 2)  # a contradiction is checked too
            founded = [{**CLAIM, "claim": f"Компания {name} основана в 1998 году"} for name in ("Google", "Tencent")]
            self.assertEqual(store.add(TRANSCRIPT, founded), 2)  # another name is another claim
            others = [{**CLAIM, "claim": claim} for claim in ("Google develops its own video generation models",
                                                               "Acme is the largest producer of smartphones worldwide",
                                                               "Acme is the smallest producer of smartphones worldwide")]
            self.assertEqual(store.add(TRANSCRIPT, others), 3)

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

    def test_a_failed_write_does_not_stop_the_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FactChecks(Path(directory) / "fact-checks.json", lambda row: {"status": "unclear", "note": "not_found"})
            store.add(TRANSCRIPT, [CLAIM, {**CLAIM, "claim": "Another claim entirely"}])
            with patch.object(store, "_persist_locked", side_effect=OSError("disk full")):
                self.assertTrue(store.check_one())
            self.assertTrue(store.check_one())
            self.assertEqual([row["status"] for row in FactChecks(store.path).snapshot("m1")], ["unclear", "unclear"])

    def test_an_unreadable_store_is_set_aside_and_the_same_path_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fact-checks.json"
            path.write_text("{broken")
            FactChecks(path).add(TRANSCRIPT, [CLAIM])
            self.assertEqual(FactChecks(path).claims("m1"), [CLAIM["claim"]])  # a restart reads what was written
            kept = [item.read_text() for item in Path(directory).glob("fact-checks-unreadable-*.json")]
        self.assertEqual(kept, ["{broken"])


class SafetyTests(unittest.TestCase):
    def test_only_public_web_addresses_are_fetched(self):
        for url in ("http://127.0.0.1/x", "http://localhost/x", "http://10.0.0.5/x", "http://169.254.169.254/latest",
                    "https://[::1]/x", "ftp://example.com/x", "https://user:pw@93.184.216.34/x", "https://93.184.216.34:8443/x"):
            with self.subTest(url=url):
                self.assertFalse(fact_check.public_url(url))
                self.assertIsNone(fact_check.fetch_text(url))
        self.assertTrue(fact_check.public_url("https://93.184.216.34/page"))  # a literal public address, no lookup

    def test_the_connection_uses_the_checked_address_so_dns_cannot_rebind(self):
        answers = iter([[(2, 1, 6, "", ("93.184.216.34", 80))], [(2, 1, 6, "", ("127.0.0.1", 80))]])
        with patch.object(fact_check.socket, "getaddrinfo", side_effect=lambda *a, **k: next(answers)), \
                patch.object(fact_check.socket, "create_connection") as connect:
            self.assertIsNone(fact_check.fetch_text("http://rebind.example/page"))
        connect.assert_not_called()

    def test_a_redirect_body_is_never_read(self):
        from types import SimpleNamespace
        from email.message import Message
        handler = fact_check._PublicRedirects()
        handler.parent = SimpleNamespace(open=lambda request, timeout=None: "followed")
        request = urllib.request.Request("https://93.184.216.34/a")
        request.timeout = 1
        headers = Message()
        headers["Location"] = "https://93.184.216.34/b"
        body = SimpleNamespace(closed=False, close=lambda: setattr(body, "closed", True),
                               read=lambda *a: b"" if body.closed else self.fail("redirect body read"))
        self.assertEqual(handler.http_error_302(request, body, 302, "Found", headers), "followed")

    def test_a_source_that_trickles_headers_is_cut_off_at_the_deadline(self):
        import socketserver
        import threading

        class Trickle(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    for byte in b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n" * 20:
                        self.request.sendall(bytes([byte]))
                        time.sleep(0.05)  # each byte well inside the socket timeout
                except OSError:
                    pass

        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Trickle)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with patch.object(fact_check, "PAGE_TIMEOUT", 0.3), patch.object(fact_check, "public_url", return_value=True), \
                patch.object(fact_check, "_public_ip", return_value=True):  # loopback stands in for a public host
            started = time.monotonic()
            self.assertIsNone(fact_check.fetch_text(f"http://127.0.0.1:{server.server_address[1]}/slow"))
            self.assertLess(time.monotonic() - started, 1.5, "one deadline (0.6 s here) covers headers too")

    def test_an_https_source_that_trickles_is_cut_off_at_the_deadline(self):
        import shutil
        import socketserver
        import ssl
        import subprocess
        import threading
        if not shutil.which("openssl"):
            self.skipTest("openssl is needed to make a throwaway certificate")
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        cert, key = Path(directory.name) / "cert.pem", Path(directory.name) / "key.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1",
                        "-days", "1", "-keyout", str(key), "-out", str(cert)], check=True, capture_output=True)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)

        class Trickle(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    with context.wrap_socket(self.request, server_side=True) as tls:
                        # Headers too: only shutting the connection down can end a blocked TLS header read.
                        for byte in b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n" * 10 + b"\r\n" + b"x" * 400:
                            tls.sendall(bytes([byte]))
                            time.sleep(0.05)  # each byte well inside the socket timeout
                except OSError:
                    pass

        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Trickle)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with patch.object(fact_check, "PAGE_TIMEOUT", 0.3), patch.object(fact_check, "public_url", return_value=True), \
                patch.object(fact_check, "_public_ip", return_value=True), \
                patch.object(ssl, "_create_default_https_context", ssl._create_unverified_context):  # throwaway cert
            started = time.monotonic()
            self.assertIsNone(fact_check.fetch_text(f"https://127.0.0.1:{server.server_address[1]}/slow"))
            self.assertLess(time.monotonic() - started, 1.5, "the deadline also ends a TLS read")

    def test_page_text_is_linear_on_hostile_markup(self):
        self.assertEqual(" ".join(fact_check.page_text("<p>a<script>x</script>b &amp; c</p>").split()), "a b & c")
        for markup in ("<" * 1_000_000, "<script" * 140_000, "<a " * 300_000):
            started = time.monotonic()
            fact_check.page_text(markup)
            with self.subTest(markup=markup[:8]):
                self.assertLess(time.monotonic() - started, 3)


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
        state = self.server.fact_check_state(TRANSCRIPT)
        self.assertEqual((state["web"], state["provider"], state["web_providers"]), (False, "Ollama", []))
        self.assertEqual(state["items"][0]["status"], "checking")

        corrected = dict(TRANSCRIPT, segments=[dict(TRANSCRIPT["segments"][0], speaker="Boris", speaker_label="Boris",
                                                    speaker_identity="manual", speaker_id="named-boris")])
        speaker = self.server.fact_check_state(corrected)["items"][0]["segment"]
        self.assertEqual((speaker["speaker_label"], speaker["speaker_identity"]), ("Boris", "manual"),
                         "a speaker corrected after the check shows on the row")
        self.assertEqual(self.store.snapshot("m1")[0]["segment"]["speaker"], "Mikhail", "the stored row is untouched")

    def test_citations_keep_their_query_and_drop_the_fragment(self):
        with patch.object(self.server, "fetch_text", side_effect=lambda url: f"page {url}") as fetch:
            url, text = self.server.fact_source("https://publisher.example/article.php?id=123#comments")
        self.assertEqual((url, fetch.call_args.args[0]), ("https://publisher.example/article.php?id=123",) * 2)
        self.assertEqual(self.server.fact_source("http://localhost/x?id=1"), ("", None))

    def test_google_results_are_dropped_when_access_changes_mid_search(self):
        google = self.server.GOOGLE_CONTEXT
        def revoke(source, query):
            google._generation += 1  # the user disconnects Google while this source is searched
            return {"items": [{"title": "Mail", "url": "https://mail.example/1", "excerpt": "secret"}]}
        with patch.object(google, "enabled_sources", return_value=["gmail"]), \
                patch.object(google, "_search_source", side_effect=revoke), \
                patch.object(google, "_generation", 0), \
                patch.object(self.server.LOCAL_CONTEXT, "search", return_value={"items": [
                    {"path": "/ctx/notes.md", "line": 3, "text": "Higgsfield notes"}]}):
            found = self.server.fact_knowledge(CLAIM)
        self.assertEqual([item["text"] for item in found], ["Higgsfield notes"])

    def test_google_is_not_searched_for_another_account(self):
        google = self.server.GOOGLE_CONTEXT
        with patch.object(google, "enabled_sources", return_value=["gmail"]), \
                patch.object(google, "status", return_value={"auth": "connected", "account": "b@example.com"}), \
                patch.object(google, "_preferences", return_value={"account": "a@example.com"}), \
                patch.object(google, "_search_source") as search, \
                patch.object(self.server.LOCAL_CONTEXT, "search", return_value={"items": []}):
            self.assertEqual(self.server.fact_knowledge(CLAIM), [])
        search.assert_not_called()

    def test_folder_excerpts_are_dropped_when_a_folder_is_disconnected_mid_search(self):
        folders = iter(["before", "after"])
        with patch.object(self.server.GOOGLE_CONTEXT, "enabled_sources", return_value=[]), \
                patch.object(self.server.LOCAL_CONTEXT, "generation", side_effect=lambda: next(folders)), \
                patch.object(self.server.LOCAL_CONTEXT, "search", return_value={"items": [
                    {"path": "/ctx/notes.md", "line": 3, "text": "Higgsfield notes"}]}):
            self.assertEqual(self.server.fact_knowledge(CLAIM), [])

    def test_claim_lines_never_reach_the_chat(self):
        from test_ai_providers import chosen_codex
        claim = capture(quote=HIGGSFIELD, claim=CLAIM["claim"], query="Higgsfield")
        answers = ["FACT — Обсуждаем видео\n" + claim, claim]  # the second answer carries only a claim
        with tempfile.TemporaryDirectory() as tmp, chosen_codex(tmp, self.server):
            session = self.server.CodexSession(Path(tmp) / "s.json")
            with patch.object(session, "_run_ai", side_effect=answers), \
                    patch.object(self.server.GOOGLE_CONTEXT, "augment", return_value=""), \
                    patch.object(self.server.LOCAL_CONTEXT, "augment", return_value=""):
                raw = [session.ask("q", "", "m", "m1", {}, kind="insight", show_user=False) for _ in answers]
        self.assertEqual(raw, answers, "the analysis still parses the raw answer")
        self.assertEqual([message["text"] for message in session.messages], ["FACT — Обсуждаем видео"])


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
        manual = [{**rows[0], "segment": {"source": "microphone", "speaker_identity": "manual", "speaker_label": "Boris"}}]
        self.assertIn("Boris", archive._report_html({**detail, "fact_checks": manual}, []))


if __name__ == "__main__":
    unittest.main()
