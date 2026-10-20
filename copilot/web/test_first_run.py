import subprocess
import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from ai_providers import AIService, Reply
from first_run import AIReadiness, ai_failure, pick_codex


METADATA = "Model metadata for `fixture-model` not found. Defaulting to fallback metadata; this can degrade performance and cause issues."
REJECTED = "unexpected status 400 Bad Request: {\"detail\":\"The 'fixture-model' model is not supported when using Codex with a ChatGPT account.\"}"


class AIFailureTests(unittest.TestCase):
    def test_old_codex_output_asks_for_update(self):
        self.assertTrue(ai_failure(METADATA + "\n" + REJECTED).startswith("AI_UPDATE:"))

    def test_rejection_without_metadata_line_is_model_error(self):
        self.assertTrue(ai_failure(REJECTED).startswith("AI_MODEL:"))

    def test_missing_binary_still_maps_to_missing(self):
        error = FileNotFoundError(2, "No such file or directory")
        error.filename = "/usr/local/bin/codex"
        self.assertTrue(ai_failure(str(error)).startswith("AI_MISSING:"))
        self.assertTrue(ai_failure("zsh: command not found: codex").startswith("AI_MISSING:"))

    def test_bare_not_found_is_not_missing(self):
        self.assertFalse(ai_failure("resource not found").startswith("AI_MISSING:"))


class PickCodexTests(unittest.TestCase):
    def test_picks_highest_version_and_skips_broken(self):
        with tempfile.TemporaryDirectory() as root:
            old, new, broken = (Path(root) / name for name in ("old", "new", "broken"))
            for path in (old, new, broken):
                path.write_text("")
            versions = {str(old): "codex-cli 0.153.2\n", str(new): "codex-cli 0.159.2\n"}

            def runner(cmd, **kwargs):
                if cmd[0] == str(broken):
                    raise subprocess.TimeoutExpired(cmd, 5)
                return subprocess.CompletedProcess(cmd, 0, versions[cmd[0]], "")

            self.assertEqual(pick_codex([None, Path(root) / "absent", broken, old, new], runner), new)
            self.assertEqual(pick_codex([broken], runner), broken)
            self.assertIsNone(pick_codex([Path(root) / "absent"], runner))


class CheckAITests(unittest.TestCase):
    def test_each_distinct_choice_is_tested_once_and_missing_ones_are_reported(self):
        from test_ai_providers import FakeAdapter
        with tempfile.TemporaryDirectory() as root:
            adapter = FakeAdapter()
            service = AIService(Path(root) / "config.json", {}, adapters=[adapter])
            same = {"provider": "fake", "model": "m2", "effort": "", "speed": ""}
            service.save("live_analysis", same)
            service.save("summary_rewrite", same)
            service.save("live_translation", {"provider": "fake", "model": "m1", "effort": "x", "speed": "quick"})
            result = AIReadiness(service).check()
        self.assertEqual(len(adapter.calls), 2)
        self.assertEqual(result["state"], "needs_choice")
        self.assertEqual(result["purposes"]["live_analysis"]["model"], "m2-reported")
        self.assertEqual(result["purposes"]["frame_relevance"]["state"], "needs_choice")


class LazyResolutionTests(unittest.TestCase):
    def test_importing_server_runs_no_subprocess(self):
        import sys
        for name in ("server", "live_translation", "first_run", "ai_providers"):
            sys.modules.pop(name, None)
        with patch("subprocess.run", side_effect=AssertionError("subprocess at import")), \
             patch("subprocess.Popen", side_effect=AssertionError("subprocess at import")):
            import server  # noqa: F401


if __name__ == "__main__":
    unittest.main()
