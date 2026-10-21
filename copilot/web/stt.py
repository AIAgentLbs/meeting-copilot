"""One speech recognition choice (`stt.choice` in the shared config.json).

Options, downloads, checks and re-transcription all come from the capture binary
(`meetingcopilot stt-options|stt-download|stt-check|process`); this module holds no
engine, model or language ids. Contract: docs/specs/2026-10-20-no-hardcoded-models.md,
"Phase 3"; shared vocabulary: stt_vocabulary.json.
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ai_providers import _file_lock
from private_dirs import private_dir

OPTIONS_CONTRACT = "meetontrack.stt-options/1"
CHECK_CONTRACT = "meetontrack.stt-check/1"
CONFIG_PATH = ("stt", "choice")
CHOICE_KEYS = ("engine", "language", "model")
STATES = ("needs_choice", "ready", "unavailable")
LIVE_MODES = ("", "sliding_window", "streaming")
MODEL_ENTRY = ("free_text", "list")
AUTO_LANGUAGE = "auto"
DEFERRED_KEY = "transcription_deferred"
DEFERRED_KINDS = ("needs_choice", "network", "unavailable")  # written by the capture app, labelled by speech.js
DOWNLOAD_EVENTS = ("done", "error", "finished", "progress")
OPTIONS_TIMEOUT, CHECK_TIMEOUT = 60, 180
DEFERRED_LIMIT, JOB_LIMIT = 50, 20
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
WINDOWS = os.name == "nt"
WINDOWS_REASON = "Speech choice on Windows is not available yet (MEETONTRACK-69)"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write(path, text):
    """Private temp file in the same folder (0600 before any byte), fsync, rename over."""
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        if os.name != "nt":
            os.fchmod(handle, 0o600)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _tail(text, lines=20):
    return "\n".join(str(text or "").strip().splitlines()[-lines:])


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def normalize_local_files(options):
    """`download_bytes` (int >= 0, or null when unknown) and `found_elsewhere` ([{path, bytes}], reused
    by a verified clone) on every model and template; malformed values become unknown."""
    for engine in options.get("engines") or []:
        template = engine.get("model_template")
        for item in (engine.get("models") or []) + ([template] if isinstance(template, dict) else []):
            if not isinstance(item, dict):
                continue
            item["download_bytes"] = _count(item.get("download_bytes"))
            found = item.get("found_elsewhere")
            item["found_elsewhere"] = [{"path": entry["path"], "bytes": _count(entry.get("bytes"))}
                                       for entry in (found if isinstance(found, list) else [])
                                       if isinstance(entry, dict) and isinstance(entry.get("path"), str) and entry["path"]
                                       and _count(entry.get("bytes")) is not None]
    return options


def add_best_for(options):
    """Tags derived only from each model's own facts (never from ids or names)."""
    for engine in options.get("engines") or []:
        models = engine.get("models") or []
        latencies = [model["live_latency_ms"] for model in models
                     if model.get("live") and isinstance(model.get("live_latency_ms"), (int, float))]
        template = engine.get("model_template")
        for model in models + ([template] if isinstance(template, dict) else []):
            languages = model.get("languages") or []
            tags = {
                "live": model.get("live") in LIVE_MODES[1:],
                "lowest_latency": model is not template and bool(model.get("live")) and bool(latencies)
                                  and model.get("live_latency_ms") == min(latencies),
                "multilingual": model.get("auto_detect") is True or len(languages) > 1,
                "offline": engine.get("kind") == "local",
                "speakers": model.get("speakers") is True,
            }
            model["best_for"] = [tag for tag, on in tags.items() if on]
    return options


def complete_choice(choice):
    """The four keys as strings (stripped), or None. Values may not look like command-line flags."""
    if not isinstance(choice, dict) or set(choice) != set(CHOICE_KEYS):
        return None
    if not all(isinstance(choice[key], str) for key in CHOICE_KEYS):
        return None
    choice = {key: choice[key].strip() for key in CHOICE_KEYS}
    return None if any(value.startswith("-") for value in choice.values()) else choice


def choice_args(choice):
    return ["--engine", choice["engine"], "--model", choice["model"], "--language", choice["language"]]


def apply_download_event(job, event):
    """Fold one `stt-download --json` line into the job; unknown events are ignored."""
    kind = event.get("event") if isinstance(event, dict) else None
    if kind not in DOWNLOAD_EVENTS:
        return
    if kind == "progress":
        for key in ("item", "fraction", "phase", "completed_files", "total_files"):
            if key in event:
                job[key] = event[key]
    elif kind == "done":
        job.update(item=event.get("item", job["item"]), fraction=1.0)
    elif kind == "finished":
        job["state"] = "done" if event.get("ok") is True else "error"
    else:
        job.update(state="error", item=event.get("item", job["item"]),
                   message=str(event.get("message") or "download failed"))


def _no_windows_recorder(*args, **kwargs):
    raise OSError(WINDOWS_REASON)


class STTService:
    def __init__(self, config_path, binary, roots, runner=subprocess.run, popen=subprocess.Popen,
                 keys_dir=None, ttl=300):
        self.config_path, self.binary = Path(config_path), Path(binary)
        self.roots = roots if callable(roots) else (lambda: [Path(roots)])
        self.keys_dir = Path(keys_dir) if keys_dir else self.config_path.parent / "keys"
        self.runner, self.popen, self.ttl = runner, popen, ttl
        self.windows = WINDOWS
        if self.windows:
            # The Windows recorder has no stt-* commands yet and opens its window on any unknown
            # arguments, so nothing here may start it (MEETONTRACK-69).
            self.runner = self.popen = _no_windows_recorder
        self.lock, self.discovery_lock, self.write_lock = threading.Lock(), threading.Lock(), threading.Lock()
        self.adopting = threading.Lock()
        self.cache = None  # (monotonic time, result)
        self.checks, self.downloads_by_id, self.jobs_by_id = {}, {}, {}

    # Discovery ---------------------------------------------------------------
    def options(self, refresh=False):
        with self.discovery_lock:
            cached = self.cache
            if cached and not refresh and time.monotonic() - cached[0] < (self.ttl if cached[1]["ok"] else min(self.ttl, 30)):
                return cached[1]
            result = self._discover(refresh)
            self.cache = (time.monotonic(), result)
            return result

    def _discover(self, refresh):
        if self.windows:
            return {"ok": False, "error": WINDOWS_REASON}
        try:
            run = self.runner([str(self.binary), "stt-options", "--json", *(["--refresh"] if refresh else [])],
                              capture_output=True, text=True, timeout=OPTIONS_TIMEOUT)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"speech recognition options did not answer within {OPTIONS_TIMEOUT} s"}
        except OSError as error:
            return {"ok": False, "error": f"cannot run the recorder ({self.binary}): {error.strerror or error}"}
        if run.returncode != 0:
            return {"ok": False, "error": _tail(run.stderr, 3) or f"stt-options exited with code {run.returncode}"}
        try:
            parsed = json.loads(run.stdout)
        except ValueError:
            return {"ok": False, "error": "stt-options printed malformed JSON"}
        if not isinstance(parsed, dict) or parsed.get("contract") != OPTIONS_CONTRACT:
            return {"ok": False, "error": f"stt-options did not answer with contract {OPTIONS_CONTRACT}"}
        if not isinstance(parsed.get("engines"), list):
            return {"ok": False, "error": "stt-options listed no engines"}
        return {**add_best_for(normalize_local_files(parsed)), "ok": True}

    def invalidate(self):
        with self.discovery_lock:
            self.cache = None

    # The stored choice -------------------------------------------------------
    def stored(self):
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        section = data.get(CONFIG_PATH[0]) if isinstance(data, dict) else None
        choice = section.get(CONFIG_PATH[1]) if isinstance(section, dict) else None
        return choice if isinstance(choice, dict) else None

    def status(self):
        """State of the stored choice as the capture app reported it in the cached options;
        "" when the options for this exact choice have not been read yet."""
        stored = self.stored()
        choice = complete_choice({key: stored.get(key) for key in CHOICE_KEYS} if stored else None)  # extra keys ignored
        cached = self.cache[1] if self.cache else None
        block = (cached or {}).get("choice") or {}
        display_name = ""
        if self.windows:
            state, reason = "", WINDOWS_REASON
        elif choice is None or not all(choice[key] for key in ("engine", "model", "language")):
            state, reason = "needs_choice", "Choose speech recognition in Getting started."
            self._adopt_in_background()
        elif cached and cached.get("ok") and block.get("stored") == stored and block.get("state") in STATES:
            state, reason = block["state"], str(block.get("reason") or "")
            display_name = str(block.get("display_name") or "")  # the recorder's name for the model
            if state == "unavailable":
                self._adopt_in_background()  # a model downloaded since then clears it within 30 s
        else:
            state, reason = "", "Reading what the recorder offers…"
            self._adopt_in_background()  # also resolves a saved choice nobody opened Getting started for
        return {"choice": stored, "state": state, "reason": reason, "display_name": display_name,
                "deferred": self.deferred()}

    def _adopt_in_background(self):
        """`stt-options` adopts the model downloaded last when there is no choice yet (the capture
        app owns that rule) and says whether a saved one can run. Run it without holding up the
        caller, one at a time, at most every 30 s."""
        cached = self.cache
        if cached and time.monotonic() - cached[0] < 30 or not self.adopting.acquire(blocking=False):
            return

        def run():
            try:
                self.invalidate()
                self.options()
            finally:
                self.adopting.release()
        threading.Thread(target=run, daemon=True).start()

    def deferred(self):
        found = []
        for root in self.roots():
            try:
                folders = [path for path in Path(root).iterdir() if path.is_dir()]
            except OSError:
                continue
            for folder in folders:
                try:
                    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                mark = meta.get(DEFERRED_KEY) if isinstance(meta, dict) else None
                if isinstance(mark, dict) and not (folder / "transcript.json").exists():
                    found.append({"session": folder.name, "kind": str(mark.get("kind") or ""),
                                  "reason": str(mark.get("reason") or ""), "at": str(mark.get("at") or "")})
        return sorted(found, key=lambda item: item["session"], reverse=True)[:DEFERRED_LIMIT]

    def save_choice(self, choice):
        if not isinstance(choice, dict) or set(choice) != set(CHOICE_KEYS) or \
                not all(isinstance(choice[key], str) for key in CHOICE_KEYS):
            raise ValueError("Send exactly engine, model and language as text")
        choice = complete_choice(choice)
        if choice is None:
            raise ValueError("A speech recognition value may not start with '-'")
        options = self.options()
        if not options.get("ok"):
            raise ValueError(f"Speech recognition options are unavailable: {options.get('error')}")
        self._validate(options, choice)
        self._write_choice(choice)
        self.invalidate()  # the options' choice block describes the previous choice
        return self.status()

    @staticmethod
    def _validate(options, choice):
        engine = next((item for item in options["engines"] if item.get("id") == choice["engine"]), None)
        if engine is None:
            raise ValueError("Choose a speech recognition engine from the list")
        label = engine.get("label") or engine["id"]
        if not engine.get("available"):
            raise ValueError(f"{label} is unavailable: {engine.get('reason') or 'unknown reason'}")
        if engine.get("model_entry") == "free_text":
            if not choice["model"]:
                raise ValueError(f"Type a model id for {label}")
            facts = engine.get("model_template") or {}
        else:
            facts = next((item for item in engine.get("models") or [] if item.get("id") == choice["model"]), None)
            if facts is None:
                raise ValueError(f"{label} does not list the model {choice['model'] or '(none)'}; choose one from the list")
            if not facts.get("available", True):
                raise ValueError(f"{choice['model']} is unavailable: {facts.get('reason') or 'unknown reason'}")
        language = choice["language"]
        if not language:
            raise ValueError("Choose a language")
        if language == AUTO_LANGUAGE:
            if facts.get("auto_detect") is not True:
                raise ValueError(f"{choice['model']} does not report automatic language detection; choose a language")
        elif facts.get("language_entry") != "free_text" and language not in (facts.get("languages") or []):
            raise ValueError(f"{choice['model']} does not list the language {language}")

    def _write_choice(self, choice):
        """Read-modify-replace under config.json.lock, same protocol as AISettings: missing file =
        empty object, malformed or not an object = refuse; every other key is kept."""
        private_dir(self.config_path.parent)
        with self.write_lock, _file_lock(self.config_path.with_name(self.config_path.name + ".lock")):
            try:
                text = self.config_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                text = None
            try:
                data = {} if text is None else json.loads(text)
            except ValueError:
                raise ValueError(f"{self.config_path} is not valid JSON; fix it before saving speech recognition") from None
            if not isinstance(data, dict):
                raise ValueError(f"{self.config_path} must hold a JSON object")
            section = data.get(CONFIG_PATH[0]) if isinstance(data.get(CONFIG_PATH[0]), dict) else {}
            data[CONFIG_PATH[0]] = {**section, CONFIG_PATH[1]: choice}
            _atomic_write(self.config_path, json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    # API keys ----------------------------------------------------------------
    def save_key(self, engine_id, key):
        """Writes keys/<engine> (the file the capture app reads). The key is never logged or returned."""
        options = self.options()
        engine = next((item for item in options.get("engines") or [] if item.get("id") == engine_id), None)
        if engine is None or engine.get("needs_key") is not True or not SAFE_ID.match(str(engine_id)):
            raise ValueError("This speech recognition engine takes no API key")
        key = key.strip() if isinstance(key, str) else ""
        if not key or any(character.isspace() for character in key):
            raise ValueError("Paste the API key as one line")
        private_dir(self.keys_dir)
        _atomic_write(self.keys_dir / engine_id, key)
        self.invalidate()

    # Check -------------------------------------------------------------------
    def check(self, choice=None):
        args = [str(self.binary), "stt-check", "--json"]
        if choice is not None:
            choice = complete_choice(choice)
            if choice is None:
                raise ValueError("Check takes engine, model and language, or nothing")
            args += choice_args(choice)
        try:
            run = self.runner(args, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
            result = json.loads(run.stdout)
            if not isinstance(result, dict) or result.get("contract") != CHECK_CONTRACT:
                raise ValueError
        except subprocess.TimeoutExpired:
            result = {"ok": False, "error": f"the check did not finish within {CHECK_TIMEOUT} s"}
        except OSError as error:
            result = {"ok": False, "error": f"cannot run the recorder ({self.binary}): {error.strerror or error}"}
        except ValueError:
            result = {"ok": False, "error": _tail(run.stderr, 3) or "stt-check printed no result"}
        result = {"contract": CHECK_CONTRACT, "choice": choice or self.stored(), "steps": [], "model_used": "",
                  "error": "", **result, "checked_at": _now()}
        with self.lock:
            self.checks[json.dumps(result["choice"], sort_keys=True)] = result
        return result

    def last_check(self):
        with self.lock:
            return self.checks.get(json.dumps(self.stored(), sort_keys=True))

    # Downloads ---------------------------------------------------------------
    def start_download(self, model_id):
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("Choose a model to download")
        model_id = model_id.strip()
        if model_id.startswith("-"):
            raise ValueError("A model id may not start with '-'")
        with self.lock:
            running = next((job for job in self.downloads_by_id.values()
                            if job["model"] == model_id and job["state"] == "running"), None)
            if running:
                return dict(running)
            job = {"id": uuid.uuid4().hex[:12], "model": model_id,
                   "state": "running", "item": "model", "fraction": 0.0, "phase": "", "completed_files": 0,
                   "total_files": 0, "message": "", "started_at": _now(), "finished_at": ""}
            self.downloads_by_id[job["id"]] = job
        args = [str(self.binary), "stt-download", "--model", model_id, "--json"]
        threading.Thread(target=self._download, args=(job, args), daemon=True).start()
        return dict(job)

    def _download(self, job, args):
        last_text = ""
        try:
            process = self.popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    last_text = line.strip() or last_text
                    continue
                with self.lock:
                    apply_download_event(job, event)
            code = process.wait()
        except OSError as error:
            code, last_text = -1, f"cannot run the recorder ({self.binary}): {error.strerror or error}"
        with self.lock:
            if job["state"] == "running":
                job["state"] = "done" if code == 0 else "error"
            if job["state"] == "error" and not job["message"]:
                job["message"] = last_text or f"stt-download exited with code {code}"
            job["finished_at"] = _now()
        self.invalidate()  # downloaded state changed

    def downloads(self):
        with self.lock:
            jobs = sorted(self.downloads_by_id.values(), key=lambda job: job["started_at"], reverse=True)
            return [dict(job) for job in jobs[:JOB_LIMIT]]

    # Re-transcription --------------------------------------------------------
    def session_dir(self, session):
        name = session if isinstance(session, str) else ""
        if not name or name in {".", ".."} or name != Path(name).name or "\\" in name or name.startswith("-"):
            raise ValueError("Unknown recording")
        for root in self.roots():
            folder = Path(root) / name
            if folder.is_dir() and (folder / "meta.json").is_file() and folder.resolve().parent == Path(root).resolve():
                return folder
        raise ValueError("Unknown recording")

    def retranscribe(self, session, choice=None):
        folder = self.session_dir(session)
        args = [str(self.binary), "process", str(folder), "--again"]
        if choice is not None:
            choice = complete_choice(choice)
            if choice is None:
                raise ValueError("A one-run choice needs engine, model and language")
            args += choice_args(choice)
        with self.lock:
            running = next((job for job in self.jobs_by_id.values()
                            if job["session"] == folder.name and job["state"] == "running"), None)
            if running:
                return dict(running)
            job = {"id": uuid.uuid4().hex[:12], "session": folder.name, "choice": choice, "state": "running",
                   "exit_code": None, "stderr": "", "started_at": _now(), "finished_at": ""}
            self.jobs_by_id[job["id"]] = job
        threading.Thread(target=self._retranscribe, args=(job, args), daemon=True).start()
        return dict(job)

    def _retranscribe(self, job, args):
        # ponytail: no timeout, a long meeting can take a long time to transcribe
        try:
            run = self.runner(args, capture_output=True, text=True)
            # `process` explains a refusal or failure on stdout, often with stderr empty.
            code, stderr = run.returncode, _tail(run.stderr) or ("" if run.returncode == 0 else _tail(run.stdout))
        except OSError as error:
            code, stderr = -1, f"cannot run the recorder ({self.binary}): {error.strerror or error}"
        with self.lock:
            job.update(state="done" if code == 0 else "error", exit_code=code, stderr=stderr, finished_at=_now())

    def jobs(self):
        with self.lock:
            jobs = sorted(self.jobs_by_id.values(), key=lambda job: job["started_at"], reverse=True)
            return [dict(job) for job in jobs[:JOB_LIMIT]]
