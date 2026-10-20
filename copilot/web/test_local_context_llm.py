import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server
from local_context import LocalContext


class LocalContextLLMTests(unittest.TestCase):
    def test_failed_cli_must_not_be_reported_as_success_after_partial_text(self):
        from test_ai_providers import chosen_codex
        with tempfile.TemporaryDirectory() as directory, chosen_codex(directory, server):
            session = server.CodexSession(Path(directory) / 'session.json')
            import ai_providers
            result = ai_providers.Result(1, '{"type":"item.completed","item":{"type":"agent_message","text":"partial"}}\n',
                                         'usage limit reached')
            with patch.object(ai_providers, '_run', return_value=result):
                with self.assertRaisesRegex(RuntimeError, 'AI_LIMIT'):
                    session._run_ai('synthetic')

    def test_folder_search_without_git_and_disconnect_resets_ai_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'project'
            folder.mkdir()
            (folder / 'notes.md').write_text('Acme supports CSV')
            provider = LocalContext(root / 'folders.json')
            identity = provider.add(str(folder))[0]['id']
            session = server.CodexSession(root / 'session.json')
            seen = []
            def model(prompt, planning=False):
                if planning:
                    return '{"query":"Acme"}'
                seen.append((prompt, session.thread_id))
                session.thread_id = 'synthetic-thread'
                return 'CSV'
            with patch.object(server, 'LOCAL_CONTEXT', provider), patch.object(server.GOOGLE_CONTEXT, 'augment', return_value=''), patch.object(session, '_run_ai', side_effect=model):
                session.ask('What can Acme export?', '', 'test', 'one', {'repositories': []})
                self.assertIn('Acme supports CSV', seen[-1][0])
                self.assertIn('notes.md', seen[-1][0])
                provider.remove(identity)
                session.ask('Next question', '', 'test', 'one', {'repositories': []})
                self.assertNotIn('Acme supports CSV', seen[-1][0])
                self.assertEqual(seen[-1][1], '')


if __name__ == '__main__':
    unittest.main()
