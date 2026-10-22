import json
import tempfile
import unittest
from pathlib import Path

from interface_preferences import interface_preferences, save_preferences


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
                          '{"interface_language":null}', '{"transcript_hidden":1}', '{"transcript_hidden":"true"}',
                          '{"call_overview_statuses":"open"}', '{"call_overview_statuses":["open","open"]}',
                          '{"call_overview_statuses":["done"]}', '{"call_overview_statuses":[{}]}',
                          '[]', 'null', 'not json'):
                path.write_text(value, encoding="utf-8")
                self.assertEqual(interface_preferences(path), {})

    def test_settings_save_changes_only_given_keys_and_is_read_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            others = {"ai": {"choice": {"provider": "x"}}, "interface_language": "ru", "keep_audio": True}
            path.write_text(json.dumps(others), encoding="utf-8")
            self.assertEqual(save_preferences(path, {"interface_language": "en"}), {"interface_language": "en"})
            self.assertEqual(json.loads(path.read_text()), {**others, "interface_language": "en"})
            save_preferences(path, {"transcript_hidden": True})
            self.assertEqual(json.loads(path.read_text()),
                             {**others, "interface_language": "en", "transcript_hidden": True})
            self.assertEqual(interface_preferences(path), {"interface_language": "en", "transcript_hidden": True})
            save_preferences(path, {"call_overview_statuses": ["clarify"]})
            self.assertEqual(interface_preferences(path)["call_overview_statuses"], ["clarify"])
            save_preferences(path, {"call_overview_statuses": []})  # every status off is a valid choice
            self.assertEqual(json.loads(path.read_text()),
                             {**others, "interface_language": "en", "transcript_hidden": True, "call_overview_statuses": []})
            path.unlink()
            save_preferences(path, {"transcript_hidden": False})  # a missing file becomes the first setting
            self.assertEqual(json.loads(path.read_text()), {"transcript_hidden": False})

    def test_settings_save_refuses_unknown_values_and_broken_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            for change in ({}, [], None, {"interface_language": "auto"}, {"interface_language": 1},
                           {"transcript_hidden": 1}, {"transcript_hidden": "true"}, {"keep_audio": False},
                           {"call_overview_statuses": ["open", "maybe"]}, {"call_overview_statuses": "open"},
                           {"call_overview_statuses": [["open"]]},
                           {"interface_language": "en", "recordings_dir": "/elsewhere"}):
                with self.assertRaises(ValueError):
                    save_preferences(path, change)
            self.assertFalse(path.exists())
            for broken in ("not json", "[]"):
                path.write_text(broken, encoding="utf-8")
                with self.assertRaises(ValueError):
                    save_preferences(path, {"interface_language": "en"})
                self.assertEqual(path.read_text(), broken)


if __name__ == "__main__":
    unittest.main()
