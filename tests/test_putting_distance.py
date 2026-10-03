"""Provisional distance-model math and isolated SQLite drill journeys."""
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from putting import PuttingSession
from putting_distance import distance_ft, required_speed_mph, MODEL_ID, BASELINE_ID
from storage import Store
from database_tools import restore_snapshot
from web_service import GolfService
from web_app import create_app


def record(seq, speed):
    return dict(kind='record', session_id='fixture', seq=seq, result='validated',
                vals=dict(ball_speed=speed, launch_dir=8.0, launch_ang=0.0))


class DistanceTests(unittest.TestCase):
    def test_constant_braking_baseline_matches_stimp_and_inverse(self):
        self.assertAlmostEqual(distance_ft(1.83/.44704,10,BASELINE_ID),10,places=10)
        for feet in (1,5,25,50):
            speed=required_speed_mph(feet,10,BASELINE_ID)
            self.assertAlmostEqual(distance_ft(speed,10,BASELINE_ID),feet,places=9)
        self.assertAlmostEqual(distance_ft(4,10,BASELINE_ID),10*(4*.44704/1.83)**2)
        with self.assertRaises(ValueError):distance_ft(4,10,'unknown-model')

    def test_default_session_uses_baseline_and_never_recomputes_saved_outcomes(self):
        with tempfile.TemporaryDirectory() as root:
            s=PuttingSession(root,'Putting ladder',4,.3,1,10,ladder_end=10,ladder_rounds=1)
            self.assertEqual(s.data['distance_model']['id'],BASELINE_ID)
            self.assertAlmostEqual(s.data['target'],required_speed_mph(5,10,BASELINE_ID))
            s.add(record(1,s.data['target']))
            saved=json.loads(s.path.read_text())
            reopened=PuttingSession.load(s.path)
            self.assertEqual(saved,reopened.data)
            self.assertAlmostEqual(reopened.data['shots'][0]['estimated_distance_ft'],5)
            self.assertEqual(reopened.data['shots'][0]['distance_model_id'],BASELINE_ID)
            self.assertNotIn('distance',reopened.data['shots'][0]['vals'])

    def test_integral_matches_independent_numerical_braking_integration(self):
        # Numerically integrate v/a(v); this checks the closed-form formula and units.
        for stimp in (3, 10, 20):
            for mph in (.5, 2, 4, 8, 15):
                v = mph * .44704
                dv = (v - .18) / 12000
                decel = 1.83 ** 2 / (2 * stimp * .3048)
                expected = sum((.18 + (i+.5)*dv) / (decel*(1+.3*(.18+(i+.5)*dv-1.83)))
                               for i in range(12000)) * dv / .3048
                self.assertAlmostEqual(distance_ft(mph, stimp, MODEL_ID), expected, places=6)
        self.assertEqual(distance_ft(0, 10), 0)
        self.assertEqual(distance_ft(.18/.44704, 10, MODEL_ID), 0)

    def test_inverse_roundtrips_and_stimp_changes_pace(self):
        for stimp in (3, 10, 20):
            for feet in (.5, 5, 10, distance_ft(14, stimp, MODEL_ID)):
                speed = required_speed_mph(feet, stimp, MODEL_ID)
                self.assertAlmostEqual(distance_ft(speed, stimp, MODEL_ID), feet, places=8)
        self.assertLess(required_speed_mph(25, 12), required_speed_mph(25, 8))
        self.assertGreater(distance_ft(4, 12), distance_ft(4, 8))
        # Speed-dependent braking is deliberately not the simple v² Stimp formula.
        self.assertGreater(abs(distance_ft(1.83/.44704, 10, MODEL_ID)-10), .1)

    def test_invalid_inputs_and_unreachable_targets_are_rejected(self):
        for speed, stimp in ((float('nan'),10),(-1,10),(16,10),(4,0),(4,float('inf')),(True,10)):
            with self.assertRaises(ValueError): distance_ft(speed,stimp)
        with self.assertRaises(ValueError): required_speed_mph(300,3)
        with tempfile.TemporaryDirectory() as root:
            for params in (dict(ladder_step=7),dict(ladder_end=5),dict(ladder_rounds=100,ladder_step=.5),
                           dict(ladder_direction='sideways'),dict(random_pace=True),dict(ladder_rounds=True)):
                with self.assertRaises(ValueError):
                    PuttingSession(root,'Putting ladder',4,.3,1,10,**params)

    def test_distance_windows_boundaries_measured_values_and_exclusions(self):
        with tempfile.TemporaryDirectory() as root:
            s=PuttingSession(root,'Pace consistency',4,.01,1,3,distance_model=MODEL_ID,target_mode='distance',target_distance=10,distance_tolerance=1,stimp=12)
            speed = required_speed_mph(11,12,MODEL_ID)
            self.assertTrue(s.add(record(1,speed)))
            self.assertTrue(s.data['shots'][0]['success'])
            self.assertEqual(s.data['shots'][0]['vals']['ball_speed'],speed)
            s.add(record(2,required_speed_mph(8.9,12,MODEL_ID)))
            self.assertFalse(s.data['shots'][1]['success'])
            self.assertEqual(s.summary()['distance_error_ft']['short'],1)
            s.toggle_excluded('fixture:2')
            self.assertEqual(s.summary()['distance_error_ft']['count'],1)
            self.assertEqual(len(s.data['shots']),2)

    def test_ladder_targets_rounds_duplicates_and_completion_persist(self):
        with tempfile.TemporaryDirectory() as root:
            s=PuttingSession(root,'Putting ladder',4,.3,1,10,distance_model=MODEL_ID,ladder_end=15,ladder_rounds=2,ladder_direction='descending')
            targets=[]
            for n in range(1,7):
                targets.append(s.data['target_distance_ft'])
                # Miss still advances; line is not scored by distance ladder.
                s.add(record(n,s.data['target']+.5 if n==1 else s.data['target']))
                self.assertFalse(s.add(record(n,4)))
                if n==2:s=PuttingSession.load(s.path)
            self.assertEqual(targets,[15,10,5,15,10,5])
            self.assertEqual([p['ladder_round'] for p in s.data['shots']],[1,1,1,2,2,2])
            self.assertEqual(s.summary()['successes'],5)
            self.assertTrue(s.data['ended'])
            self.assertFalse(s.add(record(7,4)))
            s.toggle_excluded('fixture:1')
            self.assertEqual(s.summary()['successes'],5)
            self.assertEqual(s.data['repetitions'],6)

    def test_speed_scoring_random_targets_and_historical_sessions(self):
        with tempfile.TemporaryDirectory() as root:
            s=PuttingSession(root,'Pace consistency',4,.3,1,2,random_pace=True,distance_model=MODEL_ID)
            before=s.data['target']
            s.add(record(1,before))
            self.assertTrue(s.data['shots'][0]['success'])
            self.assertAlmostEqual(s.data['shots'][0]['target_distance_ft'],distance_ft(before,10,MODEL_ID))
            self.assertAlmostEqual(s.data['target_distance_ft'],distance_ft(s.data['target'],10,MODEL_ID))
            old={k:v for k,v in s.data.items() if k not in ('distance_model','stimp','target_mode','target_distance_ft','distance_tolerance')}
            old['shots']=[];old['random_pace']=False
            s.path.write_text(json.dumps(old))
            legacy=PuttingSession.load(s.path);legacy.add(record(2,4))
            self.assertNotIn('estimated_distance_ft',legacy.data['shots'][0])
            self.assertNotIn('distance_model',legacy.data)

    def test_sqlite_api_drill_lifecycle_export_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as root:
            service=GolfService(Path(root),capture_detector=lambda:False)
            with TestClient(create_app(service),base_url='http://localhost') as client:
                self.assertIn('ladder',[d['id'] for d in client.get('/api/drills').json()])
                params=dict(drill='Putting ladder',distance_model=MODEL_ID,ladder_end=10,ladder_rounds=1,stimp=11,distance_tolerance=.5)
                launched=client.post('/api/practice',json=params).json()['practice'];sid=launched['id']
                service.ingest(record(1,launched['target']))
                self.assertEqual(client.post('/api/practice',json=params).status_code,409)
                service.ingest(record(2,service.practice.data['target']))
                saved=client.get('/api/sessions/'+sid).json()['practice']
                self.assertTrue(saved['ended']);self.assertEqual(len(saved['shots']),2)
                self.assertEqual(saved['distance_model']['id'],MODEL_ID)
                client.post('/api/sessions/'+sid+'/exclude',json={'key':'fixture:1'})
                response=client.get('/api/exports/csv')
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    rows=list(csv.DictReader(io.StringIO(z.read('session_attempts.csv').decode())))
                    self.assertEqual(rows[0]['excluded'],'1')
                    self.assertEqual(rows[0]['distance_model_id'],MODEL_ID)
                    self.assertAlmostEqual(float(rows[0]['estimated_distance_ft']),5)
                    self.assertEqual(rows[0]['stimp_ft'],'11.0')
                    self.assertEqual(json.loads(z.read('putting_models.json'))[sid]['slope_percent'],0)
                    metrics=list(csv.DictReader(io.StringIO(z.read('metric_values.csv').decode())))
                    self.assertFalse(any('distance' in row['metric_key'] for row in metrics))
                snapshot=Path(client.post('/api/storage/backup',json={}).json()['path'])
                restored=Path(root)/'restored.sqlite3';restore_snapshot(snapshot,restored)
                store=Store(restored)
                try:
                    self.assertEqual(store.load_session(sid)['shots'][1]['estimated_distance_ft'],saved['shots'][1]['estimated_distance_ft'])
                finally: store.close()
                self.assertEqual(client.delete('/api/sessions/'+sid).status_code,200)
                self.assertEqual(client.post('/api/sessions/'+sid+'/restore',json={}).status_code,200)
                reviewed=client.get('/api/sessions/'+sid).json()
                self.assertEqual(reviewed['summary']['count'],1)
                params['ladder_direction']='descending'
                launched=client.post('/api/practice',json=params).json()['practice']
                sid=launched['id'];service.ingest(record(3,launched['target']))
                self.assertEqual(client.post('/api/practice/'+sid+'/abandon',json={}).status_code,200)
                self.assertTrue(client.get('/api/sessions/'+sid).json()['practice']['abandoned'])

    def test_api_validation_leaves_no_partial_session(self):
        with tempfile.TemporaryDirectory() as root:
            service=GolfService(Path(root),capture_detector=lambda:False)
            with TestClient(create_app(service),base_url='http://localhost') as client:
                for payload in (dict(drill='Putting ladder',ladder_step=7),dict(drill='Putting ladder',stimp=0),
                                dict(drill='Start line',target_mode='distance'),dict(drill='Putting ladder',random_pace=True)):
                    self.assertIn(client.post('/api/practice',json=payload).status_code,(409,422))
                self.assertEqual(client.get('/api/sessions').json(),[])
                self.assertIsNone(service.practice)
