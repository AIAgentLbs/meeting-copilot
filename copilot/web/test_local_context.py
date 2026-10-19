import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_context import LocalContext


class LocalContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'Documents'
        self.folder.mkdir()
        self.provider = LocalContext(self.root / 'preferences.json')

    def test_optin_paths_only_fresh_reads_and_disconnect(self):
        file = self.folder / 'notes.md'
        file.write_text('Acme supports CSV')
        with patch.object(self.provider, 'search') as search:
            self.assertEqual(self.provider.augment('Acme', '', lambda _: self.fail()), '')
            search.assert_not_called()
        rows = self.provider.add(str(self.folder))
        self.assertEqual(self.provider.add(str(self.folder)), rows)
        self.assertNotIn('supports', self.provider.preferences.read_text())
        self.assertEqual(self.provider.preferences.stat().st_mode & 0o777, 0o600)
        plan = lambda _: '{"query":"Acme"}'
        self.assertIn('CSV', self.provider.augment('Acme', '', plan))
        file.write_text('Acme supports PDF')
        result = self.provider.augment('Acme', '', plan)
        self.assertIn('PDF', result)
        self.assertNotIn('CSV', result)
        generation = self.provider.generation()
        self.provider.remove(rows[0]['id'])
        self.assertNotEqual(generation, self.provider.generation())
        self.assertEqual(self.provider.augment('Acme', '', plan), '')
        self.assertEqual(file.read_text(), 'Acme supports PDF')

    def test_hidden_secrets_symlinks_and_unsupported_files_are_skipped(self):
        self.provider.add(str(self.folder))
        for name in ['.hidden.md', 'credentials.txt', 'private-key.md', 'data.xlsx']:
            (self.folder / name).write_text('Acme forbidden')
        outside = self.root / 'outside.txt'
        outside.write_text('Acme forbidden')
        (self.folder / 'link.txt').symlink_to(outside)
        hidden = self.folder / '.ssh'
        hidden.mkdir()
        (hidden / 'other.md').write_text('Acme forbidden')
        (self.folder / 'allowed.md').write_text('Acme allowed')
        result = self.provider.search('Acme')
        self.assertEqual(len(result['items']), 1)
        self.assertEqual(result['items'][0]['line'], 1)
        self.assertNotIn('forbidden', str(result))

    def test_selection_validation(self):
        for value in ('', '.', '/', str(Path.home()), None, 1):
            with self.assertRaises((ValueError, OSError)):
                self.provider.add(value)
        with self.assertRaises(ValueError):
            self.provider.add(str(self.root / 'missing'))

    def test_search_limits_and_missing_source(self):
        self.provider.add(str(self.folder))
        (self.folder / 'large.md').write_text('Acme ' * 50001)
        self.assertTrue(self.provider.search('Acme')['limited'])
        (self.folder / 'large.md').unlink()
        self.folder.rmdir()
        self.assertEqual(self.provider.search('Acme')['coverage'][0]['state'], 'unavailable')

    def test_disconnect_during_query_discards_result(self):
        row = self.provider.add(str(self.folder))[0]
        (self.folder / 'notes.md').write_text('Acme private')
        def planner(_):
            self.provider.remove(row['id'])
            return '{"query":"Acme"}'
        self.assertEqual(self.provider.augment('Acme', '', planner), '')

    def test_native_chooser_cancel_does_not_connect(self):
        with patch('local_context.subprocess.run') as run:
            run.return_value.returncode = 1
            run.return_value.stdout = ''
            self.assertEqual(self.provider.choose(), '')
        self.assertEqual(self.provider.snapshot(), [])


if __name__ == '__main__':
    unittest.main()
