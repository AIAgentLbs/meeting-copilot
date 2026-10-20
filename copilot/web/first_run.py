"""Explicit first-run AI access checks."""
from __future__ import annotations

from pathlib import Path
import re
import struct
import subprocess
import tempfile
import threading
import uuid
import zlib


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
UNCHECKED = 'Installed tools do not prove account access. Check AI to send a short test request without meeting data.'


def probe_png(path, rgb=(220, 30, 30), size=16):
    """A solid-colour PNG for the image probe, written with the standard library."""
    row = b'\x00' + bytes(rgb) * size
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(row * size)) + chunk(b'IEND', b''))


class AIReadiness:
    """Check AI: one purpose-appropriate test request per task, never meeting data.
    A result belongs to the exact choice and executable it tested (the ticket key)."""
    def __init__(self, service):
        self.service = service
        self.lock = threading.Lock()
        self.results = {}  # purpose -> (ticket key, result)

    def snapshot(self):
        purposes = {}
        for purpose, ticket in self.service.tickets().items():
            done = self.results.get(purpose)
            if ticket.state != 'ready':
                purposes[purpose] = {'state': ticket.state, 'message': ticket.reason, 'model': ''}
            elif done and done[0] == ticket.key:
                purposes[purpose] = dict(done[1])
            else:
                purposes[purpose] = {'state': 'unchecked', 'model': '',
                                     'message': 'Not checked with this choice yet. Run Check AI.'}
        if self.lock.locked():
            return {'state': 'checking', 'purposes': purposes, 'message': 'Checking AI access for each task...'}
        states = {item['state'] for item in purposes.values()}
        state = ('ready' if states == {'ready'} else 'error' if states & {'error', 'unavailable'}
                 else 'needs_choice' if 'needs_choice' in states else 'unchecked')
        bad = {'error', 'unavailable'} if state == 'error' else {state}
        message = ('AI answered successfully for every task. Account limits still apply.' if state == 'ready'
                   else UNCHECKED if state == 'unchecked'
                   else next(item['message'] for item in purposes.values() if item['state'] in bad))
        return {'state': state, 'purposes': purposes, 'message': message}

    def check(self):
        if not self.lock.acquire(blocking=False):
            return self.snapshot()
        try:
            for purpose, ticket in self.service.tickets().items():
                if ticket.state == 'ready':
                    self.results[purpose] = (ticket.key, self._probe(purpose, ticket))
        finally:
            self.lock.release()
        return self.snapshot()

    def _probe(self, purpose, ticket):
        """Text probe, an image probe for screenshots, a file probe for repository reading."""
        adapter = self.service.adapters[ticket.choice['provider']]
        with tempfile.TemporaryDirectory(prefix='meetontrack-check-') as directory:
            prompt, expect, options = PROBE, 'READY', {}
            if purpose == 'frame_relevance':
                options['image'] = Path(directory) / 'probe.png'
                probe_png(options['image'])
                prompt, expect = 'What single colour fills this image? Reply with one lowercase English word.', 'red'
            elif purpose == 'live_analysis' and getattr(adapter, 'reads_files', False):
                expect = 'probe' + uuid.uuid4().hex[:8]
                (Path(directory) / 'probe.txt').write_text(expect, encoding='utf-8')
                options['roots'] = [directory]
                prompt = (f'Read the file {Path(directory) / "probe.txt"} and reply with exactly the one word it '
                          'contains. Do not read anything else.')
            try:
                reply = self.service.run(purpose, prompt, ticket=ticket, timeout=90, **options)
            except RuntimeError as error:
                return {'state': 'error', 'message': str(error), 'model': ''}
        if expect.lower() not in reply.text.lower():
            return {'state': 'error', 'model': reply.model,
                    'message': 'AI_FAILED: The model answered, but not as asked. Try another model.'}
        return {'state': 'ready', 'model': reply.model,
                'message': 'AI answered successfully. Account limits still apply.'}
