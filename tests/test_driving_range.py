import asyncio
import copy
import csv
import io
import json
import math
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from flight_model import predict, MODEL
from web_app import create_app
from web_service import GolfService

VALUES=dict(ball_speed=120,launch_ang=18,launch_dir=2,total_spin=5000,spin_axis=8,
            carry=170,total=184,offline=12,peak_height=83)


class FlightTests(unittest.TestCase):
    def test_native_model_units_input_isolation_and_endpoints(self):
        f=predict(VALUES)
        self.assertEqual(f['status'],'ready')
        self.assertAlmostEqual(f['inputs']['ball_speed_meters_per_second'],53.6448)
        self.assertNotIn('carry',f['inputs'])
        p=f['carry_point_yd'];t=f['total_point_yd']
        self.assertAlmostEqual(math.hypot(p['forward'],p['right']),f['metrics']['carry_yd'],places=3)
        self.assertAlmostEqual(math.hypot(t['forward'],t['right']),f['metrics']['total_yd'],places=3)
        self.assertGreater(t['right'],p['right'])
        self.assertEqual(f['trajectory'][0]['t'],0)
        self.assertLess(abs(f['trajectory'][-1]['z']),.2)
        other=predict(dict(VALUES,carry=300,total=320,offline=-100))
        self.assertEqual(other,f)

    def test_mirrored_inputs_and_handed_labels(self):
        r=predict(VALUES);l=predict(dict(VALUES,launch_dir=-2,spin_axis=-8))
        self.assertAlmostEqual(r['metrics']['carry_yd'],l['metrics']['carry_yd'],places=7)
        self.assertAlmostEqual(r['carry_point_yd']['right'],-l['carry_point_yd']['right'],places=7)
        self.assertNotEqual(r['shape'],predict(VALUES,'left_handed')['shape'])

    def test_missing_zero_and_failures(self):
        for bad in (None,float('nan'),True,25000):
            self.assertEqual(predict(dict(VALUES,total_spin=bad))['status'],'unavailable')
        self.assertEqual(predict(dict(VALUES,total_spin=0,spin_axis=0,launch_dir=0))['status'],'ready')
        with patch('opengolfcoach.calculate_derived_values',side_effect=ValueError('test failure')):
            self.assertEqual(predict(VALUES)['status'],'unavailable')


class RangeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')
        self.bag=self.service.equipment['bags'][0]
        self.club=self.bag['clubs'][0]

    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()

    def launch(self,**extra):
        r=self.client.post('/api/practice',json=dict(drill='Driving range',range_bag_id=self.bag['id'],range_club_id=self.club['id'],**extra))
        self.assertEqual(r.status_code,200,r.text)
        self.sid=r.json()['practice']['id'];return r.json()['practice']

    def shot(self,seq=1,**extra):
        e=dict(kind='record',session_id='range-test',seq=seq,receipt_id=f'range-test-{seq}',
               result='validated',practice_session_id=self.sid,vals=copy.deepcopy(VALUES),**extra)
        self.service.ingest(e);return e

    def cleanup(self,action,**extra):
        d=self.service.practice.data
        params=dict(action=action,keys=[s['key'] for s in d['shots']],revision=d['cleanup_revision'],reason='Test cleanup')
        params.update(extra)
        return self.client.post(f'/api/range/{self.sid}/cleanup',json=params)

    def test_open_ended_deduplicated_and_durable(self):
        self.launch();e=self.shot();self.service.ingest(e)
        self.shot(2)
        saved=self.service.load_session(self.sid)
        self.assertEqual(saved.data['session_kind'],'driving_range')
        self.assertIsNone(saved.data['ended']);self.assertEqual(len(saved.data['shots']),2)
        self.assertEqual(saved.data['shots'][0]['flight']['model'],MODEL)
        self.assertEqual(saved.summary()['count'],2)
        self.assertEqual(self.service.store.connection.execute('select count(*) from shots').fetchone()[0],2)

    def test_missing_flight_still_saves_reported_shot(self):
        self.launch()
        with patch('opengolfcoach.calculate_derived_values',side_effect=RuntimeError('offline')):
            self.shot()
        s=self.service.practice.data['shots'][0]
        self.assertEqual(s['flight']['status'],'unavailable');self.assertEqual(s['vals']['carry'],170)

    def test_bulk_retag_preserves_measurements_original_and_prediction(self):
        self.launch();self.shot();self.shot(2)
        before=copy.deepcopy(self.service.practice.data['shots'])
        new=self.bag['clubs'][4]
        r=self.cleanup('retag',bag_id=self.bag['id'],club_id=new['id']);self.assertEqual(r.status_code,200,r.text)
        saved=self.service.load_session(self.sid).data['shots']
        for old,now in zip(before,saved):
            self.assertEqual(now['vals'],old['vals']);self.assertEqual(now['club_id'],old['club_id'])
            self.assertEqual(now['flight'],old['flight']);self.assertEqual(now['corrected_equipment']['club_id'],new['id'])
        self.assertEqual(self.service.practice.summary()['clubs'][0]['club'],new['label'])
        r=self.cleanup('undo',keys=[],batch_id=r.json()['batch_id']);self.assertEqual(r.status_code,200,r.text)
        self.assertIsNone(self.service.practice.data['shots'][0]['corrected_equipment'])

    def test_bulk_remove_restore_exclusion_and_undo(self):
        self.launch();self.shot();self.shot(2)
        self.assertEqual(self.cleanup('exclude').status_code,200)
        self.assertEqual(self.service.practice.summary()['count'],0)
        removal=self.cleanup('remove');self.assertEqual(removal.status_code,200)
        self.assertEqual(self.service.practice.summary()['removed'],2)
        self.assertEqual(self.cleanup('restore').status_code,200)
        self.assertEqual(self.service.practice.summary()['count'],0)
        self.assertEqual(self.cleanup('include').status_code,200)
        self.assertEqual(self.service.practice.summary()['count'],2)
        self.assertEqual(self.service.store.connection.execute('select count(*) from shots').fetchone()[0],2)

    def test_invalid_stale_and_failed_batches_are_atomic(self):
        self.launch();self.shot();before=copy.deepcopy(self.service.practice.data)
        for extra in ({'keys':['range-test:1','outside']},{'revision':99},{'reason':'  '},{'keys':[]}):
            self.assertEqual(self.cleanup('remove',**extra).status_code,409)
            self.assertEqual(before,self.service.practice.data)
        self.assertEqual(self.cleanup('retag',bag_id=self.bag['id'],club_id='not-in-bag').status_code,409)
        with patch.object(self.service.store,'save_session',side_effect=OSError('disk full')):
            self.assertEqual(self.cleanup('remove').status_code,500)
        self.assertEqual(before,self.service.practice.data)
        self.assertEqual(before,self.service.load_session(self.sid).data)

    def test_single_exclusion_invalidates_bulk_revision(self):
        self.launch();self.shot()
        self.assertEqual(self.client.post(f'/api/practice/{self.sid}/exclude',json={'key':'range-test:1'}).status_code,200)
        self.assertEqual(self.cleanup('remove',revision=0).status_code,409)

    def test_future_target_context_and_review_cleanup(self):
        self.launch();self.shot()
        self.assertEqual(self.client.post(f'/api/range/{self.sid}/target',json={'target':90,'width':20,'depth':10}).status_code,200)
        self.shot(2,range_context={'range_target':150,'range_width':30,'range_depth':20})
        self.shot(3)
        self.assertEqual([s['target_distance_yd'] for s in self.service.practice.data['shots']],[150,150,90])
        self.client.post(f'/api/practice/{self.sid}/finish',json={})
        self.assertEqual(self.cleanup('remove').status_code,200)
        self.assertEqual(self.client.delete(f'/api/sessions/{self.sid}').status_code,200)
        self.assertEqual(self.client.post(f'/api/sessions/{self.sid}/restore',json={}).status_code,200)
        self.assertTrue(self.service.load_session(self.sid).data['ended'])

    def test_demo_guard_export_and_real_shot_separation(self):
        self.launch(demo=True)
        self.shot()
        self.assertEqual(len(self.service.practice.data['shots']),0)
        r=self.client.post(f'/api/range/{self.sid}/simulate',json={'count':10})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(self.service.practice.data['shots']),10)
        self.assertTrue(all(s['simulated'] for s in self.service.practice.data['shots']))
        self.assertTrue(all(isinstance(s['vals']['descent_ang'],(int,float)) for s in self.service.practice.data['shots']))
        self.assertTrue(all('descent' not in s['vals'] for s in self.service.practice.data['shots']))
        self.assertEqual(self.service.input.context()['practice_session_id'],None)
        with zipfile.ZipFile(io.BytesIO(self.service.store.export())) as z:
            rows=list(csv.DictReader(io.StringIO(z.read('shots.csv').decode('utf-8-sig'))))
            self.assertEqual(sum(r['simulated']=='True' for r in rows),10)
            attempts=list(csv.DictReader(io.StringIO(z.read('session_attempts.csv').decode('utf-8-sig'))))
            self.assertTrue(all(r['simulated']=='True' for r in attempts))
        self.client.post(f'/api/practice/{self.sid}/finish',json={})
        self.assertEqual(self.client.post(f'/api/range/{self.sid}/simulate',json={'count':1}).status_code,409)
        self.launch()
        self.assertEqual(self.client.post(f'/api/range/{self.sid}/simulate',json={'count':1}).status_code,409)

    def test_selection_freezes_with_receipt(self):
        self.launch();old=copy.deepcopy(self.service.practice.data['equipment_selection'])
        new=self.bag['clubs'][4]
        self.client.post(f'/api/practice/{self.sid}/equipment',json=dict(bag_id=self.bag['id'],club_id=new['id']))
        self.shot(equipment_selection=old);self.shot(2)
        self.assertEqual([s['club_id'] for s in self.service.practice.data['shots']],[old['club_id'],new['id']])
