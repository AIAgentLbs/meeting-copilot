import json
import tempfile
import unittest
from pathlib import Path

from interface_preferences import interface_preferences


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


if __name__ == "__main__":
    unittest.main()
