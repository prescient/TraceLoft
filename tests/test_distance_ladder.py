"""Full-swing scoring, capture readiness and database journeys on disposable data."""
import asyncio
import contextlib
import copy
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from distance_ladder import DistanceLadderSession
from storage import Store
from web_app import create_app
from web_service import GolfService


def event(seq, carry=30, total=35, **extra):
    return dict(kind='record', session_id='test-ladder', seq=seq, result='validated',
                vals=dict(ball_speed=65.4, launch_ang=25, launch_dir=1, carry=carry, total=total), **extra)


class LadderTests(unittest.TestCase):
    def test_rounds_multi_shot_rungs_misses_and_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            session=DistanceLadderSession(folder, range_start=30, range_end=40, range_step=10,
                                          range_shots=2, range_rounds=2)
            expected=[30,30,40,40,30,30,40,40]
            for i,target in enumerate(expected,1):
                self.assertEqual(session.data['target'],target)
                record=event(i, target+10 if i==3 else target)
                self.assertTrue(session.add(record))
                self.assertFalse(session.add(record))
            self.assertEqual([s['target_distance_yd'] for s in session.data['shots']],expected)
            self.assertEqual([s['ladder_round'] for s in session.data['shots']],[1]*4+[2]*4)
            self.assertTrue(session.data['ended'])
            self.assertEqual(session.summary()['successes'],7)
            self.assertFalse(session.add(event(9)))
            session.toggle_excluded(session.data['shots'][0]['key'])
            self.assertEqual(session.data['completed_shots'],8)
            self.assertEqual(session.summary()['count'],7)

    def test_missing_invalid_and_zero_distance_keep_distinct_meanings(self):
        with tempfile.TemporaryDirectory() as folder:
            session=DistanceLadderSession(folder)
            for i,value in enumerate((None,float('inf'),-1,True,'30'),1):
                # A nonfinite source value cannot be persisted as JSON; validated captures never contain it.
                if isinstance(value,float):
                    continue
                self.assertTrue(session.add(event(i,value)))
                self.assertEqual(session.data['target'],30)
                self.assertEqual(session.data['completed_shots'],0)
                self.assertFalse(session.data['shots'][-1]['scored'])
            self.assertTrue(session.add(event(6,0)))
            self.assertTrue(session.data['shots'][-1]['scored'])
            self.assertFalse(session.data['shots'][-1]['success'])
            self.assertEqual(session.data['target'],40)
            self.assertEqual(session.summary()['unscored'],4)

    def test_total_does_not_substitute_carry_and_descending_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            session=DistanceLadderSession(folder,range_start=90,range_end=110,range_step=10,
                                          range_metric='total',range_order='descending')
            session.add(event(1,carry=110,total=None))
            self.assertEqual(session.data['completed_shots'],0)
            session.add(event(2,carry=85,total=105))
            shot=session.data['shots'][-1]
            self.assertEqual((shot['target_distance_yd'],shot['distance_yd'],shot['distance_error_yd']),(110,105,-5))
            self.assertTrue(shot['success'])
            self.assertEqual(session.data['target'],100)

    def test_configuration_rejection_before_saving(self):
        cases=[dict(range_step=11),dict(range_end=30),dict(range_rounds=0),dict(range_shots=1.5),
               dict(range_metric='offline'),dict(range_order='random'),dict(range_category='putting'),
               dict(range_end=460),dict(range_club='x'*81),dict(range_shots=100,range_rounds=100),
               dict(range_tolerance=float('nan'))]
        with tempfile.TemporaryDirectory() as folder:
            for params in cases:
                with self.subTest(params=params),self.assertRaises(ValueError):DistanceLadderSession(folder,**params)
            self.assertFalse(list(Path(folder).glob('*.json')))




    def test_failed_save_rolls_back_target_and_retry_scores_once(self):
        with tempfile.TemporaryDirectory() as folder:
            service=GolfService(folder,capture_detector=lambda:False)
            service.create_practice(dict(drill='Distance ladder'))
            sid=service.practice.data['id']
            e=event(1,32,receipt_id='retry-range',practice_session_id=sid)
            with patch.object(service.store,'save_session',side_effect=OSError('disk unavailable')):
                service.ingest(e)
            self.assertEqual(service.practice.data['target'],30)
            self.assertEqual(service.practice.data['completed_shots'],0)
            self.assertTrue(service.pending)
            self.assertEqual(service.store.count('ingest_events'),0)
            service.flush_practice()
            service.ingest(e)
            self.assertEqual(service.practice.data['target'],40)
            self.assertEqual(service.practice.data['completed_shots'],1)
            self.assertEqual(len(service.practice.data['shots']),1)
            asyncio.run(service.shutdown())

    def test_sqlite_reload_scoring_export_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as folder:
            service=GolfService(folder,capture_detector=lambda:False)
            client=TestClient(create_app(service),base_url='http://localhost')
            params=dict(drill='Distance ladder',range_start=30,range_end=40,range_step=10,
                        range_rounds=1,range_club='54° wedge')
            response=client.post('/api/practice',json=params)
            self.assertEqual(response.status_code,200,response.text)
            sid=response.json()['practice']['id']
            original=copy.deepcopy(service.practice.data)
            self.assertEqual(service.input.context()['required_distance'],'carry')
            self.assertEqual(client.post('/api/practice',json=params).status_code,409)
            for i,carry in ((1,None),(2,32),(3,47)):
                e=event(i,carry,practice_session_id=sid,receipt_id=f'test-receipt-{i}')
                service.ingest(e)
                service.ingest(e)
            self.assertEqual(service.practice.data['completed_shots'],2)
            self.assertEqual(len(service.practice.data['shots']),3)
            self.assertIsNone(service.input.context()['required_distance'])
            saved=service.load_session(sid)
            self.assertIsInstance(saved,DistanceLadderSession)
            self.assertEqual(saved.summary(),service.practice.summary())
            self.assertEqual(original['ladder_targets_yd'],saved.data['ladder_targets_yd'])
            key=saved.data['shots'][1]['key']
            service.exclude_saved(sid,key)
            self.assertEqual(service.load_session(sid).summary()['count'],1)
            with zipfile.ZipFile(io.BytesIO(service.store.export())) as z:
                attempts=list(csv.DictReader(io.StringIO(z.read('session_attempts.csv').decode('utf-8-sig'))))
                self.assertEqual(attempts[1]['distance_yd'],'32')
                self.assertEqual(attempts[1]['distance_error_yd'],'2.0')
                self.assertEqual(attempts[1]['club_label'],'54° wedge')
                self.assertEqual(attempts[0]['scored'],'False')
            service.delete_session(sid)
            service.restore_session(sid)
            self.assertEqual(service.load_session(sid).data['shots'][1]['excluded'],True)
            self.assertEqual(service.store.connection.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertFalse(service.store.connection.execute('PRAGMA foreign_key_check').fetchall())
            client.close()
            asyncio.run(service.shutdown())


if __name__=='__main__':unittest.main()
