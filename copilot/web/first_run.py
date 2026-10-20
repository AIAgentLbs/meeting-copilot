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


def ai_failure(detail: str) -> str:
    text = detail.lower()
    if any(word in text for word in ('quota', 'usage limit', 'rate limit', '429', 'out of credit', 'limit reached')):
        return 'AI_LIMIT: The AI account limit is reached. Check your plan or wait for the limit to reset, then retry. Audio recording is independent.'
    if any(word in text for word in ('unauthorized', '401', 'login', 'log in', 'authentication', 'sign in', 'token expired')):
        return 'AI_LOGIN: Sign in to the chosen AI provider, then run Check AI again. Audio recording is independent.'
    if 'model metadata' in text:
        return 'AI_UPDATE: The AI tool is too old for the chosen model. Update it or choose another model, then run Check AI again. Audio recording is independent.'
    if any(word in text for word in ('model is not supported', 'not supported when using', 'unsupported model')):
        return 'AI_MODEL: The AI provider rejected the chosen model. Your plan may not include it. Choose another model in Getting started. Audio recording is independent.'
    if any(word in text for word in ('no such file', 'command not found', 'not recognized', 'cannot find')):
        return 'AI_MISSING: The chosen AI tool is not installed. Install it and sign in, or choose another provider. Local recording and transcription do not need AI.'
    if any(word in text for word in ('timeout', 'timed out', 'network', 'connection', 'dns')):
        return 'AI_NETWORK: The AI service did not respond. Check your connection and retry. Audio recording is independent.'
    return 'AI_FAILED: The AI request failed. Run Check AI in Getting started, then retry your question. Audio recording is independent.'


PROBE = 'Reply with exactly READY. Do not inspect files or use tools.'


class AIReadiness:
    """Check AI: one tiny request per distinct configured choice, never meeting data."""
    def __init__(self, service):
        self.service = service
        self.lock = threading.Lock()
        self.result = {'state': 'unchecked', 'purposes': {},
                       'message': 'Installed tools do not prove account access. Check AI to send a short test request without meeting data.'}

    def snapshot(self):
        return dict(self.result)

    def check(self):
        if not self.lock.acquire(blocking=False):
            return {'state': 'checking', 'message': 'A check is already running.', 'purposes': {}}
        try:
            self.result = {'state': 'checking', 'message': 'Checking AI access for each task…', 'purposes': {}}
            tested, purposes = {}, {}
            for purpose, status in self.service.status_all().items():
                if status['state'] != 'ready':
                    purposes[purpose] = {'state': status['state'], 'message': status['reason'], 'model': ''}
                    continue
                key = json.dumps(status['choice'], sort_keys=True)
                if key not in tested:
                    try:
                        reply = self.service.run(purpose, PROBE, timeout=60)
                        ok = reply.text.strip().strip('.') == 'READY'
                        tested[key] = {'state': 'ready' if ok else 'error', 'model': reply.model,
                                       'message': 'AI answered successfully. Account limits still apply.' if ok
                                       else 'AI_FAILED: The model answered, but not as asked. Try another model.'}
                    except RuntimeError as error:
                        tested[key] = {'state': 'error', 'message': str(error), 'model': ''}
                purposes[purpose] = dict(tested[key])
            states = {item['state'] for item in purposes.values()}
            state = 'ready' if states == {'ready'} else 'error' if 'error' in states or 'unavailable' in states else 'needs_choice'
            first_problem = next((item['message'] for item in purposes.values() if item['state'] != 'ready'), '')
            self.result = {'state': state, 'purposes': purposes,
                           'message': 'AI answered successfully for every task. Account limits still apply.' if state == 'ready' else first_problem}
        finally:
            self.lock.release()
        return self.snapshot()
