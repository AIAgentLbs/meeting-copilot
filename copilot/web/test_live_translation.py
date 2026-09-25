import unittest
from unittest.mock import patch

from live_translation import LiveTranslation


class LiveTranslationTests(unittest.TestCase):
    def setUp(self):
        self.translator = LiveTranslation()

    def tearDown(self):
        self.translator.pool.shutdown(wait=True)

    def test_portuguese_gets_english_without_overwriting_original(self):
        key = ("meeting-1", "system", "2026-09-25T17:41:00Z")
        original = "Eles têm uma ferramenta para encontrar clientes no Brasil."
        with patch.object(LiveTranslation, "_language", return_value=("pt", 0.99)), \
             patch.object(LiveTranslation, "_translate", return_value="They have a tool to find clients in Brazil."):
            self.translator._work(key, original)
        result = self.translator.annotate({
            "meeting_id": "meeting-1", "segments": [
                {"source": "system", "timestamp": key[2], "text": original,
                 "provisional": False}
            ],
        })
        self.assertEqual(result["segments"][0]["text"], original)
        self.assertEqual(result["segments"][0]["language"], "pt")
        self.assertEqual(result["segments"][0]["translation_en"],
                         "They have a tool to find clients in Brazil.")

    def test_english_and_russian_are_not_sent_for_translation(self):
        for code in ("en", "ru"):
            with self.subTest(code=code), \
                 patch.object(LiveTranslation, "_language", return_value=(code, 0.99)), \
                 patch.object(LiveTranslation, "_translate") as translate:
                self.translator._work(("meeting-1", code, code), "A complete sentence.")
                translate.assert_not_called()

    def test_translation_is_bound_to_meeting_id(self):
        key = ("meeting-1", "system", "2026-09-25T17:41:00Z")
        with patch.object(LiveTranslation, "_language", return_value=("pt", 0.99)), \
             patch.object(LiveTranslation, "_translate", return_value="In English"):
            self.translator._work(key, "Esta é uma frase em português.")
        with patch.object(self.translator.pool, "submit"):
            result = self.translator.annotate({
                "meeting_id": "meeting-2", "segments": [
                    {"source": "system", "timestamp": key[2],
                     "text": "Esta é uma frase em português.", "provisional": False}
                ],
            })
        self.assertNotIn("translation_en", result["segments"][0])


if __name__ == "__main__":
    unittest.main()
