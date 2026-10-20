import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from frame_relevance import frame_relevance


class FrameRelevanceTests(unittest.TestCase):
    def classify(self, answer):
        event = {"type": "item.completed", "item": {"type": "agent_message", "text": answer}}
        with patch("frame_relevance.subprocess.run", return_value=subprocess.CompletedProcess([], 0, json.dumps(event))):
            return frame_relevance(Path('/tmp/frame.jpg'), {}, {}, None, 'codex', {})

    def test_relevance_results_and_failures(self):
        self.assertTrue(self.classify('{"keep":true,"reason":"shared diagram"}')[0])
        self.assertFalse(self.classify('{"keep":false,"reason":"unrelated email"}')[0])
        self.assertFalse(self.classify('{"keep":"false"}')[0])
        self.assertFalse(self.classify('not JSON')[0])
        with patch("frame_relevance.subprocess.run", side_effect=subprocess.TimeoutExpired('codex', 45)):
            self.assertFalse(frame_relevance(Path('/tmp/frame.jpg'), {}, {}, None, 'codex', {})[0])
        self.assertEqual(frame_relevance(None, {"image_digest": "same"}, {}, {"image_digest": "same"}, None, {}), (False, 'duplicate'))

    def test_discard_removes_file_and_never_indexes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            helper = root / 'helper'
            helper.touch()
            frames = server.MeetingFrames(root / 'index.json')

            def run(command, **kwargs):
                if command[0] == '/usr/sbin/screencapture':
                    Path(command[-1]).write_bytes(b'x' * 11000)
                    return subprocess.CompletedProcess(command, 0, '')
                if len(command) == 1:
                    return subprocess.CompletedProcess(command, 0, '{"id":1,"title":"unrelated"}')
                return subprocess.CompletedProcess(command, 0, '[]')

            with patch.object(frames, '_active_recording_dir', return_value=root), \
                 patch.object(frames, '_speaker_from_frame', return_value=('', '')), \
                 patch.object(server, 'WINDOW_FINDER', helper), patch.object(server, 'FRAME_INSPECTOR', helper), \
                 patch.object(server.subprocess, 'run', side_effect=run), \
                 patch.object(server, 'frame_relevance', return_value=(False, 'unrelated')):
                self.assertTrue(frames.capture({'meeting_id': 'fixture'})['discarded'])
            self.assertEqual(frames.items, [])
            self.assertEqual(list((root / 'screenshots').iterdir()), [])
            self.assertFalse(frames.index_path.exists())


if __name__ == '__main__':
    unittest.main()
