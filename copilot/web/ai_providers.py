"""AI provider layer: discovery, the one AI choice and calls. Holds no model ids.

Adapters read the options (models, efforts, speed tiers, input types, plan) from the exact
binary or service that will run, and turn the stored choice into a call. The person chooses
once (`ai.choice` in the shared ~/.config/meeting-copilot/config.json, schema:
docs/config.schema.json) and every task (PURPOSES) runs on it; a task the choice cannot do
reports unavailable on its own. This module writes only the `ai` subtree. Nothing here runs
at import time.

File boundary: a call reads only the `roots` it is given (the selected repositories), an
empty working directory and, for screenshots, the one image. Codex enforces it with a
permissions profile, Claude Code with --restricted plus --add-dir, Ollama gets no files.
"""
from __future__ import annotations

from collections import OrderedDict, namedtuple
from contextlib import contextmanager
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

from first_run import ai_failure, pick_codex
from private_dirs import private_dir

# The AI tasks. summary and speaker_names run in the Swift recorder; Python lists and checks them.
PURPOSES = ("live_analysis", "live_translation", "frame_relevance", "summary_rewrite", "summary", "speaker_names",
            "fact_check")
NEEDS_IMAGE = {"frame_relevance"}
CHOICE_KEYS = ("provider", "model", "effort", "speed")
STANDARD = "standard"  # an explicit "no speed tier" when a model offers tiers
WINDOWS = os.name == "nt"
DISCOVERY_TIMEOUT = 20
OUTPUT_LIMIT = 8 << 20  # characters kept per stream; the rest is read and dropped
LINE_LIMIT = 1 << 20
NO_CHOICE = ("Choose an AI tool and model in Getting started, then retry. "
             "Audio recording is independent.")
LEGACY_BACKENDS = {"claude-cli": "claude", "codex-cli": "codex", "ollama": "ollama"}
Reply = namedtuple("Reply", "text model session")
Ticket = namedtuple("Ticket", "purpose state reason choice key executable")
Result = namedtuple("Result", "returncode stdout stderr")
# Codex features that can act outside the prompt; off unless a call reads repositories.
CODEX_ISOLATION = ["--disable", "shell_tool", "--disable", "unified_exec", "--disable", "multi_agent",
                   "--disable", "enable_mcp_apps", "--disable", "skill_search",
                   "--disable", "skill_mcp_dependency_install", "--disable", "tool_suggest",
                   "-c", 'web_search="disabled"', "-c", "project_doc_max_bytes=0",
                   "-c", "skills.include_instructions=false"]


class AIChoiceError(RuntimeError):
    """A task cannot run: no complete choice (needs_choice) or the choice cannot do it."""
    def __init__(self, state, reason):
        self.state, self.reason = state, reason
        super().__init__(("AI_CHOICE: " if state == "needs_choice" else "AI_UNAVAILABLE: ") + reason)


def _stamp(path):
    """Identity of a file as it is now: resolved path, mtime and size ('' when absent)."""
    try:
        real = os.path.realpath(path)
        info = os.stat(real)
    except (OSError, TypeError, ValueError):
        return ""
    return f"{real}:{info.st_mtime_ns}:{info.st_size}"


TOOL_LOCATIONS = json.loads((Path(__file__).with_name("tool_locations.json")).read_text(encoding="utf-8"))


class _Binary:
    """Binary lookup only (a CLI path is not a model): env override, else the newest installed
    candidate from tool_locations.json (shared with Swift Tooling) or PATH, picked again whenever
    a candidate file changes (update, reinstall, removal)."""
    def __init__(self, env_name, name):
        self.env_name, self.name, self.memo = env_name, name, (None, None)
        self.lock = threading.Lock()

    def candidates(self):
        listed = [Path(os.path.expanduser(place)) for place in TOOL_LOCATIONS[self.name]]
        return [*listed, shutil.which(self.name)]

    def __call__(self):
        if os.environ.get(self.env_name):
            return Path(os.environ[self.env_name])
        candidates = self.candidates()
        signature = tuple(_stamp(candidate) for candidate in candidates)
        with self.lock:
            if signature != self.memo[0]:
                self.memo = (signature, pick_codex(candidates))
            return self.memo[1]


CODEX = _Binary("MEETING_COPILOT_CODEX", "codex")
CLAUDE = _Binary("MEETING_COPILOT_CLAUDE", "claude")
AGY = _Binary("MEETING_COPILOT_AGY", "agy")


def _unavailable(adapter, reason):
    return {"provider": adapter.name, "label": adapter.label, "state": "unavailable",
            "reason": reason, "plan": "", "models": [], "executable": ""}


def _available(adapter, models, plan="", executable=""):
    return {"provider": adapter.name, "label": adapter.label, "state": "available", "reason": "",
            "plan": plan or "", "models": models, "executable": str(executable or "")}


def _model(identity, label, efforts=(), speeds=(), speed_reason="", image=None, problem=""):
    """`image` is True/False when discovery says, None when it does not; `problem` makes
    the model unusable (e.g. discovery did not report a capability we must choose)."""
    return {"id": identity, "label": label or identity, "efforts": list(efforts), "speeds": list(speeds),
            "speed_reason": "" if speeds else speed_reason, "image": image, "problem": problem}


def _run(argv, stdin_text, env, timeout, cwd=None):
    """One child process with an absolute deadline and bounded output buffers."""
    process = subprocess.Popen([str(part) for part in argv], text=True, env=env, cwd=cwd,
                               stdin=subprocess.DEVNULL if stdin_text is None else subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    kept = {}

    def drain(name, stream):
        kept[name] = stream.read(OUTPUT_LIMIT)
        while stream.read(65536):
            pass
        stream.close()

    def feed():
        try:
            process.stdin.write(stdin_text)
            process.stdin.close()
        except OSError:
            pass

    workers = [threading.Thread(target=drain, args=pair, daemon=True)
               for pair in (("out", process.stdout), ("err", process.stderr))]
    workers += [threading.Thread(target=feed, daemon=True)] if stdin_text is not None else []
    for worker in workers:
        worker.start()
    try:
        process.wait(timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise TimeoutError(f"did not respond within {timeout} s") from None
    finally:
        for worker in workers:
            worker.join(5)
    return Result(process.returncode, kept.get("out", ""), kept.get("err", ""))


def _invoke(argv, prompt, env, timeout, cwd):
    try:
        return _run(argv, prompt, env, timeout, cwd)
    except TimeoutError:
        raise RuntimeError(ai_failure("timed out")) from None
    except OSError as error:
        raise RuntimeError(ai_failure(str(error))) from None


class _Lines:
    """A child process spoken to in JSON lines, with one absolute deadline and bounded reads."""
    def __init__(self, argv, env=None, cwd=None, timeout=None):
        self.timeout = DISCOVERY_TIMEOUT if timeout is None else timeout
        self.deadline = time.monotonic() + self.timeout
        self.proc = subprocess.Popen([str(part) for part in argv], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, env=env, cwd=cwd)
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        total = 0
        while total < OUTPUT_LIMIT:
            line = self.proc.stdout.readline(LINE_LIMIT)  # an oversized line arrives in pieces that fail to parse
            if not line:
                break
            total += len(line)
            self.lines.put(line)
        self.proc.stdout.close()
        self.lines.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def until(self, match):
        while True:
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"did not respond within {self.timeout} s")
            try:
                line = self.lines.get(timeout=left)
            except queue.Empty:
                continue
            if line is None:
                raise RuntimeError("exited before answering")
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if isinstance(message, dict) and match(message):
                return message

    def close(self):
        self.proc.kill()
        self.proc.wait()
        try:
            self.proc.stdin.close()
        except OSError:
            pass


def _discovery(adapter, body):
    """Run one discovery; every failure becomes `unavailable` with a reason."""
    binary = adapter.binary()
    if not binary or not Path(binary).is_file():
        return _unavailable(adapter, f"{adapter.label} is not installed")
    try:
        return body(binary)
    except (OSError, subprocess.SubprocessError, TimeoutError, RuntimeError, ValueError, KeyError, TypeError) as error:
        return _unavailable(adapter, f"{adapter.label} {error}".strip())


def _workdir():
    """The one empty working directory every call starts in: stable, so sessions resume, and
    outside the temp folder, which Codex would otherwise leave writable as a project root."""
    directory = Path(os.environ.get("MEETING_COPILOT_AI_WORKDIR") or Path.home() / ".cache/meeting-copilot/ai-workdir")
    private_dir(directory)
    return str(directory)


@contextmanager
def _image_dir(image):
    """A fresh directory holding only a copy of the screenshot, or None without one."""
    if not image:
        yield None
        return
    with tempfile.TemporaryDirectory(prefix="meetontrack-image-") as directory:
        shutil.copyfile(image, Path(directory) / Path(image).name)
        yield directory


def _json_lines(text):
    for line in (text or "").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            yield item


def _toml(text):
    return json.dumps(str(text))  # a JSON string is a valid TOML basic string


class CodexAdapter:
    name, label, reads_files, web_search = "codex", "Codex", True, True

    def __init__(self, binary=None):
        self.binary = binary or CODEX

    def identity(self, env=None):
        home = Path((env or os.environ).get("CODEX_HOME") or Path.home() / ".codex")
        return _stamp(self.binary()) + "|" + _stamp(home / "auth.json")

    def discover(self, env=None):
        def body(binary):
            session = _Lines([binary, "app-server"], env=env)
            try:
                ids = itertools.count(1)

                def request(method, params=None):
                    identity = next(ids)
                    session.send({"id": identity, "method": method, "params": params or {}})
                    reply = session.until(lambda message: message.get("id") == identity)
                    if reply.get("error"):
                        raise RuntimeError(str(reply["error"].get("message") or reply["error"]))
                    return reply.get("result") or {}

                request("initialize", {"clientInfo": {"name": "meetontrack", "version": "0"}})
                session.send({"method": "initialized"})
                account = request("account/read").get("account")
                if not account:
                    return _unavailable(self, "Codex is installed but not signed in. Sign in, then refresh.")
                listed, cursor = [], None
                for _ in range(50):
                    page = request("model/list", {"cursor": cursor} if cursor else {})
                    listed += page.get("data") or []
                    cursor = page.get("nextCursor")
                    if not cursor:
                        break
            finally:
                session.close()
            fast_allowed = account.get("type") == "chatgpt"
            return _available(self, [self._entry(item, fast_allowed) for item in listed if not item.get("hidden")],
                              account.get("planType") or account.get("type"), binary)
        return _discovery(self, body)

    @staticmethod
    def _entry(item, fast_allowed):
        efforts, inputs = item.get("supportedReasoningEfforts"), item.get("inputModalities")
        speeds = [{"id": tier["id"], "label": tier.get("name") or tier["id"]}
                  for tier in item.get("serviceTiers") or []] if fast_allowed else []
        return _model(item["id"], item.get("displayName"), [effort["reasoningEffort"] for effort in efforts or []],
                      speeds, "This model has no speed tiers" if fast_allowed else
                      "Speed tiers need a ChatGPT sign-in in Codex",
                      image=("image" in inputs) if isinstance(inputs, list) else None,
                      problem="" if isinstance(efforts, list) else "Codex did not report its effort levels")

    @staticmethod
    def _windows_sandbox(env):
        """The Windows sandbox set up in Codex itself (`[windows] sandbox`). The rest of the person's
        Codex config is ignored, but on Windows only the elevated sandbox can keep reads to the
        profile's folders; without it Codex refuses to read files (MEETONTRACK-86)."""
        if not WINDOWS:
            return []
        import tomllib  # bundled Windows Python; macOS may run an older system Python
        home = Path((env or os.environ).get("CODEX_HOME") or Path.home() / ".codex")
        try:
            windows = tomllib.loads((home / "config.toml").read_text(encoding="utf-8")).get("windows")
        except (OSError, ValueError):
            return []
        mode = windows.get("sandbox") if isinstance(windows, dict) else None
        return ["-c", f"windows.sandbox={_toml(mode)}"] if isinstance(mode, str) and mode else []

    def call(self, choice, prompt, *, executable, env, timeout, roots=(), image=None, resume="", keep_session=False,
             web=False):
        workdir, executable = _workdir(), os.path.realpath(executable)
        # Read-only everywhere it is allowed to look; Codex must also read its own package
        # (its sandbox helper re-executes the binary by its resolved path). Writes and
        # every other path are denied.
        readable = [":minimal", ":project_roots", workdir, Path(executable).parent.parent, *roots]
        profile = "{" + ",".join([*(f'{_toml(path)}="read"' for path in readable),
                                  '":tmpdir"="deny"', '":slash_tmp"="deny"']) + "}"
        argv = [executable, "--ask-for-approval", "never", "-m", choice["model"]]
        argv += ["-c", f"model_reasoning_effort={_toml(choice['effort'])}"] if choice["effort"] else []
        argv += ["-c", f"service_tier={_toml(choice['speed'])}"] if choice["speed"] not in ("", STANDARD) else []
        argv += ["-c", 'default_permissions="meetontrack"', "-c", "permissions.meetontrack.filesystem=" + profile]
        argv += self._windows_sandbox(env)
        argv += ["exec", "resume"] if resume else ["exec"]
        argv += ["--ignore-user-config", "--skip-git-repo-check"]
        isolation = [part.replace('"disabled"', '"live"') if web and part.startswith("web_search=") else part
                     for part in CODEX_ISOLATION]  # web search only for a call that asks for it
        argv += [] if roots else isolation  # every turn, first or resumed
        if resume:
            argv += ["--json", resume, "-"]
        else:
            argv += [] if keep_session else ["--ephemeral"]
            argv += ["--image", str(image)] if image else []
            argv += ["-C", workdir, "--json", "-"]
        result = _invoke(argv, prompt, env, timeout, workdir)
        answers, session = [], resume
        for event in _json_lines(result.stdout):
            if event.get("type") == "thread.started":
                session = event.get("thread_id") or session
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == "agent_message" and item.get("text"):
                answers.append(item["text"].strip())
        if result.returncode or not answers:
            raise RuntimeError(ai_failure((result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"))
        # `codex exec --json` does not report the model; the requested one is what ran.
        return Reply(answers[-1], choice["model"], session)


class ClaudeAdapter:
    name, label, reads_files, web_search = "claude", "Claude Code", True, True
    # --restricted confines file tools to the working directories (cwd and --add-dir).
    ISOLATED = ["--restricted", "--setting-sources", "", "--strict-mcp-config"]
    FAST_OPT_IN = {None, "", "sdk_opt_in_required"}  # opt-in is what --settings fastMode does

    def __init__(self, binary=None):
        self.binary = binary or CLAUDE

    def identity(self, env=None):
        """Executable plus the signed-in account: switching accounts re-runs discovery and
        invalidates readiness and sessions. Env credentials count by hash, never by value."""
        env = env or os.environ
        home = env.get("CLAUDE_CONFIG_DIR")
        path = Path(home) / ".claude.json" if home else Path(env.get("HOME") or Path.home()) / ".claude.json"
        stamp = _stamp(path)
        if getattr(self, "_account", (None,))[0] != stamp:
            try:
                account = json.loads(path.read_text(encoding="utf-8")).get("oauthAccount") or {}
            except (OSError, ValueError, AttributeError):
                account = {}
            self._account = (stamp, f"{account.get('accountUuid', '')}/{account.get('organizationUuid', '')}")
        secrets = "".join(env.get(name, "") for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"))
        secret = hashlib.sha256(secrets.encode()).hexdigest()[:16] if secrets else ""
        return f"{_stamp(self.binary())}|{self._account[1]}|{secret}"

    def discover(self, env=None):
        def body(binary):
            run = _run([binary, "auth", "status", "--json"], None, env, DISCOVERY_TIMEOUT)
            try:
                auth = json.loads(run.stdout or "{}")
            except ValueError:
                auth = {}
            if not auth.get("loggedIn"):
                return _unavailable(self, "Claude Code is installed but not signed in. Sign in, then refresh.")
            session = _Lines([binary, "-p", "--input-format", "stream-json", "--output-format", "stream-json",
                              "--verbose", *self.ISOLATED, "--tools", "", "--no-session-persistence"],
                             env=env, cwd=_workdir())
            try:
                session.send({"type": "control_request", "request_id": "meetontrack-init",
                              "request": {"subtype": "initialize"}})
                reply = session.until(lambda message: message.get("type") == "control_response")["response"]
            finally:
                session.close()
            info = reply.get("response") or reply
            fast_reason = info.get("fast_mode_disabled_reason")
            models = []
            for item in info.get("models") or []:
                levels = item.get("supportedEffortLevels")
                offered = bool(item.get("supportsFastMode")) and fast_reason in self.FAST_OPT_IN
                why = ("This model has no fast mode" if not item.get("supportsFastMode")
                       else f"Fast mode is unavailable: {fast_reason}")
                # Claude Code does not report image input, so screenshots are not offered here.
                models.append(_model(item["value"], item.get("displayName"), levels or [],
                                     [{"id": "fastMode", "label": "Fast mode"}] if offered else [], why,
                                     problem="Claude Code did not report its effort levels"
                                     if item.get("supportsEffort") and not isinstance(levels, list) else ""))
            account = info.get("account") or {}
            return _available(self, models, account.get("subscriptionType") or auth.get("subscriptionType"), binary)
        return _discovery(self, body)

    def call(self, choice, prompt, *, executable, env, timeout, roots=(), image=None, resume="", keep_session=False,
             web=False):
        argv = [executable, "-p", "--output-format", "stream-json", "--verbose", *self.ISOLATED,
                "--model", choice["model"]]
        argv += ["--effort", choice["effort"]] if choice["effort"] else []
        argv += ["--settings", json.dumps({"fastMode": True})] if choice["speed"] == "fastMode" else []
        argv += [f"--add-dir={root}" for root in roots]
        tools = "Read,Grep,Glob" if roots else "Read" if image else ""
        tools = ",".join(filter(None, [tools, "WebSearch,WebFetch" if web else ""]))
        argv += ["--tools", tools] + (["--allowedTools", tools] if tools else [])
        argv += ["--resume", resume] if resume else [] if keep_session else ["--no-session-persistence"]
        with _image_dir(image) as directory:
            if directory:
                prompt += (f"\n\nThe screenshot is the file {Path(image).name} in the working directory. "
                           "Read that one file; do not read anything else.")
            result = _invoke(argv, prompt, env, timeout, directory or _workdir())
        model, session, text, failed = choice["model"], resume, None, True
        for event in _json_lines(result.stdout):
            if event.get("type") == "system" and event.get("subtype") == "init":
                model = event.get("model") or model
                session = event.get("session_id") or session
            elif event.get("type") == "result":
                text, failed = str(event.get("result") or ""), bool(event.get("is_error"))
                session = event.get("session_id") or session
        if result.returncode or failed or not text:
            raise RuntimeError(ai_failure((text or result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"))
        return Reply(text.strip(), model, session)


class AntigravityAdapter:
    """Discovery only: agy reports permission_mode always-proceed even with --mode plan --sandbox,
    so a read-only, no-tools call cannot be enforced. Re-enable when agy can enforce it."""
    name, label, reads_files, web_search = "antigravity", "Antigravity", False, False
    BLOCKED = "cannot enforce read-only/no-tools: permission_mode always-proceed"
    SUFFIX = re.compile(r"^(.*) \(([^()]+)\)$")

    def __init__(self, binary=None):
        self.binary = binary or AGY

    def identity(self, env=None):
        return _stamp(self.binary())

    def discover(self, env=None):
        def body(binary):
            run = _run([binary, "models"], None, env, DISCOVERY_TIMEOUT)
            if run.returncode:
                raise RuntimeError((run.stderr or run.stdout).strip()[:300] or "could not list models")
            grouped = {}
            for line in run.stdout.splitlines():
                identity, _, name = line.partition("\t")
                if not name:
                    continue
                match = self.SUFFIX.match(name.strip())
                effort = match.group(2).lower() if match else ""
                base, label = (identity[:-len(effort) - 1], match.group(1)) if effort and identity.endswith("-" + effort) \
                    else (identity, name.strip())
                entry = grouped.setdefault(base, {"label": label, "efforts": []})
                if base != identity:
                    entry["efforts"].append(effort)
            if not grouped:
                raise RuntimeError("lists no models for this account; sign in, then refresh")
            found = _available(self, [_model(base, item["label"], item["efforts"], (),
                                             "Antigravity does not report speed tiers")
                                      for base, item in grouped.items()], executable=binary)
            return {**found, "state": "unavailable", "reason": f"Antigravity {self.BLOCKED}"}
        return _discovery(self, body)

    def call(self, choice, prompt, **options):
        raise AIChoiceError("unavailable", f"Antigravity {self.BLOCKED}")


class OllamaAdapter:
    name, label, reads_files, web_search = "ollama", "Ollama", False, False
    SESSIONS, HISTORY = 8, 40  # conversations kept in memory, turn messages kept per conversation (plus its rules)
    REPLY_TOKENS = 4096  # context kept free for the answer (same as Swift LLMBackend.ollamaReplyTokens)

    @staticmethod
    def context_length(shown):
        """model_info["<general.architecture>.context_length"] from /api/show, or None."""
        info = shown.get("model_info") if isinstance(shown.get("model_info"), dict) else {}
        length = info.get(f"{info.get('general.architecture')}.context_length")
        return length if isinstance(length, int) and not isinstance(length, bool) and length > 0 else None

    @classmethod
    def fit(cls, pinned, turns, prompt, context):
        """(messages to send before the prompt, num_ctx). `pinned` is the session's system message
        (its first prompt: the session rules) and is never dropped; only the oldest conversation
        turns are, whole, never cut mid-message. A request that cannot fit is rejected.
        ponytail: one character counts as at least one token (true for Latin/Cyrillic); images not
        counted; use the tokenizer if CJK or image-heavy requests get cut."""
        size = lambda messages: sum(len(str(m.get("content", ""))) for m in messages)
        budget, pinned = context - cls.REPLY_TOKENS, [pinned] if pinned else []
        if len(prompt) + size(pinned) > budget:
            raise RuntimeError(f"The text is longer than this Ollama model's context of {context} tokens. "
                               "Choose a model with a longer context in Getting started.")
        turns = list(turns)
        while turns and len(prompt) + size(pinned + turns) > budget:
            turns = turns[1:]  # oldest message first
        used = len(prompt) + size(pinned + turns)
        return pinned + turns, min(context, used + cls.REPLY_TOKENS)

    def __init__(self, host=None):
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        if "://" not in self.host:
            self.host = "http://" + self.host
        self.sessions, self.lock = OrderedDict(), threading.Lock()

    def identity(self, env=None):
        return self.host

    def _request(self, path, payload=None, timeout=5):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.host + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read(OUTPUT_LIMIT).decode("utf-8"))

    def discover(self, env=None):
        deadline = time.monotonic() + DISCOVERY_TIMEOUT  # one budget for every per-model probe
        try:
            tags = self._request("/api/tags", timeout=3)
        except (OSError, ValueError) as error:
            return _unavailable(self, f"Ollama is not running at {self.host}: {getattr(error, 'reason', error)}")
        models = []
        for item in tags.get("models") or []:
            name = str(item.get("name") or "")
            left = deadline - time.monotonic()
            if not name:
                continue
            if left <= 0:
                models.append(_model(name, name, problem="Ollama did not describe this model in time; refresh"))
                continue
            try:
                shown = self._request("/api/show", {"model": name}, timeout=min(5, left))
            except (OSError, ValueError) as error:
                if isinstance(error, urllib.error.HTTPError):
                    error.close()
                models.append(_model(name, name, problem=f"Ollama could not describe this model: {error}"))
                continue
            thinking = shown.get("thinking") if isinstance(shown.get("thinking"), dict) else {}
            values, capabilities = thinking.get("values"), shown.get("capabilities")
            image = ("vision" in capabilities) if isinstance(capabilities, list) else None
            if isinstance(capabilities, list) and "completion" not in capabilities:
                models.append(_model(name, name, image=image,
                                     problem="this model does not generate text (no completion capability)"))
                continue
            if self.context_length(shown) is None:
                models.append(_model(name, name, image=image,
                                     problem="Ollama does not report this model's context length"))
                continue
            advertised = "thinking" in shown or (isinstance(capabilities, list) and "thinking" in capabilities)
            if advertised and not (isinstance(values, list) and values):
                models.append(_model(name, name, image=image,
                                     problem="Ollama reports thinking for this model but not its levels"))
                continue
            efforts = [] if not values or values == [False] else \
                [str(value).lower() if isinstance(value, bool) else str(value) for value in values]
            models.append(_model(name, name, efforts, (), "Ollama does not report speed tiers", image=image))
        return _available(self, models, "local")

    def call(self, choice, prompt, *, executable="", env=None, timeout, roots=(), image=None, resume="", keep_session=False,
             web=False):
        if web:
            raise AIChoiceError("unavailable", "Ollama cannot search the web.")
        if roots:
            raise AIChoiceError("unavailable", "Ollama cannot read the selected repositories. Choose Codex or "
                                               "Claude Code for live analysis, or disconnect the repositories.")
        with self.lock:
            pinned, turns = self.sessions.get(resume, (None, ())) if resume else (None, ())
        try:
            context = self.context_length(self._request("/api/show", {"model": choice["model"]}, timeout=10))
        except (OSError, ValueError) as error:
            raise RuntimeError(ai_failure(f"connection failed: {error}")) from None
        if context is None:
            raise AIChoiceError("unavailable", f"Ollama does not report the context length of {choice['model']}. "
                                               "Choose another model in Getting started.")
        history, num_ctx = self.fit(pinned, turns, prompt, context)
        message = {"role": "user", "content": prompt}
        sent = {**message, "images": [base64.b64encode(Path(image).read_bytes()).decode("ascii")]} if image else message
        payload = {"model": choice["model"], "messages": history + [sent], "stream": False,
                   "options": {"num_ctx": num_ctx}}
        if choice["effort"]:
            payload["think"] = {"true": True, "false": False}.get(choice["effort"], choice["effort"])
        try:
            reply = self._request("/api/chat", payload, timeout=timeout)
        except urllib.error.HTTPError as error:
            raise RuntimeError(ai_failure(error.read(4096).decode("utf-8", "replace"))) from None
        except (OSError, ValueError) as error:
            raise RuntimeError(ai_failure(f"connection failed: {error}")) from None
        text = str((reply.get("message") or {}).get("content") or "").strip()
        if not text:
            raise RuntimeError(ai_failure(str(reply.get("error") or "empty reply")))
        session = ""
        if keep_session or resume:  # Ollama is stateless: the conversation is kept here
            with self.lock:
                session = resume if resume in self.sessions else uuid.uuid4().hex
                # the first prompt carries the session rules: kept as the system message, never trimmed
                kept = (pinned, [*history[1 if pinned else 0:], message]) if pinned else \
                    ({"role": "system", "content": prompt}, [])
                self.sessions[session] = (kept[0], (kept[1] + [{"role": "assistant", "content": text}])[-self.HISTORY:])
                self.sessions.move_to_end(session)
                while len(self.sessions) > self.SESSIONS:
                    self.sessions.popitem(last=False)
        return Reply(text, reply.get("model") or choice["model"], session)


def default_adapters():
    return [CodexAdapter(), ClaudeAdapter(), AntigravityAdapter(), OllamaAdapter()]


@contextmanager
def _file_lock(path):
    """Advisory lock on config.json.lock, shared with the Swift recorder. POSIX: flock().
    Windows: msvcrt.locking on byte 0 (it retries for about 10 s, then raises OSError)."""
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)  # closing releases the lock on both platforms


class AISettings:
    """The `ai` section of the shared config.json; every other key belongs to other components."""
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def choice(self):
        """The stored `ai.choice` (a dict, possibly partial) or None. When the file has none yet,
        the old per-task choices are carried over once (`migrated_choice`) and written."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        section = data.get("ai") if isinstance(data, dict) else None
        if isinstance(section, dict) and "choice" in section:
            return section["choice"] if isinstance(section["choice"], dict) else None
        adopted = migrated_choice(data) if isinstance(data, dict) else None
        if adopted is None:
            return None
        try:  # under the lock, only if still absent: a choice saved meanwhile wins
            written = self._update(lambda section: section.setdefault("choice", adopted)).get("choice")
        except (OSError, ValueError):
            return adopted
        return written if isinstance(written, dict) else None

    def set_choice(self, choice):
        self._update(lambda section: section.__setitem__("choice", choice))

    def _update(self, change):
        """Read-modify-replace of `ai` under config.json.lock: missing file = empty, malformed =
        refuse, result written 0600 to a temp file in the same directory, then renamed over.
        Returns the `ai` section as written."""
        private_dir(self.path.parent)
        with self.lock, _file_lock(self.path.with_name(self.path.name + ".lock")):
            try:
                text = self.path.read_text(encoding="utf-8")
            except FileNotFoundError:
                text = None
            try:
                data = {} if text is None else json.loads(text)
            except ValueError:
                raise ValueError(f"{self.path} is not valid JSON; fix it before saving the AI choice") from None
            if not isinstance(data, dict):
                raise ValueError(f"{self.path} must hold a JSON object")
            section = dict(data["ai"]) if isinstance(data.get("ai"), dict) else {}
            change(section)
            data["ai"] = section
            handle, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".config.", suffix=".tmp")
            try:
                if os.name != "nt":
                    os.fchmod(handle, 0o600)  # before any byte is written
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    stream.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
            return section


def _legacy_choice(data, name):
    """{provider[, model]} from the settings before `ai` (summary.backend, speaker_names.backend),
    only from keys written in the file. Same mapping as the Swift migration of phase 2."""
    def text(section, key):
        value = section.get(key) if isinstance(section, dict) else None
        return value.strip() if isinstance(value, str) and value.strip() else None
    summary, section = data.get("summary"), data.get(name)
    provider = LEGACY_BACKENDS.get(text(section, "backend") or "")
    if not provider:
        return None
    model = {"claude": text(section, "model") or text(summary, "model"), "codex": text(summary, "openai_model"),
             "ollama": text(summary, "ollama_model")}[provider]  # naming used the summary's codex/ollama model
    return {"provider": provider, **({"model": model} if model else {})}


def migrated_choice(data):
    """The one choice carried over when `ai.choice` is absent (owner decision 2026-10-21).
    Complete per-task choices: all identical, or only one, is adopted; several that differ adopt
    live_analysis if it is complete, else nothing. Without any, the legacy summary/naming
    backends feed it by the same rule (partial: the person still picks effort and speed)."""
    section = data.get("ai") if isinstance(data.get("ai"), dict) else {}
    purposes = section.get("purposes") if isinstance(section.get("purposes"), dict) else {}
    complete = [choice for choice in map(_normal, purposes.values()) if choice]
    if complete:
        return complete[0] if all(choice == complete[0] for choice in complete) else \
            _normal(purposes.get("live_analysis"))
    legacy = [choice for choice in (_legacy_choice(data, name) for name in ("summary", "speaker_names")) if choice]
    return legacy[0] if legacy and all(choice == legacy[0] for choice in legacy) else None


def _normal(choice):
    """A complete choice (all four keys present as strings, provider and model set), else None."""
    if not isinstance(choice, dict) or not all(isinstance(choice.get(key), str) for key in CHOICE_KEYS):
        return None
    choice = {key: choice[key].strip() for key in CHOICE_KEYS}
    return choice if choice["provider"] and choice["model"] else None


def choice_problem(found, choice, purpose=""):
    """(state, reason) for running the choice (for one task when `purpose` is given) with the
    provider as discovered now. A task-specific need fails only that task."""
    label, model_id = found.get("label") or choice["provider"], choice["model"]
    if found.get("state") != "available":
        return "unavailable", f"{label} is unavailable: {found.get('reason') or 'unknown reason'}"
    model = next((item for item in found.get("models", []) if item["id"] == model_id), None)
    if model is None:
        return "unavailable", f"{label} does not offer the model {model_id} now. Choose a model again."
    if model.get("problem"):
        return "unavailable", f"{label} cannot run {model_id}: {model['problem']}."
    if purpose in NEEDS_IMAGE and model.get("image") is not True:
        why = "does not accept images" if model.get("image") is False else "is not reported to accept images"
        return "unavailable", (f"Your chosen model {model_id} {why}, so screenshots are not analysed. "
                               "Choose a model that accepts images to turn this on.")
    if model["efforts"] and choice["effort"] not in model["efforts"]:
        return "needs_choice", f"Choose an effort level for {model_id} in Getting started."
    if not model["efforts"] and choice["effort"]:
        return "needs_choice", f"{model_id} has no effort levels; choose it again in Getting started."
    tiers = [speed["id"] for speed in model["speeds"]]
    if tiers and choice["speed"] not in [STANDARD, *tiers]:
        return "needs_choice", f"Choose a speed for {model_id} in Getting started."
    if not tiers and choice["speed"]:
        return "needs_choice", f"No speed tiers are offered for {model_id}: {model['speed_reason']}"
    return "ready", ""


class AIService:
    PURPOSES = PURPOSES

    def __init__(self, config_path, env, adapters=None, ttl=300):
        self.settings, self.env, self.ttl = AISettings(config_path), env, ttl
        self.adapters = {adapter.name: adapter for adapter in (adapters if adapters is not None else default_adapters())}
        self.cache, self.lock, self.provider_locks = {}, threading.Lock(), {}

    def providers(self):
        return [{"provider": name, "label": adapter.label} for name, adapter in self.adapters.items()]

    def options(self, provider, refresh=False):
        """Discovery bound to the executable (and sign-in) it ran: a change re-runs it."""
        adapter = self.adapters.get(provider)
        if adapter is None:
            return {"provider": provider, "label": provider, "state": "unavailable", "reason": "Unknown AI provider",
                    "plan": "", "models": [], "executable": "", "identity": ""}
        with self.lock:
            provider_lock = self.provider_locks.setdefault(provider, threading.Lock())
        with provider_lock:  # one discovery per provider at a time
            identity = adapter.identity(self.env)
            cached = self.cache.get(provider)
            ttl = self.ttl if cached and cached[2]["state"] == "available" else min(self.ttl, 30)
            if refresh or not cached or cached[1] != identity or time.monotonic() - cached[0] > ttl:
                cached = (time.monotonic(), identity, {**adapter.discover(self.env), "identity": identity})
                self.cache[provider] = cached
            return cached[2]

    def resolve(self, purpose=""):
        """Snapshot of what one invocation of a task will run: the one choice, its state for this
        task (any task when `purpose` is empty), executable and a key that changes with the
        choice or the executable (sessions and checks belong to a key)."""
        stored = self.settings.choice()
        choice = _normal(stored)
        if choice is None:
            partial = isinstance(stored, dict) and stored.get("provider") and stored.get("model")
            return Ticket(purpose, "needs_choice", "Finish the AI choice (effort and speed) in Getting "
                          "started." if partial else NO_CHOICE, stored, "", "")
        found = self.options(choice["provider"])
        state, reason = choice_problem(found, choice, purpose)
        key = json.dumps({"choice": choice, "identity": found.get("identity", "")}, sort_keys=True)
        return Ticket(purpose, state, reason, choice, key, found.get("executable", ""))

    def tickets(self):
        return {purpose: self.resolve(purpose) for purpose in PURPOSES}

    def status(self, purpose=""):
        """The choice for one task, or for no task in particular when `purpose` is empty."""
        ticket = self.resolve(purpose)
        return {"purpose": purpose, "state": ticket.state, "choice": ticket.choice, "reason": ticket.reason}

    def status_all(self):
        return {purpose: self.status(purpose) for purpose in PURPOSES}

    def save(self, choice):
        """Save the one choice. It must be runnable as such; a task it cannot do (screenshots
        without image input) is reported by that task's status, not refused here."""
        choice = _normal(choice)
        if choice is None:
            raise ValueError("Choose a provider, a model, an effort level and a speed")
        state, reason = choice_problem(self.options(choice["provider"]), choice)
        if state != "ready":
            raise ValueError(reason)
        self.settings.set_choice(choice)
        return self.status()

    def web_search(self, choice=None):
        """(searches, labels): whether the provider of `choice` (the stored one when None) can search
        the web, and the labels of the providers that can, to tell the person what to choose."""
        choice = self.settings.choice() if choice is None else choice
        adapter = self.adapters.get((choice or {}).get("provider") if isinstance(choice, dict) else None)
        return (bool(getattr(adapter, "web_search", False)),
                [item.label for item in self.adapters.values() if getattr(item, "web_search", False)])

    def run(self, purpose, prompt, ticket=None, **options):
        """Run with the ticket's snapshot (resolved now when none is given)."""
        ticket = ticket or self.resolve(purpose)
        if ticket.state != "ready":
            raise AIChoiceError(ticket.state, ticket.reason)
        options.setdefault("env", self.env)
        options.setdefault("timeout", 120)
        return self.adapters[ticket.choice["provider"]].call(ticket.choice, prompt, executable=ticket.executable,
                                                              **options)
