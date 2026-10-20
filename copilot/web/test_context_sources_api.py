import http.client
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import server
from local_context import LocalContext


class ContextSourcesAPITests(unittest.TestCase):
    def test_connect_disconnect_validation_and_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'project'
            folder.mkdir()
            provider = LocalContext(root / 'sources.json')
            with patch.object(server, 'LOCAL_CONTEXT', provider):
                httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
                worker = threading.Thread(target=httpd.serve_forever, daemon=True)
                worker.start()
                def post(path, payload, origin=None):
                    connection = http.client.HTTPConnection('127.0.0.1', httpd.server_port, timeout=3)
                    headers = {'Content-Type': 'application/json'}
                    if origin:
                        headers['Origin'] = origin
                    connection.request('POST', path, json.dumps(payload), headers)
                    response = connection.getresponse()
                    status, body = response.status, response.read()
                    connection.close()
                    return status, body
                try:
                    self.assertEqual(post('/api/context-folders/add', {'path': str(folder)}, 'https://example.test')[0], 403)
                    self.assertEqual(provider.snapshot(), [])
                    self.assertEqual(post('/api/context-folders/add', {'path': 'relative'})[0], 400)
                    status, body = post('/api/context-folders/add', {'path': str(folder)})
                    self.assertEqual(status, 200)
                    identity = json.loads(body)['folders'][0]['id']
                    self.assertEqual(post('/api/context-folders/remove', {'id': identity})[0], 200)
                    self.assertEqual(provider.snapshot(), [])
                    self.assertTrue(folder.exists())
                    self.assertEqual(post('/api/context-documents/add', {'name': 'notes.md', 'data': 'abc'})[0], 404)
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    worker.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
