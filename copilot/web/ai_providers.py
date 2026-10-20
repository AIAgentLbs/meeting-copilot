"""AI provider layer: discovery, per-purpose choice and calls. Holds no model ids.

Adapters read the options (models, efforts, speed tiers, plan) from the exact binary or
service that will run, and turn a stored choice into a call. The choice lives in the
shared ~/.config/meeting-copilot/config.json under `ai` (schema: docs/config.schema.json);
this module writes only that subtree. Nothing here runs at import time.
"""
from __future__ import annotations

from collections import namedtuple
from contextlib import contextmanager
import base64
import itertools
import json
import os
from pathlib import Path
import queue
import re
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request

from first_run import ai_failure, pick_codex, resolve_codex

PURPOSES = ("live_analysis", "live_translation", "frame_relevance", "summary_rewrite")
CHOICE_KEYS = ("provider", "model", "effort", "speed")
DISCOVERY_TIMEOUT = 20
Reply = namedtuple("Reply", "text model session")
# Codex features that can act outside the prompt; off unless a purpose needs files.
CODEX_ISOLATION = ["--disable", "shell_tool", "--disable", "unified_exec", "--disable", "multi_agent",
                   "--disable", "enable_mcp_apps", "--disable", "skill_search",
                   "--disable", "skill_mcp_dependency_install", "--disable", "tool_suggest",
                   "-c", 'web_search="disabled"', "-c", "project_doc_max_bytes=0",
                   "-c", "skills.include_instructions=false"]


def _newest(env_name, name):
    """Binary lookup only (a CLI path is not a model): env override, else newest installed."""
    def resolve():
        if os.environ.get(env_name):
            return Path(os.environ[env_name])
        home = Path.home()
        return pick_codex([home / ".local/bin" / name, shutil.which(name),
                           Path("/opt/homebrew/bin") / name, Path("/usr/local/bin") / name])
    return resolve


def _unavailable(adapter, reason):
    return {"provider": adapter.name, "label": adapter.label, "state": "unavailable",
            "reason": reason, "plan": "", "models": [], "current": {}}


def _available(adapter, models, plan="", current=None):
    return {"provider": adapter.name, "label": adapter.label, "state": "available", "reason": "",
            "plan": plan or "", "models": models, "current": current or {}}


def _model(identity, label, efforts=(), speeds=(), speed_reason=""):
    return {"id": identity, "label": label or identity, "efforts": list(efforts),
            "speeds": list(speeds), "speed_reason": "" if speeds else speed_reason}


class _Lines:
    """A child process spoken to in JSON lines, with one deadline for the whole exchange."""
    def __init__(self, argv, env=None, cwd=None, timeout=DISCOVERY_TIMEOUT):
        self.proc = subprocess.Popen([str(part) for part in argv], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, env=env, cwd=cwd)
        self.deadline = time.monotonic() + timeout
        self.timeout = timeout
        self.lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.proc.stdout.close()
        self.lines.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def until(self, match):
        while True:
            try:
                line = self.lines.get(timeout=max(0.0, self.deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError(f"did not respond within {self.timeout} s") from None
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
    binary = adapter.binary() if hasattr(adapter, "binary") else None
    if hasattr(adapter, "binary") and (not binary or not Path(binary).is_file()):
        return _unavailable(adapter, f"{adapter.label} is not installed")
    try:
        return body(binary)
    except (OSError, subprocess.SubprocessError, TimeoutError, RuntimeError, ValueError, KeyError, TypeError) as error:
        return _unavailable(adapter, f"{adapter.label} {error}".strip())


@contextmanager
def _workdir(cwd, files):
    if cwd:
        yield str(cwd)
    elif files:
        yield str(Path.home())
    else:
        with tempfile.TemporaryDirectory(prefix="meetontrack-ai-") as directory:
            yield directory


def _run(argv, prompt, env, timeout, cwd):
    try:
        return subprocess.run([str(part) for part in argv], input=prompt, text=True, capture_output=True,
                              timeout=timeout, check=False, env=env, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise RuntimeError(ai_failure("timed out")) from None
    except OSError as error:
        raise RuntimeError(ai_failure(str(error))) from None


def _json_lines(text):
    for line in (text or "").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            yield item


class CodexAdapter:
    name, label = "codex", "Codex"

    def __init__(self, binary=resolve_codex):
        self.binary = binary

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
                config = request("config/read").get("config") or {}
            finally:
                session.close()
            fast_allowed = account.get("type") == "chatgpt"
            models = [_model(item["id"], item.get("displayName"),
                             [effort["reasoningEffort"] for effort in item.get("supportedReasoningEfforts") or []],
                             [{"id": tier["id"], "label": tier.get("name") or tier["id"]}
                              for tier in item.get("serviceTiers") or []] if fast_allowed else [],
                             "This model has no speed tiers" if fast_allowed else
                             "Speed tiers need a ChatGPT sign-in in Codex")
                      for item in listed if not item.get("hidden")]
            return _available(self, models, account.get("planType") or account.get("type"),
                              {"model": config.get("model") or "", "effort": config.get("model_reasoning_effort") or "",
                               "speed": config.get("service_tier") or ""})
        return _discovery(self, body)

    def call(self, choice, prompt, *, env, timeout, files=False, image=None, cwd=None, resume="", keep_session=False):
        argv = [self.binary(), "--ask-for-approval", "never", "-m", choice["model"]]
        if choice.get("effort"):
            argv += ["-c", f'model_reasoning_effort="{choice["effort"]}"']
        if choice.get("speed"):
            argv += ["-c", f'service_tier="{choice["speed"]}"']
        with _workdir(cwd, files) as directory:
            if resume:
                argv += ["exec", "resume", "--ignore-user-config", "--skip-git-repo-check", "--json", resume, "-"]
            else:
                argv += ["exec", "--ignore-user-config", "--sandbox", "read-only", "--skip-git-repo-check"]
                argv += [] if keep_session else ["--ephemeral"]
                argv += [] if files else CODEX_ISOLATION
                argv += ["--image", str(image)] if image else []
                argv += ["-C", directory, "--json", "-"]
            result = _run(argv, prompt, env, timeout, directory)
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
    name, label = "claude", "Claude Code"
    ISOLATED = ["--setting-sources", "", "--strict-mcp-config"]
    FAST_OPT_IN = {None, "", "sdk_opt_in_required"}  # opt-in is what --settings fastMode does

    def __init__(self, binary=_newest("MEETING_COPILOT_CLAUDE", "claude")):
        self.binary = binary

    def discover(self, env=None):
        def body(binary):
            run = subprocess.run([str(binary), "auth", "status", "--json"], text=True, capture_output=True,
                                 timeout=DISCOVERY_TIMEOUT, check=False, env=env)
            try:
                auth = json.loads(run.stdout or "{}")
            except ValueError:
                auth = {}
            if not auth.get("loggedIn"):
                return _unavailable(self, "Claude Code is installed but not signed in. Sign in, then refresh.")
            with tempfile.TemporaryDirectory(prefix="meetontrack-ai-") as directory:
                session = _Lines([binary, "-p", "--input-format", "stream-json", "--output-format", "stream-json",
                                  "--verbose", *self.ISOLATED, "--no-session-persistence"], env=env, cwd=directory)
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
                offered = bool(item.get("supportsFastMode")) and fast_reason in self.FAST_OPT_IN
                why = ("This model has no fast mode" if not item.get("supportsFastMode")
                       else f"Fast mode is unavailable: {fast_reason}")
                models.append(_model(item["value"], item.get("displayName"), item.get("supportedEffortLevels") or [],
                                     [{"id": "fastMode", "label": "Fast mode"}] if offered else [], why))
            account = info.get("account") or {}
            return _available(self, models, account.get("subscriptionType") or auth.get("subscriptionType"))
        return _discovery(self, body)

    def call(self, choice, prompt, *, env, timeout, files=False, image=None, cwd=None, resume="", keep_session=False):
        argv = [self.binary(), "-p", "--output-format", "stream-json", "--verbose", *self.ISOLATED,
                "--model", choice["model"]]
        if choice.get("effort"):
            argv += ["--effort", choice["effort"]]
        if choice.get("speed") == "fastMode":
            argv += ["--settings", json.dumps({"fastMode": True})]
        tools = "Read,Grep,Glob" if files else "Read" if image else ""
        argv += ["--tools", tools] + (["--allowedTools", tools] if tools else [])
        argv += ["--resume", resume] if resume else [] if keep_session else ["--no-session-persistence"]
        if image:
            prompt += f"\n\nThe screenshot is the image file {image}. Read that one file; do not read anything else."
            cwd = cwd or Path(image).parent
        with _workdir(cwd, files) as directory:
            result = _run(argv, prompt, env, timeout, directory)
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
    name, label = "antigravity", "Antigravity"
    SUFFIX = re.compile(r"^(.*) \(([^()]+)\)$")

    def __init__(self, binary=_newest("MEETING_COPILOT_AGY", "agy")):
        self.binary = binary

    def discover(self, env=None):
        def body(binary):
            run = subprocess.run([str(binary), "models"], text=True, capture_output=True,
                                 timeout=DISCOVERY_TIMEOUT, check=False, env=env)
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
            return _available(self, [_model(base, item["label"], item["efforts"], (),
                                            "Antigravity does not report speed tiers")
                                     for base, item in grouped.items()])
        return _discovery(self, body)

    def call(self, choice, prompt, *, env, timeout, files=False, image=None, cwd=None, resume="", keep_session=False):
        model = f"{choice['model']}-{choice['effort']}" if choice.get("effort") else choice["model"]
        argv = [self.binary(), "--model", model, "--mode", "plan", "--sandbox", "--output-format", "stream-json",
                "--print-timeout", f"{int(timeout)}s"] + (["--conversation", resume] if resume else [])
        if image:
            prompt += f"\n\nThe screenshot is the image file {image}. View that one file; do not open anything else."
            cwd = cwd or Path(image).parent
        # ponytail: agy reads the prompt only from argv (Windows caps a command line at 32K chars).
        with _workdir(cwd, files) as directory:
            result = _run(argv + [f"--print={prompt}"], None, env, timeout + 15, directory)
        reported, outcome = model, {}
        for event in _json_lines(result.stdout):
            if event.get("event") == "init":
                reported = (event.get("init") or {}).get("model") or reported
            elif event.get("event") == "result":
                outcome = event.get("result") or {}
        text = str(outcome.get("response") or "").strip()
        if result.returncode or outcome.get("status") != "SUCCESS" or not text:
            raise RuntimeError(ai_failure(str(outcome.get("error") or result.stderr or result.stdout).strip()))
        return Reply(text, reported, outcome.get("conversation_id") or resume)


class OllamaAdapter:
    name, label = "ollama", "Ollama"

    def __init__(self, host=None):
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        if "://" not in self.host:
            self.host = "http://" + self.host

    def _request(self, path, payload=None, timeout=5):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.host + path, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def discover(self, env=None):
        try:
            tags = self._request("/api/tags", timeout=3)
        except (OSError, ValueError) as error:
            return _unavailable(self, f"Ollama is not running at {self.host}: {getattr(error, 'reason', error)}")

        def body(_):
            models = []
            for item in tags.get("models") or []:
                thinking = (self._request("/api/show", {"model": item["name"]}).get("thinking") or {})
                values = thinking.get("values") if isinstance(thinking, dict) else None
                efforts = [] if not values or values == [False] else \
                    [str(value).lower() if isinstance(value, bool) else str(value) for value in values]
                models.append(_model(item["name"], item["name"], efforts, (), "Ollama does not report speed tiers"))
            return _available(self, models, "local")
        return _discovery(self, body)

    def call(self, choice, prompt, *, env, timeout, files=False, image=None, cwd=None, resume="", keep_session=False):
        message = {"role": "user", "content": prompt}
        if image:
            message["images"] = [base64.b64encode(Path(image).read_bytes()).decode("ascii")]
        payload = {"model": choice["model"], "messages": [message], "stream": False}
        if choice.get("effort"):
            payload["think"] = {"true": True, "false": False}.get(choice["effort"], choice["effort"])
        try:
            reply = self._request("/api/chat", payload, timeout=timeout)
        except urllib.error.HTTPError as error:
            raise RuntimeError(ai_failure(error.read().decode("utf-8", "replace"))) from None
        except (OSError, ValueError) as error:
            raise RuntimeError(ai_failure(f"connection failed: {error}")) from None
        text = str((reply.get("message") or {}).get("content") or "").strip()
        if not text:
            raise RuntimeError(ai_failure(str(reply.get("error") or "empty reply")))
        return Reply(text, reply.get("model") or choice["model"], "")


def default_adapters():
    return [CodexAdapter(), ClaudeAdapter(), AntigravityAdapter(), OllamaAdapter()]


@contextmanager
def _file_lock(path):
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

    def purposes(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        section = data.get("ai") if isinstance(data, dict) else None
        purposes = section.get("purposes") if isinstance(section, dict) else None
        return purposes if isinstance(purposes, dict) else {}

    def set_purpose(self, purpose, choice):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with self.lock, _file_lock(self.path.with_name(self.path.name + ".lock")):
            try:
                text, mode = self.path.read_text(encoding="utf-8"), stat.S_IMODE(self.path.stat().st_mode)
            except FileNotFoundError:
                text, mode = None, 0o600
            try:
                data = {} if text is None else json.loads(text)
            except ValueError:
                raise ValueError(f"{self.path} is not valid JSON; fix it before saving AI choices") from None
            if not isinstance(data, dict):
                raise ValueError(f"{self.path} must hold a JSON object")
            section = data.get("ai") if isinstance(data.get("ai"), dict) else {}
            purposes = dict(section.get("purposes") or {})
            purposes[purpose] = choice
            data["ai"] = {**section, "purposes": purposes}
            handle, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".config.", suffix=".tmp")
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as stream:
                    stream.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
                os.chmod(temporary, mode)
                os.replace(temporary, self.path)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise


def _normal(choice):
    if not isinstance(choice, dict) or not all(isinstance(choice.get(key, ""), str) for key in CHOICE_KEYS):
        return None
    choice = {key: choice.get(key, "").strip() for key in CHOICE_KEYS}
    return choice if choice["provider"] and choice["model"] else None


def choice_problem(found, choice):
    """Why the provider, as discovered now, cannot run this choice ('' when it can)."""
    label = found.get("label") or choice["provider"]
    if found.get("state") != "available":
        return f"{label} is unavailable: {found.get('reason') or 'unknown reason'}"
    model = next((item for item in found.get("models", []) if item["id"] == choice["model"]), None)
    if model is None:
        return f"{label} does not offer the model {choice['model']} now. Choose a model again."
    if model["efforts"] and choice["effort"] not in model["efforts"]:
        return f"Choose one of the effort levels {label} offers for {choice['model']}."
    if not model["efforts"] and choice["effort"]:
        return f"{choice['model']} has no effort levels."
    if choice["speed"] and choice["speed"] not in [speed["id"] for speed in model["speeds"]]:
        return f"The chosen speed is not offered: {model['speed_reason'] or 'not listed by ' + label}"
    return ""


class AIService:
    def __init__(self, config_path, env, adapters=None, ttl=300):
        self.settings, self.env, self.ttl = AISettings(config_path), env, ttl
        self.adapters = {adapter.name: adapter for adapter in (adapters if adapters is not None else default_adapters())}
        self.cache, self.lock, self.provider_locks = {}, threading.Lock(), {}

    def providers(self):
        return [{"provider": name, "label": adapter.label} for name, adapter in self.adapters.items()]

    def options(self, provider, refresh=False):
        adapter = self.adapters.get(provider)
        if adapter is None:
            return {"provider": provider, "label": provider, "state": "unavailable",
                    "reason": "Unknown AI provider", "plan": "", "models": [], "current": {}}
        with self.lock:
            provider_lock = self.provider_locks.setdefault(provider, threading.Lock())
        with provider_lock:  # one discovery per provider at a time
            cached = self.cache.get(provider)
            ttl = self.ttl if cached and cached[1]["state"] == "available" else min(self.ttl, 30)
            if refresh or not cached or time.monotonic() - cached[0] > ttl:
                cached = (time.monotonic(), adapter.discover(self.env))
                self.cache[provider] = cached
            return cached[1]

    def status(self, purpose):
        stored = self.settings.purposes().get(purpose)
        choice = _normal(stored)
        if choice is None:
            return {"purpose": purpose, "state": "needs_choice", "choice": None,
                    "reason": "No AI provider and model chosen for this purpose yet"}
        problem = choice_problem(self.options(choice["provider"]), choice)
        return {"purpose": purpose, "state": "unavailable" if problem else "ready", "choice": choice, "reason": problem}

    def status_all(self):
        return {purpose: self.status(purpose) for purpose in PURPOSES}

    def save(self, purpose, choice):
        if purpose not in PURPOSES:
            raise ValueError("Unknown AI purpose")
        choice = _normal(choice)
        if choice is None:
            raise ValueError("Choose a provider and a model")
        problem = choice_problem(self.options(choice["provider"]), choice)
        if problem:
            raise ValueError(problem)
        self.settings.set_purpose(purpose, choice)
        return self.status(purpose)

    def choice_key(self, purpose):
        return json.dumps(_normal(self.settings.purposes().get(purpose)), sort_keys=True)

    def run(self, purpose, prompt, **options):
        status = self.status(purpose)
        if status["state"] == "needs_choice":
            raise RuntimeError("AI_CHOICE: Choose an AI provider and model for this task in Getting started, "
                               "then retry. Audio recording is independent.")
        if status["state"] != "ready":
            raise RuntimeError("AI_UNAVAILABLE: " + status["reason"])
        options.setdefault("env", self.env)
        options.setdefault("timeout", 120)
        return self.adapters[status["choice"]["provider"]].call(status["choice"], prompt, **options)
