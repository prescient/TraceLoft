"""Real schema-v1 upgrades, rollback and immutable source/calculation identity."""
import copy
import contextlib
import csv
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from database_tools import ServiceLease, restore_snapshot
from shot_schema import SOURCE_FIELDS, evidence_manifest, identity as report_identity
from storage import ROOT, SCHEMA, Store, digest, encoded, identity


class ShotSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'golfdata.sqlite3'
        self.store = None

    def tearDown(self):
        if self.store:
            self.store.close()
        self.temp.cleanup()

    def legacy_database(self):
        connection = sqlite3.connect(self.path,isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.executescript(SCHEMA)
        seed = Store.__new__(Store)
        seed.connection = connection
        seed._catalog()
        profile = json.loads((ROOT/'data/metric_mapping.normalized.v1.json').read_text('utf-8'))['profiles'][0]
        connection.execute('INSERT INTO mapping_versions VALUES(?,?,?)',(profile['id'],digest(encoded(profile).encode()),encoded(profile)))
        connection.execute('INSERT INTO sources VALUES(?,?)',('source','{}'))
        connection.execute('INSERT INTO capture_streams VALUES(?,?,?)',('stream','source','stream'))
        shot_id = identity('shot:receipt')
        observations = []
        for event_id, provenance, total in (('receipt','live_capture',180),('practice','practice_measurements',179)):
            event = dict(kind='record',receipt_id=event_id,session_id='source',seq=1,result='validated',
                vals=dict(ball_speed=100.123456,total=total,carry=170,offline=-4,club_speed=80,total_spin=0),
                mapping_id='traceloft.normalized.v1')
            connection.execute('INSERT INTO ingest_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                (event_id,'stream','source:1',None,'2026-10-10T00:00:00+00:00','utc_receipt','accepted',encoded(event),None,None))
            if event_id == 'receipt':
                connection.execute('INSERT INTO shots VALUES(?,?,?,?,?)',(shot_id,event_id,'2026-10-10T00:00:00+00:00','utc_receipt','7i'))
            observation_id = identity('observation:'+event_id)
            observations.append(observation_id)
            connection.execute('INSERT INTO observations VALUES(?,?,?,?,?)',(observation_id,event_id,shot_id,profile['id'],provenance))
            for field in profile['fields']:
                value = event['vals'].get(field['source_field'])
                factor = field['transform'].get('factor',1)
                connection.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (observation_id,field['metric'],1,value*factor if value is not None else None,None,None,None,
                     field['source_field'],field['source_unit'],encoded(value),'available' if value is not None else 'unavailable',
                     field['method'],field['semantic_variant']))
        sid = 'a'*32
        attempt = dict(key='source:1',captured='2026-10-10T00:00:00+00:00',vals=event['vals'],
            excluded=True,success=False,target=170,
            equipment_selection=dict(bag_id='bag',bag_name='My bag',club_id='club',club_label='7 iron'),
            flight=dict(model='test_saved_model_v1',status='ready',metrics=dict(carry_yd=169,total_yd=177,apex_ft=65,
                descent_deg=40,hang_time_s=5),shape='Straight',trajectory=[dict(t=0,x=0,y=0,z=0)],
                carry_point_yd=dict(forward=169,right=2),total_point_yd=dict(forward=177,right=3)),
            game_outcome=dict(score=5,penalty_strokes=1,conceded_putts=1),
            estimated_distance_ft=12,target_distance_ft=10,distance_error_ft=2,stimp_ft=10,distance_model_id='saved_putting_v1')
        data = dict(id=sid,started='2026-10-10T00:00:00+00:00',ended='2026-10-10T01:00:00+00:00',
                    drill='Driving range',target=170,shots=[attempt],game=dict(score=5))
        connection.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?)',(sid,data['started'],data['ended'],data['drill'],None,1,encoded(data)))
        connection.execute('INSERT INTO session_attempts VALUES(?,?,?,?,?,?,?,?,?,?)',
            (sid,1,attempt['key'],shot_id,observations[1],attempt['captured'],170,0,1,encoded(attempt)))
        connection.execute('PRAGMA application_id=1196379206')
        connection.execute('PRAGMA user_version=1')
        before = evidence_manifest(connection)
        connection.close()
        return data,shot_id,observations,before

    def test_upgrade_preserves_evidence_outcomes_and_both_reports(self):
        data,shot_id,observations,before = self.legacy_database()
        self.store = Store(self.path)
        c = self.store.connection
        from storage import SCHEMA_VERSION
        self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
        self.assertEqual(evidence_manifest(c),before)
        self.assertEqual(self.store.load_session(data['id']),data)
        self.assertEqual(self.store.list_sessions(),[data])
        self.assertEqual(c.execute('SELECT count(*) FROM shot_source_metrics').fetchone()[0],2)
        source = c.execute('SELECT * FROM v_shots_source').fetchone()
        self.assertEqual(source['total_distance_yd'],180)
        self.assertEqual(source['observation_id'],observations[0])
        attempt = c.execute('SELECT * FROM v_session_shots').fetchone()
        self.assertEqual(attempt['total_distance_yd'],179)
        self.assertEqual(attempt['model_total_distance_yd'],177)
        self.assertEqual(attempt['excluded'],1)
        self.assertEqual(attempt['estimated_distance_ft'],12)
        self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        original_event = json.loads(c.execute("SELECT raw_json FROM ingest_events WHERE id='receipt'").fetchone()[0])
        self.assertEqual(self.store.ingest(original_event),('receipt',False))
        self.assertEqual(c.execute('SELECT count(*) FROM shot_source_metrics').fetchone()[0],2)
        self.assertTrue(all(r[0]=='legacy_saved_outcome_incomplete_lineage' for r in c.execute("SELECT provenance FROM calculation_runs WHERE model_family!='source_features'")))
        report = json.loads(c.execute("SELECT value FROM metadata WHERE key='schema_migration.v2'").fetchone()[0])
        backup = Path(report['backup'])
        manifest = json.loads(backup.with_suffix('.manifest.json').read_text('utf-8'))
        self.assertEqual(manifest['schema'],1)
        self.assertEqual(manifest['sha256'],digest(backup.read_bytes()))
        restore_snapshot(backup,Path(self.temp.name)/'rollback.sqlite3')
        with contextlib.closing(sqlite3.connect(Path(self.temp.name)/'rollback.sqlite3')) as original:
            self.assertEqual(original.execute('PRAGMA user_version').fetchone()[0],1)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(self.store.load_session(data['id']),data)
        self.assertEqual(len(list((self.path.parent/'backups').glob('*.sqlite3'))),2)

    def test_failed_migration_rolls_back_to_v1(self):
        data,_,_,before = self.legacy_database()
        with patch('shot_schema.backfill',side_effect=RuntimeError('interrupted upgrade')):
            with self.assertRaises(RuntimeError):
                Store(self.path)
        with contextlib.closing(sqlite3.connect(self.path)) as c:
            self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],1)
            self.assertEqual(evidence_manifest(c),before)
            self.assertIsNone(c.execute("SELECT name FROM sqlite_master WHERE name='shot_source_metrics'").fetchone())
        self.store = Store(self.path)
        self.assertEqual(self.store.load_session(data['id']),data)

    def test_live_18_fields_quality_zero_smash_and_idempotency(self):
        self.store = Store(self.path)
        event = dict(receipt_id='stable',session_id='live',seq=1,result='validated',mapping_id='traceloft.normalized.v1',
            vals=dict(ball_speed=150,club_speed=100,smash_factor=1.47,carry=260,total=275,offline=0,
                      launch_ang=12,launch_dir=0,total_spin=2500,spin_axis=None,curve='invalid'))
        self.store.ingest(event)
        self.store.ingest(copy.deepcopy(event))
        c = self.store.connection
        row = c.execute('SELECT * FROM v_shots_source').fetchone()
        self.assertEqual(row['total_distance_yd'],275)
        self.assertEqual(row['smash_factor'],1.47)
        self.assertEqual(c.execute('SELECT calculated_smash_factor FROM v_shots_analysis').fetchone()[0],1.5)
        quality = dict(c.execute('SELECT column_name,availability FROM source_metric_quality'))
        self.assertEqual(len(quality),18)
        self.assertEqual(quality['total_distance_yd'],'available')
        self.assertEqual(quality['ball_offline_yd'],'available')
        self.assertEqual(quality['spin_tilt_axis_deg'],'unavailable')
        self.assertEqual(quality['ball_curve_yd'],'invalid')
        self.assertEqual(quality['ball_apex_ft'],'not_supplied')
        self.assertEqual(c.execute('SELECT count(*) FROM shot_source_metrics').fetchone()[0],1)
        with self.assertRaises(OSError):
            with self.store.transaction():
                c.execute('UPDATE shot_source_metrics SET total_distance_yd=300')
        self.assertEqual(c.execute('SELECT total_distance_yd FROM v_shots_source').fetchone()[0],275)
        self.store.ingest(dict(event,receipt_id='no_club',seq=2,vals=dict(ball_speed=100,club_speed=0)))
        row = c.execute('SELECT calculated_smash_factor FROM v_shots_analysis WHERE shot_id=?',(identity('shot:no_club'),)).fetchone()
        self.assertIsNone(row[0])

    def test_new_calculation_version_is_separate_and_does_not_rescore(self):
        data,shot_id,_,_ = self.legacy_database()
        self.store = Store(self.path)
        c = self.store.connection
        pinned = c.execute("SELECT * FROM attempt_derived_results WHERE model_family='flight'").fetchone()
        report = c.execute('SELECT report_id FROM calculation_inputs WHERE result_id=?',(pinned['result_id'],)).fetchone()[0]
        args = (shot_id,report,'flight',pinned['context_id'],'test_model_v2',dict(ground='test'),
                dict(status='ready'),dict(total_distance_yd=185,carry_distance_yd=178))
        new = self.store.write_derived_result(*args,provenance='test_recalculation',select=False)
        self.assertEqual(self.store.write_derived_result(*args,provenance='test_recalculation'),new)
        self.assertEqual(c.execute("SELECT result_id FROM derived_metric_selection WHERE model_family='flight'").fetchone()[0],pinned['result_id'])
        self.store.write_derived_result(*args,provenance='test_recalculation',select=True)
        self.assertEqual(c.execute("SELECT result_id FROM derived_metric_selection WHERE model_family='flight'").fetchone()[0],new)
        self.assertEqual(c.execute('SELECT model_total_distance_yd FROM v_session_shots').fetchone()[0],177)
        self.assertEqual(self.store.load_session(data['id']),data)
        with self.assertRaises(OSError):
            with self.store.transaction():
                c.execute('UPDATE shot_derived_metrics SET total_distance_yd=999 WHERE result_id=?',(new,))
        other = dict(receipt_id='other',session_id='live',seq=2,result='validated',vals=dict(ball_speed=50))
        self.store.ingest(other)
        with self.assertRaises(OSError):
            self.store.write_derived_result(identity('shot:other'),report,'flight','shot','bad_link',{},dict(status='ready'),{},provenance='test')
        self.assertIsNone(c.execute("SELECT 1 FROM calculation_runs WHERE model_version='bad_link'").fetchone())

    def test_upgrade_respects_service_owner_and_export_has_versioned_tables(self):
        self.legacy_database()
        lease = ServiceLease(self.path)
        try:
            with self.assertRaises(OSError):
                Store(self.path)
        finally:
            lease.close()
        self.store = Store(self.path)
        with zipfile.ZipFile(io.BytesIO(self.store.export())) as archive:
            reports = list(csv.DictReader(io.StringIO(archive.read('shot_source_metrics.csv').decode('utf-8-sig'))))
            self.assertEqual(len(reports),2)
            self.assertEqual(set(c for c,_,_ in SOURCE_FIELDS.values())-set(reports[0]),set())
            self.assertIn('shot_derived_metrics.csv',archive.namelist())
            self.assertIn('calculation_inputs.csv',archive.namelist())
            single = list(csv.DictReader(io.StringIO(archive.read('shots_source.csv').decode('utf-8-sig'))))
            self.assertEqual(len(single),1)
            self.assertEqual(single[0]['total_distance_yd'],'180.0')
            from storage import SCHEMA_VERSION
            self.assertEqual(json.loads(archive.read('manifest.json'))['schema'],SCHEMA_VERSION)


if __name__ == '__main__':
    unittest.main()
