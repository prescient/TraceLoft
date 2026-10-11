import asyncio
import tempfile
import unittest
from unittest.mock import patch

from web_service import GolfService


PUTTING = dict(drill='Pace consistency', target=4, speed_tolerance=0.3, angle_tolerance=1, repetitions=5)


class MutationRollbackTests(unittest.TestCase):
    """A failed save must leave the live session matching SQLite."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.session_id = self.service.create_practice(dict(PUTTING))['id']

    def tearDown(self):
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def saved(self):
        return self.service.store.load_session(self.session_id)

    def test_finish_rolls_back_memory_when_save_raises_value_error(self):
        with patch.object(self.service.practice, 'save', side_effect=ValueError('rejected')):
            with self.assertRaises(ValueError):
                self.service.change_practice(self.session_id, 'finish')
        self.assertIsNone(self.service.practice.data['ended'])
        self.assertIsNone(self.saved()['ended'])

    def test_finish_rolls_back_memory_for_unexpected_errors(self):
        with patch.object(self.service.practice, 'save', side_effect=KeyError('bug')):
            with self.assertRaises(KeyError):
                self.service.change_practice(self.session_id, 'abandon')
        self.assertIsNone(self.service.practice.data['ended'])
        self.assertFalse(self.service.practice.data.get('abandoned', False))
        self.assertIsNotNone(self.service.practice)

    def test_rollback_also_undoes_database_writes_in_the_same_change(self):
        store = self.service.store
        before = store.connection.execute('SELECT count(*) FROM audit_events').fetchone()[0]

        def fail_after_write():
            store.audit(self.session_id, 'test_partial_write', {})
            raise ValueError('later failure')

        with self.assertRaises(ValueError), self.service._changing(self.service.practice):
            self.service.practice.data['ended'] = 'now'
            fail_after_write()
        self.assertIsNone(self.service.practice.data['ended'])
        after = store.connection.execute('SELECT count(*) FROM audit_events').fetchone()[0]
        self.assertEqual(after, before)

    def test_target_change_retries_pending_saves_before_refusing(self):
        self.service.change_practice(self.session_id, 'abandon')
        self.service.create_practice(
            dict(drill='Driving range', range_target=150, range_width=30, range_depth=20)
        )
        range_id = self.service.practice.data['id']
        # A saveable queued receipt previously blocked the change until the 5 s retry loop ran.
        self.service.pending.append(dict(kind='record', result='logged', vals={}, seq=1))
        self.service.target_range(range_id, 160, 30, 20)
        self.assertFalse(self.service.pending)
        self.assertEqual(self.service.practice.data['range_target'], 160)
        self.assertEqual(self.service.store.load_session(range_id)['range_target'], 160)


if __name__ == '__main__':
    unittest.main()
