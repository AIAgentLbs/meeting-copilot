"""Explicit first-run AI access checks."""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading


def pick_codex(candidates, runner=None):
    """Return the existing candidate reporting the highest `codex --version` (first existing if none answer)."""
    existing = []
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and Path(candidate).resolve() not in {p.resolve() for p in existing}:
            existing.append(Path(candidate))
    best, best_version = (existing or [None])[0], ()
    for candidate in existing:
        try:
            run = (runner or subprocess.run)([str(candidate), '--version'], text=True, capture_output=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        match = re.search(r'\d+(?:\.\d+)+', run.stdout or '')
        version = tuple(map(int, match.group().split('.'))) if run.returncode == 0 and match else ()
        if version > best_version:
            best, best_version = candidate, version
    return best


@lru_cache(maxsize=1)
def resolve_codex():
    """One Codex binary for every caller: env override, else the newest installed CLI."""
    if os.environ.get('MEETING_COPILOT_CODEX'):
        return Path(os.environ['MEETING_COPILOT_CODEX'])
    home = Path.home()
    return pick_codex([home / '.codex/packages/standalone/current/bin/codex', home / '.local/bin/codex',
                       shutil.which('codex'), '/opt/homebrew/bin/codex', '/usr/local/bin/codex']) or Path('/usr/local/bin/codex')


class LazyCodex:
    """Resolves the Codex binary on first str()/fspath use, so imports never probe `--version`."""
    def __str__(self):
        return str(resolve_codex())
    __fspath__ = __str__


CODEX = LazyCodex()


def ai_failure(detail: str) -> str:
    text = detail.lower()
    if any(word in text for word in ('quota', 'usage limit', 'rate limit', '429', 'out of credit', 'limit reached')):
        return 'AI_LIMIT: Codex account limit reached. Check your plan or wait for the limit to reset, then retry. Audio recording is independent.'
    if any(word in text for word in ('unauthorized', '401', 'login', 'log in', 'authentication', 'sign in', 'token expired')):
        return 'AI_LOGIN: Sign in to Codex, then run Check AI again. Audio recording is independent.'
    if 'model metadata' in text:
        return 'AI_UPDATE: Codex is installed but too old for the required model. Update Codex, then run Check AI again. Audio recording is independent.'
    if any(word in text for word in ('model is not supported', 'not supported when using codex', 'unsupported model')):
        return 'AI_MODEL: Codex rejected the required model. Update Codex; if it is already up to date, your Codex account plan may not include this model. Audio recording is independent.'
    if any(word in text for word in ('no such file', 'command not found', 'not recognized', 'cannot find')):
        return 'AI_MISSING: Install Codex and sign in, then run Check AI again. Local recording and transcription do not need Codex.'
    if any(word in text for word in ('timeout', 'timed out', 'network', 'connection', 'dns')):
        return 'AI_NETWORK: The AI service did not respond. Check your connection and retry. Audio recording is independent.'
    return 'AI_FAILED: The AI request failed. Run Check AI in Getting started, then retry your question. Audio recording is independent.'


class AIReadiness:
    def __init__(self, executable, env, runner=subprocess.run):
        self.executable, self.env, self.runner = executable, env, runner
        self.lock = threading.Lock()
        self.result = {'state': 'unchecked', 'message': 'Installed tools do not prove account access. Check AI to send a short test request without meeting data.'}

    def snapshot(self):
        return dict(self.result)

    def check(self):
        if not self.lock.acquire(blocking=False):
            return {'state': 'checking', 'message': 'A check is already running.'}
        try:
            self.result = {'state': 'checking', 'message': 'Checking Codex account and model access…'}
            run = self.runner([str(self.executable), '--model', 'gpt-6.1-sol', '--ask-for-approval', 'never',
                               'exec', '--ignore-user-config', '--ephemeral', '--sandbox', 'read-only',
                               '--skip-git-repo-check', '--json', '-'],
                              input='Reply with exactly READY. Do not inspect files or use tools.',
                              text=True, capture_output=True, timeout=40, check=False, env=self.env)
            ready = False
            for line in run.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                item = event.get('item', {})
                ready |= event.get('type') == 'item.completed' and item.get('type') == 'agent_message' and item.get('text', '').strip() == 'READY'
            self.result = {'state': 'ready', 'message': 'AI answered successfully. Account limits still apply.'} if ready and run.returncode == 0 else {
                'state': 'error', 'message': ai_failure(run.stderr + '\n' + run.stdout)}
        except (OSError, subprocess.TimeoutExpired) as error:
            self.result = {'state': 'error', 'message': ai_failure(str(error))}
        finally:
            self.lock.release()
        return self.snapshot()
