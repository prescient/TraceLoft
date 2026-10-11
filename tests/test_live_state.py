import asyncio
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from web_app import create_app
from web_service import GolfService


class LiveStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')

    def tearDown(self):
        self.client.close()
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def test_idle_revision_does_not_read_attempts_or_compute_summary(self):
        class History(list):
            def __iter__(self):
                raise AssertionError('Idle update walked attempt history')

        summary = Mock(side_effect=AssertionError('Idle update calculated summary'))
        self.service.practice = SimpleNamespace(
            data=dict(id='fixture', ended=None, shots=History([{}] * 1000)), summary=summary
        )
        first = self.service.live_revision()
        for _ in range(10):
            self.assertEqual(self.service.live_revision(), first)
        self.service.capture['error'] = 'Source disconnected'
        self.assertEqual(self.service.live_revision()['revision'], first['revision'] + 1)
        summary.assert_not_called()
        self.service.practice = None

    def test_snapshot_and_database_updates_share_revision_and_epoch(self):
        first = self.service.snapshot()['live']
        self.assertEqual(self.service.live_revision(), first)
        with self.service.store.transaction():
            self.service.store.connection.execute(
                'INSERT INTO metadata VALUES(?,?)', ('test-live', 'updated')
            )
        second = self.service.snapshot()['live']
        self.assertEqual(second['epoch'], first['epoch'])
        self.assertEqual(second['revision'], first['revision'] + 1)
        self.assertEqual(self.service.live_revision(), second)

    def test_v2_socket_only_sends_notifications_and_idle_does_not_snapshot(self):
        with patch.object(self.service, 'snapshot', wraps=self.service.snapshot) as snapshot:
            with self.client.websocket_connect('ws://localhost/ws?protocol=2') as ws:
                initial = ws.receive_json()
                self.assertEqual(
                    initial, dict(type='state_changed', **self.service.live_revision())
                )
                time.sleep(0.65)
                snapshot.assert_not_called()
                self.service.capture['status'] = 'New status'
                changed = ws.receive_json()
                self.assertEqual(changed['revision'], initial['revision'] + 1)
                self.assertLess(len(str(changed)), 120)
                snapshot.assert_not_called()

    def test_legacy_socket_remains_compatible_but_sends_only_changes(self):
        with patch.object(self.service, 'snapshot', wraps=self.service.snapshot) as snapshot:
            with self.client.websocket_connect('ws://localhost/ws') as ws:
                first = ws.receive_json()
                self.assertIn('practice', first)
                time.sleep(0.65)
                self.assertEqual(snapshot.call_count, 1)
                self.service.capture['status'] = 'Changed'
                second = ws.receive_json()
                self.assertEqual(second['capture']['status'], 'Changed')
                self.assertEqual(snapshot.call_count, 2)
