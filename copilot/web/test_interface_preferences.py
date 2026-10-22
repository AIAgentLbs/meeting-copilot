import json
import tempfile
import unittest
from pathlib import Path

from interface_preferences import interface_preferences, save_interface_language


class InterfacePreferencesTests(unittest.TestCase):
    def test_explicit_choice_only_and_no_other_config_is_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for language in ("en", "ru"):
                settings = {"interface_language": language, "transcription": {"language": "de"},
                            "private_setting": "synthetic-secret"}
                path.write_text(json.dumps(settings), encoding="utf-8")
                self.assertEqual(interface_preferences(path), {"interface_language": language})
                self.assertEqual(json.loads(path.read_text()), settings)

    def test_missing_automatic_unknown_or_invalid_config_keeps_legacy_behaviour(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(interface_preferences(path), {})
            for value in ('{}', '{"interface_language":"auto"}', '{"interface_language":"de"}',
                          '{"interface_language":null}', '[]', 'null', 'not json'):
                path.write_text(value, encoding="utf-8")
                self.assertEqual(interface_preferences(path), {})

    def test_settings_save_changes_only_the_language_and_is_read_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            others = {"ai": {"choice": {"provider": "x"}}, "interface_language": "ru", "keep_audio": True}
            path.write_text(json.dumps(others), encoding="utf-8")
            self.assertEqual(save_interface_language(path, "en"), {"interface_language": "en"})
            self.assertEqual(json.loads(path.read_text()), {**others, "interface_language": "en"})
            self.assertEqual(interface_preferences(path), {"interface_language": "en"})
            path.unlink()
            save_interface_language(path, "ru")  # a missing file becomes the first setting
            self.assertEqual(json.loads(path.read_text()), {"interface_language": "ru"})

    def test_settings_save_refuses_unknown_language_and_broken_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for language in ("auto", "de", None, 1):
                with self.assertRaises(ValueError):
                    save_interface_language(path, language)
            self.assertFalse(path.exists())
            for broken in ("not json", "[]"):
                path.write_text(broken, encoding="utf-8")
                with self.assertRaises(ValueError):
                    save_interface_language(path, "en")
                self.assertEqual(path.read_text(), broken)


if __name__ == "__main__":
    unittest.main()
