"""Host checks: local by default, LAN names in LAN mode, and the owner's allowed_hosts.txt (D62)."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from web_app import create_app, extra_hosts
from web_service import GolfService


class AllowedHostsFileTests(unittest.TestCase):
    def test_reads_one_host_per_line_ignoring_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'allowed_hosts.txt'
            path.write_text('# comment\n\n96.61.155.11\n  Golf.Example.com  # sim screen\n')
            self.assertEqual(extra_hosts(path), ['96.61.155.11', 'golf.example.com'])
            self.assertEqual(extra_hosts(Path(root) / 'missing.txt'), [])


class HostCheckTests(unittest.TestCase):
    def test_public_address_needs_lan_mode_and_the_allow_list(self):
        with tempfile.TemporaryDirectory() as root:
            service = GolfService(root)
            with TestClient(create_app(service), base_url='http://localhost') as client:

                def status(host):
                    return client.get('/api/health', headers={'host': host}).status_code

                self.assertEqual(status('localhost:8765'), 200)
                self.assertEqual(status('96.61.155.11:8765'), 400)  # local mode: never
                service.access.update(
                    lan=True, addresses=['http://10.10.0.209:8765'], extra_hosts=[]
                )
                self.assertEqual(status('10.10.0.209:8765'), 200)
                self.assertEqual(status('96.61.155.11:8765'), 400)  # LAN mode, not listed
                service.access['extra_hosts'] = ['96.61.155.11']
                self.assertEqual(status('96.61.155.11:8765'), 200)
                self.assertEqual(status('evil.example:8765'), 400)  # other names stay refused


if __name__ == '__main__':
    unittest.main()
