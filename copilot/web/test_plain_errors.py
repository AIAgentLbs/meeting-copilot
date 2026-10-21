"""No raw error text reaches the page: every failure is retried or turned into plain words."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent
PAGES = ("app.js", "getting-started.js", "speech.js")
# Each of these put an exception's own text (or an HTTP status) on screen before plainError existed.
RAW = (r"String\(error\b", r"\berror\.message\b", r"HTTP \$\{", r"\berror\.name\b")

PROBE = r"""
const fs = require("fs");
const source = fs.readFileSync(process.argv[2], "utf8");
const helpers = source.slice(source.indexOf("function apiError"), source.indexOf("// GETs retry quietly"));
let uiLanguage = process.argv[3];
const translations = {ru: {"error.AI_LIMIT": "Лимит аккаунта ИИ исчерпан."}, en: {}};
const t = key => key;
eval(helpers);
const timeout = Object.assign(new Error("signal timed out"), {name: "TimeoutError"});
console.log(JSON.stringify({
  network: plainError(new TypeError("Failed to fetch")),
  timeout: plainError(timeout),
  server: plainError(apiError({error: "database is locked"}, {status: 500})),
  traceback: plainError("Traceback (most recent call last): KeyError: 'x'"),
  className: plainError(new Error("FileNotFoundError: [Errno 2] No such file")),
  status: plainError(new Error("HTTP 502")),
  empty: plainError(apiError({}, {status: 400})),
  human: plainError(apiError({error: "Введите вопрос"}, {status: 400})),
  ai: plainError(apiError({error: "AI_LIMIT: The AI account limit is reached. Check your plan."}, {status: 500})),
}));
"""


class RawErrorTextTests(unittest.TestCase):
    def test_pages_never_render_raw_error_text(self):
        for name in PAGES:
            source = (WEB / name).read_text(encoding="utf-8")
            if name == "app.js":  # plainError itself is the one place allowed to read the raw text
                source = source[:source.index("function apiError")] + source[source.index("// GETs retry quietly"):]
            for line in source.splitlines():
                for pattern in RAW:
                    self.assertIsNone(re.search(pattern, line), f"{name} renders raw error text: {line.strip()}")


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PlainErrorTests(unittest.TestCase):
    def run_probe(self, language):
        with tempfile.TemporaryDirectory() as folder:
            probe = Path(folder) / "probe.js"
            probe.write_text(PROBE, encoding="utf-8")
            run = subprocess.run(["node", str(probe), str(WEB / "app.js"), language],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_failures_become_plain_instructions(self):
        result = self.run_probe("en")
        self.assertEqual(result["network"], "error.unreachable")
        self.assertEqual(result["timeout"], "error.unreachable")
        for key in ("server", "traceback", "className", "status", "empty"):
            self.assertEqual(result[key], "error.generic", key)
        self.assertEqual(result["human"], "Введите вопрос")
        self.assertEqual(result["ai"], "The AI account limit is reached. Check your plan.")

    def test_ai_codes_are_translated(self):
        self.assertEqual(self.run_probe("ru")["ai"], "Лимит аккаунта ИИ исчерпан.")


if __name__ == "__main__":
    unittest.main()
