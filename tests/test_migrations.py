import json
import tempfile
import unittest
from pathlib import Path

import migrations
from storage import SCHEMA_VERSION, Store


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
                self.store, SCHEMA_VERSION + 1, 'CREATE TABLE probe(x);', 'probe', False,
                lambda store: None, reject,
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
            self.store, SCHEMA_VERSION + 1, 'CREATE TABLE probe(x);', 'probe', True,
            lambda store: 'before', lambda store, before: dict(seen=before),
        )
        self.assertEqual(self.version(), SCHEMA_VERSION + 1)
        report = json.loads(
            self.store.connection.execute(
                'SELECT value FROM metadata WHERE key=?', (f'schema_migration.v{SCHEMA_VERSION + 1}',)
            ).fetchone()[0]
        )
        self.assertEqual(report['from_schema'], SCHEMA_VERSION)
        self.assertEqual(report['stage'], 'probe')
        self.assertEqual(report['seen'], 'before')
        self.assertTrue(Path(report['backup']).exists())


if __name__ == '__main__':
    unittest.main()
