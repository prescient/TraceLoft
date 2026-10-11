import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import migrations
from storage import SCHEMA, SCHEMA_VERSION, Store


# SHA-256 (LF line endings) of every released migration file. A mismatch means a released
# step was edited: revert it and add the next step instead. Add new files here when released.
RELEASED = {
    'sql/0001_base.sql': '434f9e0590c20355a763b4658f68e9220123fca920cd33af295f4c99ae557fa9',
    'sql/0002_wide_metrics.sql': '2b522ac4d9b0c66543a3560952009359f3c9b622b9c990bcd49f9ba7e4620edf',
    'sql/0003_relational_domain.sql': '18364bfdbef03af2a0b3c540d91b4caa10200145479e941f51da8fe13e65308a',
    'sql/0004_collection_cohorts.sql': '66b5b97c1657dff8ab3172bd86df87342b1ad8af0148770d6b42181124c5d386',
    'sql/0005_staged_calculations.sql': '1e22e4d8efa8c6ef904236090dc46f94095cddf3a518e61310893195357a01c1',
    'v0002_wide_metrics.py': '40892884e18206e024c732529bade6c859d26eed6f1f1eba5f768bc4d4d09c51',
    'v0003_relational_domain.py': 'e8783a9f8c29d1f9db1ec2d467a586aa3ff084810af8197d8213d4cebe58943f',
    'v0004_collection_cohorts.py': 'd05a1bb197748f438d973de57b98dff5de3669e379e53af78aabbb109c5455e5',
    'v0005_staged_calculations.py': 'b5d68b358c2931f9de64cddbce5c4fe496f97615fbc6897e8be5496438d8669d',
}


class ReleasedMigrationTests(unittest.TestCase):
    root = Path(migrations.__file__).resolve().parent

    def test_released_steps_are_unchanged(self):
        for name, expected in RELEASED.items():
            with self.subTest(file=name):
                data = (self.root / name).read_bytes().replace(b'\r\n', b'\n')
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(),
                    expected,
                    f'{name} is a released migration; add a new step instead of editing it.',
                )

    def test_every_step_and_sql_file_is_pinned(self):
        files = {p.relative_to(self.root).as_posix() for p in self.root.glob('v0*.py')}
        files |= {p.relative_to(self.root).as_posix() for p in (self.root / 'sql').glob('*.sql')}
        self.assertEqual(files, set(RELEASED))
        for version, step in migrations.STEPS.items():
            self.assertEqual(step.TO_VERSION, version + 1)
            self.assertIn('sql/' + step.SQL, RELEASED)

    def test_base_schema_is_loaded_from_the_frozen_file(self):
        self.assertEqual(SCHEMA, migrations.sql('0001_base.sql'))


class MigrationTableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'golfdata.sqlite3')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def version(self):
        return self.store.connection.execute('PRAGMA user_version').fetchone()[0]

    def test_steps_are_contiguous_and_reach_the_current_schema(self):
        self.assertEqual(sorted(migrations.STEPS), list(range(1, SCHEMA_VERSION)))
        self.assertEqual(self.version(), SCHEMA_VERSION)

    def test_failed_reconciliation_rolls_back_ddl_report_and_version(self):
        def reject(store, before):
            raise ValueError('reconciliation failed')

        with self.assertRaises(ValueError):
            migrations._apply(
                self.store,
                SCHEMA_VERSION + 1,
                'CREATE TABLE probe(x);',
                'probe',
                False,
                lambda store: None,
                reject,
            )
        connection = self.store.connection
        self.assertEqual(self.version(), SCHEMA_VERSION)
        self.assertIsNone(
            connection.execute("SELECT 1 FROM sqlite_master WHERE name='probe'").fetchone()
        )
        self.assertIsNone(
            connection.execute(
                'SELECT 1 FROM metadata WHERE key=?', (f'schema_migration.v{SCHEMA_VERSION + 1}',)
            ).fetchone()
        )

    def test_successful_step_records_report_with_backup(self):
        migrations._apply(
            self.store,
            SCHEMA_VERSION + 1,
            'CREATE TABLE probe(x);',
            'probe',
            True,
            lambda store: 'before',
            lambda store, before: dict(seen=before),
        )
        self.assertEqual(self.version(), SCHEMA_VERSION + 1)
        report = json.loads(
            self.store.connection.execute(
                'SELECT value FROM metadata WHERE key=?',
                (f'schema_migration.v{SCHEMA_VERSION + 1}',),
            ).fetchone()[0]
        )
        self.assertEqual(report['from_schema'], SCHEMA_VERSION)
        self.assertEqual(report['stage'], 'probe')
        self.assertEqual(report['seen'], 'before')
        self.assertTrue(Path(report['backup']).exists())


if __name__ == '__main__':
    unittest.main()
