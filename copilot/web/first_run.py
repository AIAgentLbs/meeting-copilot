"""Explicit first-run AI access checks."""
from __future__ import annotations

import json
import subprocess
import threading


def ai_failure(detail: str) -> str:
    text = detail.lower()
    if any(word in text for word in ('quota', 'usage limit', 'rate limit', '429', 'out of credit', 'limit reached')):
        return 'AI_LIMIT: Codex account limit reached. Check your plan or wait for the limit to reset, then retry. Audio recording is independent.'
    if any(word in text for word in ('unauthorized', '401', 'login', 'log in', 'authentication', 'sign in', 'token expired')):
        return 'AI_LOGIN: Sign in to Codex, then run Check AI again. Audio recording is independent.'
    if any(word in text for word in ('not found', 'no such file', 'not recognized')):
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
