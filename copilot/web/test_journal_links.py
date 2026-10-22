import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from journal_links import collapse_links

FORM = "https://docs.google.com/forms/d/e/FAlg"


def item(category, text, index=0):
    return {"id": f"{category}-{index}", "category": category, "text": text, "meeting_id": "m",
            "source": "screen", "created_at": f"2026-10-22T10:00:{index:02d}+02:00"}


class CollapseLinksTests(unittest.TestCase):
    def test_same_url_as_service_and_link_is_one_card_with_the_label(self):
        for order in ((item("URL", FORM, 1), item("SERVICE", f"Google Docs — {FORM}", 2)),
                      (item("SERVICE", f"Google Docs — {FORM}/", 1), item("URL", "http://" + FORM[8:], 2))):
            with self.subTest(order=[i["category"] for i in order]):
                self.assertEqual([i["category"] for i in collapse_links(list(order))], ["SERVICE"])

    def test_ocr_variant_on_same_host_keeps_earliest(self):
        kept = collapse_links([item("SERVICE", f"Google Docs — {FORM}", 1),
                               item("SERVICE", "Google Docs — https://docs.google.com/torms/d/e/FAlg", 2),
                               item("URL", "docs.google.com/forms/d/e/FAIg", 3)])
        self.assertEqual([i["id"] for i in kept], ["SERVICE-1"])

    def test_call_links_never_show(self):
        calls = ["https://app.zoom.us/wc/123/join", "https://us02web.zoom.us/j/8812", "https://meet.google.com/abc-defg-hij",
                 "https://teams.microsoft.com/l/meetup-join/19%3a", "https://teams.live.com/meet/9341",
                 "https://telemost.yandex.ru/j/5512", "https://telemost.360.yandex.ru/j/5512",
                 "https://acme.webex.com/meet/bob", "https://meet.jit.si/standup", "https://whereby.com/acme",
                 "https://join.skype.com/abcDEF"]
        stored = [item("URL", url, n) for n, url in enumerate(calls)]
        stored.append(item("SERVICE", "Google Meet — https://meet.google.com/abc-defg-hij", 30))
        self.assertEqual(collapse_links(stored), [])
        for url in calls:
            with self.subTest(url=url):
                self.assertEqual(server.extract_urls(f"join {url}?pwd=x"), [])

    def test_distinct_links_and_other_items_are_kept(self):
        stored = [item("URL", "https://example.com/v1", 1), item("URL", "https://example.com/v2", 2),
                  item("URL", "https://example.org/v1", 3), item("URL", "https://example.com/pricing", 4),
                  item("SERVICE", "Miro", 5), item("PRODUCT", "Google Sheets", 6), item("RISK", "Срок", 7),
                  item("SERVICE", f"Google Docs — {FORM}", 8),
                  item("SERVICE", "Google Docs — https://docs.google.com/forms/d/e/1FAIpQLSxyz", 9)]
        self.assertEqual(collapse_links(stored), stored)


class JournalLinkCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "journal.json"
        self.journal = server.MeetingJournal(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_capture_adds_one_card_per_link_and_no_call_links(self):
        with patch.object(server, "JOURNAL", self.journal):
            server.capture_mentions(f"Анкета {FORM} звонок https://meet.google.com/abc-defg-hij "
                                    "https://teams.microsoft.com/l/meetup-join/1 telemost.yandex.ru/j/42",
                                    "m", "Встреча", "screen")
            server.capture_mentions("docs.google.com/torms/d/e/FAlg", "m", "Встреча", "screen")
            server.capture_mentions("https://acme-crm.io/pricing", "m", "Встреча", "screen")
        self.assertEqual([(i["category"], i["text"]) for i in reversed(self.journal.snapshot("m"))], [
            ("SERVICE", f"Google Docs — {FORM}"),
            ("SERVICE", "Acme Crm — https://acme-crm.io/pricing"),
        ])
        self.assertEqual(len(json.loads(self.path.read_text())["items"]), 2)

    def test_labelled_card_replaces_bare_link_from_copilot(self):
        self.journal.add_answer(f"URL — {FORM}", "m", "Встреча")
        with patch.object(server, "JOURNAL", self.journal):
            server.capture_mentions(FORM, "m", "Встреча", "screen")
        self.assertEqual([i["category"] for i in self.journal.snapshot("m")], ["SERVICE"])

    def test_stored_duplicates_and_call_links_are_hidden_without_rewriting(self):
        stored = [item("URL", FORM, 1), item("SERVICE", f"Google Docs — {FORM}", 2),
                  item("URL", "https://docs.google.com/torms/d/e/FAlg", 3),
                  item("URL", "https://app.zoom.us/wc/88/join", 4), item("NOTE", "моя заметка", 5)]
        self.path.write_text(json.dumps({"version": 1, "items": stored}), encoding="utf-8")
        before = self.path.read_text(encoding="utf-8")
        journal = server.MeetingJournal(self.path)
        self.assertEqual([i["id"] for i in journal.snapshot("m")], ["NOTE-5", "SERVICE-2"])
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
