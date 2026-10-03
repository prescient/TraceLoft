"""Migration, atomicity, recovery and database-backed user journeys on isolated data."""
import asyncio
import copy
import csv
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from database_tools import ServiceLease, preserve_legacy, restore_snapshot
from putting import PuttingSession
from storage import Store, atomic_json, import_legacy, inspect_legacy, digest
from web_app import create_app
from web_service import GolfService

PARAMS = dict(drill='Pace + start line',target=4,speed_tolerance=.3,angle_tolerance=1,repetitions=10)


def event(seq=1, result='validated', **extra):
    return dict(kind='record',session_id='capture',seq=seq,result=result,
                vals=dict(ball_speed=4.123456,launch_dir=-.2,launch_ang=0,total_spin=0),**extra)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root/'data/golfdata.sqlite3')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def legacy(self, collision=False):
        fields = ['time','session_id','seq','ball_speed','launch_dir','launch_ang','total_spin','sent','note','club']
        rows = [dict(time='2026-09-30 12:01:02',session_id='capture',seq=1,ball_speed=4.1,
                     launch_dir=-.2,launch_ang=0,total_spin=0,sent='False',note='ok (no GSPro)',club=''),
                dict(time='2026-09-30 12:01:03',session_id='capture',seq=2,ball_speed='bad',
                     launch_dir='',launch_ang='',total_spin='',sent='False',note='unreadable',club='')]
        path = self.root/'shots.csv'
        with path.open('w',newline='') as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            writer.writerows(rows)
        if collision:
            rows[0]['ball_speed'] = 9
            with (self.root/'shots-other.csv').open('w',newline='') as handle:
                writer = csv.DictWriter(handle, fields)
                writer.writeheader()
                writer.writerows(rows)
        session = PuttingSession(self.root/'practice_sessions', **PARAMS)
        session.add(event())
        session.toggle_excluded('capture:1')
        session.abandon()
        trash = session.folder/'.trash'
        trash.mkdir()
        session.path.rename(trash/session.path.name)
        return session.data

    def test_import_reconciliation_precision_trash_unknown_and_repeat(self):
        data = self.legacy()
        originals = {p: p.read_bytes() for p in self.root.rglob('*') if p.suffix in ('.csv','.json')}
        report = import_legacy(self.store,self.root)
        self.assertEqual(report['after']['sessions'],1)
        self.assertEqual(report['after']['session_attempts'],1)
        self.assertEqual(report['after']['shots'],1)
        self.assertEqual(self.store.load_session(data['id'],True),data)
        self.assertEqual(self.store.list_sessions(),[])
        self.assertEqual(self.store.connection.execute("SELECT count(*) FROM ingest_events WHERE acceptance='unknown'").fetchone()[0],1)
        values = self.store.connection.execute("SELECT real_value FROM shot_metrics WHERE metric_key='ball.speed' ORDER BY provenance").fetchall()
        self.assertEqual(len(values),2)
        self.assertNotEqual(values[0][0],values[1][0])
        again = import_legacy(self.store,self.root)
        self.assertFalse(any(again['added'].values()))
        self.assertEqual(originals,{p:p.read_bytes() for p in originals})
        self.assertEqual(self.store.connection.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_duplicate_files_deduplicate_but_colliding_keys_do_not_merge(self):
        data = self.legacy(collision=True)
        (self.root/'shots-copy.csv').write_bytes((self.root/'shots.csv').read_bytes())
        import_legacy(self.store,self.root)
        self.assertEqual(self.store.count('shots'),3)
        self.assertEqual(self.store.count('ingest_events'),5)
        attempt = self.store.connection.execute('SELECT shot_id FROM session_attempts').fetchone()[0]
        self.assertEqual(self.store.connection.execute('SELECT provenance FROM observations WHERE shot_id=?',(attempt,)).fetchone()[0],'legacy_practice')

    def test_conflicting_sessions_and_changed_sources_roll_back(self):
        data = self.legacy()
        conflict = copy.deepcopy(data)
        conflict['target'] = 8
        (self.root/'practice_sessions'/f"{data['id']}.json").write_text(json.dumps(conflict))
        with self.assertRaises(ValueError):
            import_legacy(self.store,self.root)
        self.assertEqual(self.store.count('shots'),0)
        self.assertFalse(self.store.migrated())
        (self.root/'practice_sessions'/f"{data['id']}.json").unlink()
        import_legacy(self.store,self.root)
        with (self.root/'shots.csv').open('a') as handle:
            handle.write('\n')
        before = self.store.count('ingest_events')
        with self.assertRaises(ValueError):
            import_legacy(self.store,self.root)
        self.assertEqual(self.store.count('ingest_events'),before)

    def test_validity_missing_zero_and_duplicate_conflict(self):
        first = event(receipt_id='stable',captured_at='2026-10-01T00:00:00+00:00')
        self.store.ingest(first)
        self.store.ingest(first)
        self.assertEqual(self.store.count('shots'),1)
        with self.assertRaises(ValueError):
            self.store.ingest(dict(first,vals={'ball_speed':5}))
        self.store.ingest(event(2,'failed'))
        self.assertEqual(self.store.count('shots'),1)
        self.assertEqual(self.store.connection.execute("SELECT real_value FROM metric_values WHERE source_field='total_spin' LIMIT 1").fetchone()[0],0)
        self.assertIsNone(self.store.connection.execute("SELECT real_value FROM metric_values WHERE source_field='spin_axis' LIMIT 1").fetchone()[0])

    def test_backup_restore_wal_counts_checksum_and_existing_destination(self):
        self.store.ingest(event())
        backup = self.store.backup()
        self.store.ingest(event(2))
        target = self.root/'restored.sqlite3'
        restore_snapshot(backup,target)
        restored = Store(target)
        self.assertEqual(restored.count('shots'),1)
        restored.close()
        with self.assertRaises(FileExistsError):
            restore_snapshot(backup,target)
        with backup.open('ab') as handle:
            handle.write(b'bad')
        with self.assertRaises(ValueError):
            restore_snapshot(backup,self.root/'other.sqlite3')

    def test_export_one_shot_multiple_observations_exclusions_and_text_safety(self):
        data = self.legacy()
        import_legacy(self.store,self.root)
        self.store.ingest(dict(event(3),club='=DANGEROUS'))
        with zipfile.ZipFile(io.BytesIO(self.store.export())) as archive:
            shots = list(csv.DictReader(io.StringIO(archive.read('shots.csv').decode('utf-8-sig'))))
            attempts = list(csv.DictReader(io.StringIO(archive.read('session_attempts.csv').decode('utf-8-sig'))))
            long_values = list(csv.DictReader(io.StringIO(archive.read('metric_values.csv').decode('utf-8-sig'))))
            self.assertTrue(any(v['shot_id']=='' and v['acceptance']=='unknown' and v['availability']=='invalid' for v in long_values))
            self.assertEqual(len(shots),2)
            self.assertTrue(any(s['reported_club']=="'=DANGEROUS" for s in shots))
            self.assertEqual(attempts[0]['excluded'],'1')
            self.assertTrue(attempts[0]['deleted_at'])
            self.assertEqual(json.loads(archive.read('manifest.json'))['counts']['shots.csv'],2)

    def test_dry_run_no_database_and_verified_source_archive(self):
        self.legacy()
        archive = preserve_legacy(self.root,self.root/'archive')
        with zipfile.ZipFile(archive) as handle:
            manifest = json.loads(handle.read('manifest.json'))
            self.assertEqual(digest(handle.read('shots.csv')),manifest['shots.csv']['sha256'])
        absent = self.root/'absent.sqlite3'
        result = subprocess.run([sys.executable,'-B','database_tools.py','migrate','--root',str(self.root),
                                 '--database',str(absent),'--dry-run'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(absent.exists())

    def test_sqlite_locked_writer_aborts_without_partial_data(self):
        other = sqlite3.connect(self.store.path,isolation_level=None)
        other.execute('BEGIN IMMEDIATE')
        self.store.connection.execute('PRAGMA busy_timeout=5')
        with self.assertRaises(OSError):
            self.store.ingest(event())
        other.execute('ROLLBACK')
        other.close()
        self.assertEqual(self.store.count('shots'),0)

    def test_process_crash_rolls_back_transaction_and_keeps_receipt(self):
        receipt = self.root/'receipts'/'crash.json'
        atomic_json(receipt,event(receipt_id='crash'))
        script = "import os,sys; from storage import Store; s=Store(sys.argv[1]); s.connection.execute('BEGIN IMMEDIATE'); s.connection.execute(\"INSERT INTO metadata VALUES('uncommitted','x')\"); os._exit(3)"
        crashed = subprocess.run([sys.executable,'-B','-c',script,str(self.store.path)],capture_output=True)
        self.assertEqual(crashed.returncode,3)
        self.assertIsNone(self.store.connection.execute("SELECT value FROM metadata WHERE key='uncommitted'").fetchone())
        self.assertTrue(receipt.exists())
        self.assertEqual(self.store.connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')


    def test_catalog_rejects_value_type_mismatch(self):
        self.store.ingest(event())
        row = list(self.store.connection.execute('SELECT * FROM metric_values LIMIT 1').fetchone())
        row[1] = 'outcome.holed'
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',row)

    def test_sqlite_full_aborts_entire_receipt_transaction(self):
        pages = self.store.connection.execute('PRAGMA page_count').fetchone()[0]
        self.store.connection.execute(f'PRAGMA max_page_count={pages}')
        with self.assertRaises(OSError):
            self.store.ingest(dict(event(),evidence='x'*1000000))
        self.assertEqual(self.store.count('ingest_events'),0)
        self.assertEqual(self.store.count('shots'),0)
        self.assertEqual(self.store.connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')


class DatabaseJourneys(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name,capture_detector=lambda:False)
        self.client = TestClient(create_app(self.service),base_url='http://localhost')

    def tearDown(self):
        self.client.close()
        self.service.lease.close()
        self.service.store.close()
        self.temp.cleanup()

    def launch(self,**extra):
        response = self.client.post('/api/practice',json=dict(PARAMS,**extra))
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['practice']

    def test_finish_review_delete_restore_and_exports(self):
        data = self.launch(repetitions=1)
        self.service.ingest(event(receipt_id='record-1',practice_session_id=data['id']))
        self.assertTrue(self.service.practice.data['ended'])
        self.assertEqual(self.service.store.count('shots'),1)
        self.assertEqual(self.client.get(f"/api/sessions/{data['id']}").status_code,200)
        self.assertEqual(self.client.post(f"/api/sessions/{data['id']}/exclude",json={'key':'capture:1'}).json()['summary']['count'],0)
        self.assertEqual(self.client.delete(f"/api/sessions/{data['id']}").status_code,200)
        self.assertEqual(self.client.get(f"/api/sessions/{data['id']}").status_code,404)
        self.assertEqual(self.client.get('/api/sessions?deleted=true').json()[0]['id'],data['id'])
        self.assertEqual(self.client.post(f"/api/sessions/{data['id']}/restore").status_code,200)
        self.assertEqual(self.service.store.count('shots'),1)
        self.assertFalse((self.service.root/'practice_sessions').exists())
        self.assertEqual(self.client.get('/api/exports/csv').status_code,200)
        self.assertTrue(self.client.post('/api/storage/backup').json()['verified'])

    def test_unspooled_compatibility_record_links_without_double_counting(self):
        self.launch()
        self.service.ingest(event())
        self.service.ingest(event())
        self.assertEqual(self.service.store.count('shots'),1)
        self.assertEqual(self.service.store.count('session_attempts'),1)

    def test_backup_failure_reports_without_undoing_saved_completion(self):
        self.launch(repetitions=1)
        with patch.object(self.service.store,'backup',side_effect=sqlite3.OperationalError('disk full')):
            self.service.ingest(event(receipt_id='saved'))
            self.assertTrue(self.service.practice.data['ended'])
            self.assertEqual(self.service.store.count('shots'),1)
            self.assertIn('Session saved; local backup failed',self.service.capture['error'])
            response = self.client.post('/api/storage/backup')
            self.assertEqual(response.status_code,500)
            self.assertIn('disk full',response.json()['detail'])

    def test_failed_atomic_save_rolls_back_all_and_receipt_survives_crash(self):
        data = self.launch()
        receipt = event(receipt_id='durable-1',practice_session_id=data['id'],captured_at='2026-10-01T00:00:00+00:00')
        atomic_json(self.service.receipt_dir/'durable-1.json',receipt)
        with patch.object(self.service.practice,'save',side_effect=OSError('disk full')):
            self.service.ingest(receipt)
        self.assertEqual(self.service.store.count('shots'),0)
        self.assertEqual(self.service.practice.data['shots'],[])
        self.assertTrue((self.service.receipt_dir/'durable-1.json').exists())
        self.service.pending.clear()  # simulated loss of in-memory queue
        self.service.practice = None
        self.service.recover_receipts()
        self.assertEqual(self.service.store.count('shots'),1)
        self.assertEqual(self.service.store.load_session(data['id'])['shots'][0]['target'],4)
        self.assertFalse((self.service.receipt_dir/'durable-1.json').exists())
        # Crash after commit, before unlink: leftover receipt does not count a second putt.
        atomic_json(self.service.receipt_dir/'durable-1.json',receipt)
        self.service.recover_receipts()
        self.assertEqual(self.service.store.count('session_attempts'),1)

    def test_range_failures_and_desktop_receipts_do_not_enter_another_drill(self):
        self.service.ingest(event(result='failed',receipt_id='bad'))
        self.service.ingest(event(2,receipt_id='range',practice_session_id=None))
        data = self.launch()
        self.service.ingest(event(3,receipt_id='desktop',practice_session_id=None))
        self.assertEqual(self.service.practice.data['shots'],[])
        self.assertEqual(self.service.store.count('shots'),2)
        self.assertEqual(self.service.store.count('ingest_events'),3)
        self.assertEqual(self.client.delete(f"/api/sessions/{data['id']}").status_code,409)
        self.assertEqual(self.client.post(f"/api/practice/{data['id']}/abandon").status_code,200)
        self.assertEqual(self.client.delete(f"/api/sessions/{data['id']}").status_code,200)

    def test_random_targets_duplicate_records_and_owner_guard(self):
        data = self.launch(random_pace=True,minimum=3,maximum=3.1)
        for seq in range(1,4):
            target = self.service.practice.data['target']
            shot = dict(event(seq,receipt_id=f'putt-{seq}',practice_session_id=data['id']),
                        vals={'ball_speed':target,'launch_dir':0,'launch_ang':0})
            self.service.ingest(shot)
            self.service.ingest(shot)
            self.assertNotEqual(self.service.practice.data['target'],target)
        self.assertEqual(self.service.practice.summary()['count'],3)
        with self.assertRaises(OSError):
            ServiceLease(self.service.store.path)
        with self.assertRaises(OSError):
            GolfService(self.temp.name,capture_detector=lambda:False)
        self.assertEqual(self.client.post('/api/practice/'+'f'*32+'/finish').status_code,409)


if __name__=='__main__':
    unittest.main()
