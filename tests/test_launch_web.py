"""Service identity compatibility prevents a second server during a rename."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from launch_web import ready


class LauncherIdentityTests(unittest.TestCase):
    def test_recognizes_current_and_already_running_legacy_service(self):
        for name in ('TraceLoft', 'GolfData'):
            with (
                self.subTest(name=name),
                patch(
                    'launch_web.urllib.request.urlopen',
                    return_value=io.BytesIO(('{"app":"' + name + '"}').encode()),
                ),
            ):
                self.assertTrue(ready(8765))

    def test_does_not_recognize_other_services_or_invalid_responses(self):
        for body in (b'{"app":"Other"}', b'{}', b'not json'):
            with (
                self.subTest(body=body),
                patch('launch_web.urllib.request.urlopen', return_value=io.BytesIO(body)),
            ):
                self.assertFalse(ready(8765))

    def test_unavailable_service_is_not_ready(self):
        with patch('launch_web.urllib.request.urlopen', side_effect=OSError):
            self.assertFalse(ready(8765))


class RuntimeFileOwnershipTests(unittest.TestCase):
    """Only the default-database service may write or remove web_runtime.json."""

    def run_main(self, root, environ):
        import web_app

        service = MagicMock()
        service.store.connection.execute.return_value.fetchone.return_value = None
        seen = {}

        def run():
            seen['during'] = (Path(root) / 'web_runtime.json').exists()

        server = MagicMock()
        server.run.side_effect = run
        with (
            patch.object(web_app, 'ROOT', Path(root)),
            patch.dict('os.environ', environ, clear=False),
            patch.object(web_app, 'GolfService', return_value=service),
            patch.object(web_app, 'create_app', return_value=MagicMock()),
            patch('uvicorn.Server', return_value=server),
            patch('uvicorn.Config'),
            patch('sys.argv', ['web_app.py', '--port', '8799']),
            patch('builtins.print'),
        ):
            web_app.main()
        return seen['during'], (Path(root) / 'web_runtime.json').exists()

    def test_isolated_instance_never_touches_the_runtime_file(self):
        with tempfile.TemporaryDirectory() as root:
            existing = Path(root) / 'web_runtime.json'
            existing.write_text('{"pid": 16388, "port": 8765, "lan": false}')
            during, after = self.run_main(
                root, {'GOLFDATA_DATABASE': str(Path(root) / 'qa.sqlite3')}
            )
            self.assertTrue(during and after)
            self.assertEqual(existing.read_text(), '{"pid": 16388, "port": 8765, "lan": false}')

    def test_default_database_service_writes_then_removes_its_own_record(self):
        import os

        environ = {k: v for k, v in os.environ.items() if k != 'GOLFDATA_DATABASE'}
        with tempfile.TemporaryDirectory() as root, patch.dict('os.environ', environ, clear=True):
            during, after = self.run_main(root, {})
        self.assertTrue(during)
        self.assertFalse(after)
