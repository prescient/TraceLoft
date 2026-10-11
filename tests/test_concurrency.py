"""The event loop must never wait for a long write transaction on another thread."""

import asyncio
import tempfile
import threading
import unittest
import zipfile
import io
from unittest.mock import patch

from domain_schema import read_session
from web_service import GolfService


PUTTING = dict(
    drill='Pace consistency', target=4, speed_tolerance=0.3, angle_tolerance=1, repetitions=20
)


def putt(seq):
    return dict(
        session_id='fixture',
        seq=seq,
        result='validated',
        vals=dict(ball_speed=4.0 + seq / 100, launch_dir=0.2, launch_ang=1.5),
    )


def completes(function, timeout=5):
    """Run function on a watchdog thread; return (finished, value, error)."""
    outcome = {}

    def run():
        try:
            outcome['value'] = function()
        except BaseException as exc:  # reported to the test, not swallowed
            outcome['error'] = exc

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    return not thread.is_alive(), outcome.get('value'), outcome.get('error')


class WriterLockIndependenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.store = self.service.store
        self.service.create_practice(dict(PUTTING))
        for seq in range(3):
            self.service.practice.add(putt(seq))
        self.release = threading.Event()
        self.entered = threading.Event()
        self.writer = None

    def tearDown(self):
        self.release.set()
        if self.writer:
            self.writer.join(10)
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def hold_write_transaction(self):
        def hold():
            with self.store.transaction():
                self.store.connection.execute(
                    "INSERT INTO metadata VALUES('uncommitted-probe','1')"
                )
                self.entered.set()
                self.release.wait(20)

        self.writer = threading.Thread(target=hold, daemon=True)
        self.writer.start()
        self.assertTrue(self.entered.wait(5))

    def test_reads_live_state_and_backups_proceed_while_another_thread_writes(self):
        before = self.service.live_revision()
        self.hold_write_transaction()
        operations = dict(
            live_revision=self.service.live_revision,
            snapshot=self.service.snapshot,
            sessions=self.service.sessions,
            analysis=lambda: self.store.analysis(dict(mode='real')),
            calculation_batches=self.store.calculation_batches,
            export=self.store.export,
            backup=self.store.backup,
        )
        results = {}
        for name, operation in operations.items():
            finished, value, error = completes(operation)
            self.assertTrue(finished, f'{name} waited for the writer lock')
            self.assertIsNone(error, f'{name} failed: {error!r}')
            results[name] = value
        # Uncommitted work is neither announced nor visible to snapshot readers.
        self.assertEqual(results['live_revision'], before)
        self.assertEqual(len(results['sessions']), 1)
        self.assertEqual(results['sessions'][0]['captured'], 3)
        with zipfile.ZipFile(io.BytesIO(results['export'])) as archive:
            self.assertIn('shots.csv', archive.namelist())
        self.assertTrue(results['backup'].exists())
        self.release.set()
        self.writer.join(10)
        self.assertEqual(self.service.live_revision()['revision'], before['revision'] + 1)

    def test_reads_inside_own_transaction_still_see_uncommitted_rows(self):
        with self.store.transaction():
            self.store.connection.execute("INSERT INTO metadata VALUES('own-write','1')")
            with self.store.reading() as connection:
                row = connection.execute(
                    "SELECT value FROM metadata WHERE key='own-write'"
                ).fetchone()
            self.assertEqual(row[0], '1')
            self.store.connection.execute("DELETE FROM metadata WHERE key='own-write'")

    def test_post_session_backup_runs_off_the_event_loop(self):
        started, release = threading.Event(), threading.Event()
        original = self.store.backup

        def slow_backup(*args, **kwargs):
            started.set()
            release.wait(10)
            return original(*args, **kwargs)

        async def finish_session():
            with patch.object(self.store, 'backup', side_effect=slow_backup):
                self.service.change_practice(self.service.practice.data['id'], 'finish')
                # The loop is free while the copy is still in progress.
                self.assertTrue(await asyncio.to_thread(started.wait, 5))
                self.assertTrue(any(t.is_alive() for t in self.store._background))
                release.set()
                await asyncio.to_thread(self.store.wait_for_background)

        asyncio.run(finish_session())
        self.assertIsNotNone(self.service.practice.data['ended'])
        self.assertTrue(list((self.store.path.parent / 'backups').glob('*.sqlite3')))


class SessionReadCostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)

    def tearDown(self):
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def session_with(self, shots):
        if self.service.practice:
            self.service.change_practice(self.service.practice.data['id'], 'abandon')
        data = self.service.create_practice(dict(PUTTING))
        for seq in range(shots):
            self.service.practice.add(putt(seq))
        return data['id']

    def statements(self, session_id):
        executed = []
        connection = self.service.store.connection
        connection.set_trace_callback(executed.append)
        try:
            data = read_session(connection, session_id)
        finally:
            connection.set_trace_callback(None)
        return len(executed), data

    def test_query_count_does_not_grow_with_attempts(self):
        few, few_data = self.statements(self.session_with(2))
        many, many_data = self.statements(self.session_with(12))
        self.assertEqual(len(few_data['shots']), 2)
        self.assertEqual(len(many_data['shots']), 12)
        self.assertEqual(few, many)

    def test_session_list_filters_other_golfers_in_sql_and_reads_each_once(self):
        mine = self.session_with(2)
        self.service.change_practice(mine, 'finish')
        self.service.change_golfer(name='Second golfer')
        other = self.session_with(1)
        self.service.change_practice(other, 'finish')
        with patch('domain_schema.read_session', wraps=read_session) as reads:
            listed = self.service.sessions()
        self.assertEqual([s['id'] for s in listed], [other])
        self.assertEqual(reads.call_count, 1)


if __name__ == '__main__':
    unittest.main()
