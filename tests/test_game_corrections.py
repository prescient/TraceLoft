import asyncio
import copy
import math
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from golf_sim import simulated_event
from web_service import GolfService
from web_app import create_app


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')
    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()
    def launch(self,course='meadow-one-v1'):
        r=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id=course))
        self.assertEqual(r.status_code,200,r.text)
        self.p=self.service.practice
        return self.p
    def action(self,action,**params):
        return self.client.post(f"/api/game/{self.p.data['id']}/{action}",json=dict(turn=self.p.data['game']['turn'],**params))
    def hit(self,d,offline=0):
        r=self.action('simulate',distance_yd=d,offline_yd=offline)
        self.assertEqual(r.status_code,200,r.text)
    def correct(self,kind='misread'):
        return self.action('correct',kind=kind,key=self.p.latest_played_shot()['key'])
    def holeout(self):
        p=self.p;g=p.data['game'];pin=p.data['course']['pin']
        self.assertEqual(self.action('aim',x=pin[0],y=pin[1]).status_code,200)
        self.hit(math.dist(g['position'],pin)/(1-p.data['game_settings'].get(g['lie']+'_percent',0)/100))
    def test_penalty_gimme_and_evidence(self):
        p=self.launch();self.hit(200)
        self.action('aim',x=80,y=200);self.hit(150)
        original=copy.deepcopy(p.data['shots'][-1])
        self.assertEqual(p.summary()['strokes'],3)
        self.assertEqual(self.correct('mulligan').status_code,200)
        self.assertEqual((p.summary()['strokes'],p.summary()['penalties']),(1,0))
        shot=p.data['shots'][-1]
        for field in ('vals','game_outcome','receipt_id','scored'):self.assertEqual(shot[field],original[field])
        self.assertFalse(shot['excluded'])
        self.action('aim',x=0,y=350);self.hit(149.5)
        self.assertTrue(p.data['ended']);self.assertEqual(p.summary()['concessions'],1)
        self.assertEqual(self.correct().status_code,200)
        self.assertIsNone(p.data['ended']);self.assertFalse(p.data['game']['holed'])
        self.assertEqual((p.summary()['strokes'],p.summary()['concessions']),(1,0))
        self.assertTrue(p.data['shots'][-1]['excluded'])
        decisions=self.service.store.connection.execute("SELECT reason FROM inclusion_decisions WHERE session_id=?",(p.data['id'],)).fetchall()
        self.assertEqual([r['reason'] for r in decisions],['game_misread'])
        self.assertEqual(p.data['game']['position'],[0,200])
        self.assertEqual((p.summary()['scored'],p.summary()['mulligans'],p.summary()['misreads']),(1,1,1))
        self.assertEqual(self.service.load_session(p.data['id']).data,p.data)
        self.holeout();self.assertEqual(p.summary()['strokes'],2)
    def test_stale_double_click_and_inflight_read(self):
        p=self.launch();self.hit(100);late=simulated_event(p,50)
        params=dict(turn=p.data['game']['turn'],kind='misread',key=p.latest_played_shot()['key'])
        self.assertEqual(self.correct().status_code,200)
        url=f"/api/game/{p.data['id']}/correct"
        self.assertEqual(self.client.post(url,json=params).status_code,409)
        self.assertTrue(p.add(late));self.assertFalse(p.data['shots'][-1]['scored'])
        self.assertEqual(p.summary()['strokes'],0)
        self.assertIsNone(p.latest_played_shot())
        self.hit(40);self.assertEqual(p.summary()['strokes'],1)
    def test_finished_hole_next_tee_and_sequential_undo(self):
        p=self.launch('pebble-boulder-blue-v1');self.holeout()
        self.assertEqual(self.action('next').status_code,200)
        self.assertEqual(p.data['round']['index'],1)
        self.assertEqual(self.correct().status_code,200)
        self.assertEqual(p.data['round']['index'],0)
        self.assertEqual(p.data['round']['results'],[])
        self.holeout();self.assertEqual(len(p.data['round']['results']),1)
        self.action('next');self.hit(100)
        self.correct('mulligan');self.correct('mulligan')
        self.assertEqual(p.summary()['strokes'],0)
        self.assertEqual(p.data['round']['index'],0)
        self.assertEqual(len(p.data['game_corrections']),3)
    def test_final_round_reopen_from_saved_review(self):
        p=self.launch('pebble-boulder-blue-v1')
        for i in range(18):
            self.holeout()
            if i<17:self.assertEqual(self.action('next').status_code,200)
        self.assertTrue(p.summary()['round_complete']);self.assertEqual(p.summary()['strokes'],18)
        sid=p.data['id'];self.service.practice=None
        self.assertEqual(self.correct().status_code,200)
        self.p=p=self.service.practice
        self.assertEqual(p.data['id'],sid);self.assertIsNone(p.data['ended'])
        self.assertEqual(p.summary()['holes_completed'],17);self.assertEqual(p.summary()['strokes'],17)
        self.assertEqual(p.data['course']['hole_number'],18)
        self.holeout();self.assertTrue(p.summary()['round_complete'])
        self.assertEqual(p.summary()['strokes'],18)
        self.assertEqual(len(p.data['round']['results']),18)
    def test_active_owner_abandoned_and_deleted_guards(self):
        p=self.launch();self.holeout();sid=p.data['id']
        params=dict(turn=p.data['game']['turn'],kind='misread',key=p.latest_played_shot()['key'])
        other=self.launch();url=f'/api/game/{sid}/correct'
        self.assertEqual(self.client.post(url,json=params).status_code,409)
        self.assertIs(self.service.practice,other)
        self.hit(10);other.abandon()
        self.assertEqual(self.correct().status_code,409)
        self.service.practice=None
        self.assertEqual(self.client.delete(f'/api/sessions/{sid}').status_code,200)
        self.assertEqual(self.client.post(url,json=params).status_code,404)
    def test_failed_audit_rolls_back_entire_correction(self):
        p=self.launch();self.hit(100);before=copy.deepcopy(p.data)
        params=dict(turn=p.data['game']['turn'],kind='misread',key=p.latest_played_shot()['key'])
        with patch.object(self.service.store,'_audit',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):self.service.correct_game(p.data['id'],params)
        self.assertEqual(p.data,before)
        self.assertEqual(self.service.load_session(p.data['id']).data,before)
        self.assertIs(self.service.practice,p)

    def test_live_round_context_and_manual_end_reopen(self):
        response=self.client.post('/api/practice',json=dict(drill='2D golf',demo=False,
            game_course_id='meadow-one-v1',game_acknowledged=True))
        self.assertEqual(response.status_code,200)
        self.p=p=self.service.practice
        event=dict(kind='record',session_id='live',seq=1,result='validated',simulated=False,
                   practice_session_id=p.data['id'],game_context=p.context(),
                   vals=dict(total=100,offline=0,ball_speed=65,launch_ang=15,launch_dir=0))
        self.service.ingest(event)
        self.assertEqual(p.summary()['strokes'],1)
        self.assertEqual(self.client.post(f"/api/practice/{p.data['id']}/finish",json={}).status_code,200)
        self.assertEqual(self.correct().status_code,200)
        self.assertIsNone(p.data['ended']);self.assertEqual(p.data['game']['turn'],2)
        self.assertEqual(p.data['game']['position'],[0,0])
        self.assertEqual(self.service.load_session(p.data['id']).data,p.data)
