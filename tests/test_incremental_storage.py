import copy
import tempfile
import unittest
import uuid
from pathlib import Path

from storage import Store


class IncrementalStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'data.sqlite3')
        self.addCleanup(self.store.close)
        self.data = dict(id=uuid.uuid4().hex, started='2026-10-10T12:00:00Z', ended=None,
                         drill='Driving range', practice_type='full_swing', target=150, shots=[])
        self.store.save_session(self.data)
        self.store.connection.executescript('''
            CREATE TEMP TABLE field_writes(action TEXT,ordinal INTEGER,path TEXT);
            CREATE TEMP TRIGGER field_insert AFTER INSERT ON main.attempt_fields BEGIN
                INSERT INTO field_writes VALUES('insert',NEW.ordinal,NEW.path); END;
            CREATE TEMP TRIGGER field_update AFTER UPDATE ON main.attempt_fields BEGIN
                INSERT INTO field_writes VALUES('update',NEW.ordinal,NEW.path); END;
            CREATE TEMP TRIGGER field_delete AFTER DELETE ON main.attempt_fields BEGIN
                INSERT INTO field_writes VALUES('delete',OLD.ordinal,OLD.path); END;
        ''')

    def append(self):
        seq = len(self.data['shots']) + 1
        self.data['shots'].append(dict(key=f'fixture:{seq}', captured='2026-10-10T12:00:00Z',
            vals=dict(ball_speed=100, launch_ang=18, launch_dir=0, total_spin=6000,
                      carry=150, total=160), target=150, success=True, excluded=False))
        self.store.append_attempt(self.data)

    def writes(self):
        return [tuple(r) for r in self.store.connection.execute('SELECT * FROM field_writes')]

    def reset_probe(self):
        self.store.connection.execute('DELETE FROM field_writes')

    def test_shot_100_writes_only_its_fields_and_preserves_history(self):
        for _ in range(99):
            self.append()
        first = self.store.load_session(self.data['id'])['shots'][0]
        self.reset_probe()
        self.append()
        writes = self.writes()
        self.assertTrue(writes)
        self.assertTrue(all(action == 'insert' and ordinal == 100 for action, ordinal, _ in writes))
        field_count = self.store.connection.execute(
            'SELECT count(*) FROM attempt_fields WHERE session_id=? AND ordinal=100',
            (self.data['id'],)).fetchone()[0]
        self.assertEqual(len(writes), field_count)
        restored = self.store.load_session(self.data['id'])
        self.assertEqual(restored['shots'][0], first)
        self.assertEqual(len(restored['shots']), 100)

    def test_state_only_and_scoped_correction_do_not_rewrite_other_attempts(self):
        for _ in range(3):
            self.append()
        self.reset_probe()
        self.data['target'] = 175
        self.store.save_session(self.data)
        self.assertEqual(self.writes(), [])
        self.data['shots'][1]['excluded'] = True
        self.data['shots'][1]['cleanup_reason'] = 'Warmup'
        self.store.save_session(self.data)
        self.assertEqual({row[1] for row in self.writes()}, {2})
        self.assertEqual({row[2] for row in self.writes()}, {'/excluded', '/cleanup_reason'})
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM inclusion_decisions').fetchone()[0], 1)
        self.assertTrue(self.store.load_session(self.data['id'])['shots'][1]['excluded'])

    def test_outer_rollback_does_not_poison_attempt_cache_or_skip_retry(self):
        self.append()
        before = copy.deepcopy(self.data)
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.append()
                raise RuntimeError('interrupt after inner save')
        self.data = before
        self.assertEqual(len(self.store.load_session(self.data['id'])['shots']), 1)
        self.append()
        self.reset_probe()
        self.data['shots'][1]['excluded'] = True
        self.store.save_session(self.data)
        self.assertEqual(self.writes(), [('update', 2, '/excluded')])
        self.assertEqual(self.store.connection.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_restart_and_field_shape_changes_preserve_reconstructed_dto(self):
        self.append()
        self.store._attempt_cache.clear()  # Exercise the cold/restarted-store path.
        self.data = self.store.load_session(self.data['id'])
        self.reset_probe()
        self.data['target'] = 170
        self.store.save_session(self.data)
        self.assertEqual(self.writes(), [])
        self.data['shots'][0]['note'] = {'value': None, 'parts': ['first', True]}
        self.store.save_session(self.data)
        self.data['shots'][0]['note'] = 'reviewed'
        self.store.save_session(self.data)
        self.assertEqual(self.store.load_session(self.data['id'])['shots'][0]['note'], 'reviewed')
        del self.data['shots'][0]['note']
        self.store.save_session(self.data)
        self.assertNotIn('note', self.store.load_session(self.data['id'])['shots'][0])

    def test_removal_reordering_and_invalid_append_reject_atomically(self):
        self.append()
        original = self.store.load_session(self.data['id'])
        for changed in ({**self.data, 'shots': []},
                        {**self.data, 'shots': [{**self.data['shots'][0], 'key': 'other:1'}]}):
            with self.assertRaises(ValueError):
                self.store.save_session(changed)
        with self.assertRaises(ValueError):
            self.store.append_attempt(self.data)
        self.assertEqual(self.store.load_session(self.data['id']), original)
