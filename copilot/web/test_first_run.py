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

    def test_windows_sandbox_refusal_says_why_and_what_to_do(self):
        # MEETONTRACK-86: Codex's own words, as Windows printed them without its elevated sandbox.
        refusal = ("failed to prepare windows sandbox wrapper: windows unelevated restricted-token sandbox cannot "
                   "enforce split filesystem read restrictions directly; refusing to run unsandboxed (code -32603)")
        message = ai_failure(refusal)
        self.assertTrue(message.startswith("AI_SANDBOX:"))
        self.assertIn("/setup-default-sandbox", message)

    def test_probe_image_is_larger_than_a_vision_patch(self):
        # MEETONTRACK-87: a 16 px probe was seen as salmon, pink or white; the probe is a solid 256 px fill.
        import struct
        from first_run import probe_png
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "probe.png"
            probe_png(path)
            self.assertEqual(struct.unpack(">II", path.read_bytes()[16:24]), (256, 256))

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
    def test_every_task_is_probed_against_the_one_choice(self):
        from test_ai_providers import FakeAdapter, M1
        with tempfile.TemporaryDirectory() as root:
            adapter = FakeAdapter()
            service = AIService(Path(root) / "config.json", {}, adapters=[adapter])
            readiness = AIReadiness(service)
            self.assertEqual(readiness.check()["state"], "needs_choice")
            self.assertEqual(adapter.calls, [])
            service.save(M1)
            self.assertEqual(readiness.snapshot()["purposes"]["live_analysis"]["state"], "unchecked")
            result = readiness.check()
            options = {call[1][:20]: call[2] for call in adapter.calls}
            self.assertEqual(len(adapter.calls), 3)  # one text, one image, one file probe shared by six tasks
            self.assertEqual({call[0]["model"] for call in adapter.calls}, {"m1"})
            self.assertIn("roots", next(o for p, o in options.items() if p.startswith("Read the file")))
            self.assertTrue(next(o for p, o in options.items() if p.startswith("Which colour")).get("image"))
            self.assertEqual(set(result["purposes"]), {"live_analysis", "live_translation", "frame_relevance",
                                                       "summary_rewrite", "summary", "speaker_names"})
            for purpose in ("summary_rewrite", "live_translation", "summary", "speaker_names"):
                self.assertEqual(result["purposes"][purpose]["state"], "ready", purpose)
            self.assertEqual(result["purposes"]["live_analysis"]["state"], "error")  # the fake cannot read files
            self.assertEqual(result["purposes"]["frame_relevance"]["state"], "error")  # nor tell the colour
            service.save({**M1, "speed": "standard"})
            self.assertEqual(readiness.snapshot()["purposes"]["summary_rewrite"]["state"], "unchecked")

    def test_file_probe_folder_is_outside_the_temp_folder(self):
        # Codex's profile denies the temp folders; with the probe file there gpt-6.1-sol replied
        # "I can't read that file because its location is restricted" in 4 of 5 checks on macOS.
        # The probe folder is a sibling of the AI working directory, like a real repository.
        import os
        from test_ai_providers import FakeAdapter, M1
        with tempfile.TemporaryDirectory() as root:
            adapter = FakeAdapter()
            service = AIService(Path(root) / "config.json", {}, adapters=[adapter])
            service.save(M1)
            with patch.dict(os.environ, {"MEETING_COPILOT_AI_WORKDIR": str(Path(root) / "ai-workdir")}):
                AIReadiness(service).check()
            probe = Path(next(call[2]["roots"][0] for call in adapter.calls if "roots" in call[2]))
            self.assertEqual(probe.parent, Path(root))
            self.assertFalse(probe.exists())

    def test_a_task_the_choice_cannot_do_is_listed_unavailable_and_others_still_pass(self):
        from test_ai_providers import FakeAdapter, M2
        with tempfile.TemporaryDirectory() as root:
            adapter = FakeAdapter()
            adapter.reads_files = False
            service = AIService(Path(root) / "config.json", {}, adapters=[adapter])
            service.save(M2)  # m2 does not accept images
            result = AIReadiness(service).check()
            self.assertEqual(len(adapter.calls), 1)  # text only: no image probe for a model without images
            self.assertEqual(result["purposes"]["frame_relevance"]["state"], "unavailable")
            self.assertIn("screenshots are not analysed", result["purposes"]["frame_relevance"]["message"])
            others = {p: v["state"] for p, v in result["purposes"].items() if p != "frame_relevance"}
            self.assertEqual(set(others.values()), {"ready"})
            self.assertIn("connected folders", result["purposes"]["live_analysis"]["message"])
            self.assertEqual(result["state"], "partial")


class LazyResolutionTests(unittest.TestCase):
    def test_importing_server_runs_no_subprocess(self):
        import sys
        names = ("server", "live_translation", "frame_relevance", "first_run", "ai_providers")
        saved = {name: sys.modules.pop(name) for name in names if name in sys.modules}
        try:
            with patch("subprocess.run", side_effect=AssertionError("subprocess at import")), \
                 patch("subprocess.Popen", side_effect=AssertionError("subprocess at import")):
                import server  # noqa: F401
        finally:  # other tests patch the modules they imported; give those back
            for name in names:
                sys.modules.pop(name, None)
            sys.modules.update(saved)


if __name__ == "__main__":
    unittest.main()
