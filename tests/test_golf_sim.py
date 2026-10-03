import asyncio
import copy
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from golf_sim import GolfSimSession, COURSE, lie_at, simulated_event
from web_service import GolfService
from web_app import create_app


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')

    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()

    def launch(self,**extra):
        r=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id='meadow-one-v1',**extra))
        self.assertEqual(r.status_code,200,r.text)
        return self.service.practice

    def simulate(self,p,distance,offline=0,turn=None):
        return self.client.post(f"/api/game/{p.data['id']}/simulate",json=dict(distance_yd=distance,
            offline_yd=offline,turn=p.data['game']['turn'] if turn is None else turn))

    def test_round_putt_completion_and_recoverable_review(self):
        p=self.launch();sid=p.data['id']
        self.assertEqual(self.simulate(p,200).status_code,200)
        self.assertEqual(self.simulate(p,145).status_code,200)
        self.assertEqual(p.data['game']['lie'],'green')
        self.assertAlmostEqual(p.summary()['remaining_yd'],5)
        self.assertGreater(p.summary()['required_pace_mph'],0)
        self.assertEqual(self.simulate(p,4.5).status_code,200)
        self.assertTrue(p.data['game']['holed']);self.assertEqual(p.summary()['strokes'],4)
        self.assertEqual(p.summary()['concessions'],1)
        saved=copy.deepcopy(p.data)
        self.assertEqual(self.simulate(p,10).status_code,409)
        self.assertIsInstance(self.service.load_session(sid),GolfSimSession)
        self.assertEqual(self.service.load_session(sid).data,saved)
        self.client.post(f'/api/sessions/{sid}/exclude',json={'key':p.data['shots'][0]['key']})
        self.assertEqual(p.summary()['strokes'],4)
        self.client.delete(f'/api/sessions/{sid}')
        self.client.post(f'/api/sessions/{sid}/restore',json={})
        self.assertEqual(self.service.load_session(sid).summary()['strokes'],4)

    def test_default_aerial_course_uses_its_own_aim_bounds(self):
        r=self.client.post('/api/practice',json={'drill':'2D golf','demo':True})
        self.assertEqual(r.status_code,200)
        p=self.service.practice;self.assertEqual(p.data['course']['id'],'meadow-one-v2')
        url=f"/api/game/{p.data['id']}/aim"
        self.assertEqual(self.client.post(url,json={'x':100,'y':100,'turn':0}).status_code,200)
        self.assertEqual(self.simulate(p,30).status_code,200)
        self.assertEqual(p.data['game']['turn'],1)
        self.assertEqual(self.client.post(url,json={'x':500,'y':100,'turn':1}).status_code,409)

    def test_duplicate_stale_context_missing_results_and_live_separation(self):
        p=self.launch();event=simulated_event(p,100)
        self.assertTrue(p.add(event));self.assertFalse(p.add(event))
        duplicate=copy.deepcopy(event);duplicate['seq']=99
        self.assertFalse(p.add(duplicate))
        self.assertEqual(self.simulate(p,100,turn=0).status_code,409)
        event=simulated_event(p,100);event['game_context']['turn']=0
        self.assertTrue(p.add(event));self.assertFalse(p.data['shots'][-1]['scored'])
        self.assertEqual(p.data['game']['turn'],1)
        event=simulated_event(p,100);event['vals']['offline']=None
        self.assertTrue(p.add(event));self.assertEqual(p.data['game']['position'],[0,100])
        event=simulated_event(p,100);event['simulated']=False
        self.assertFalse(p.add(event))

    def test_three_shots_penalty_and_gimme_are_five_not_four(self):
        p=self.launch()
        self.assertEqual(self.simulate(p,200).status_code,200)
        p.set_aim(80,200,1)
        self.assertEqual(self.simulate(p,150).status_code,200)
        self.assertEqual(p.data['game']['strokes'],3)
        self.assertEqual(p.data['game']['position'],[0,200])
        p.set_aim(0,350,2)
        self.assertEqual(self.simulate(p,149.5).status_code,200)
        self.assertEqual(len(p.data['shots']),3)
        self.assertEqual(p.summary()['strokes'],5)
        self.assertEqual(p.summary()['penalties'],1)
        self.assertEqual(p.summary()['concessions'],1)
        self.assertEqual([s['game_outcome']['after']['strokes'] for s in p.data['shots']],[1,3,5])
        self.assertEqual(self.service.load_session(p.data['id']).summary()['strokes'],5)

    def test_actual_hole_out_does_not_add_gimme_stroke(self):
        p=self.launch()
        self.simulate(p,200)
        self.simulate(p,150)
        self.assertTrue(p.data['game']['holed'])
        self.assertEqual(p.summary()['strokes'],2)
        self.assertEqual(p.summary()['concessions'],0)

    def test_rotation_geometry_and_raw_values(self):
        p=self.launch(game_geometry='radial')
        p.set_aim(70,0,0)
        event=simulated_event(p,50,30);raw=copy.deepcopy(event['vals']);p.add(event)
        self.assertEqual(p.data['game']['position'],[0,0])
        # OB returns to start, but the immutable attempted endpoint preserves this rotation.
        o=p.data['shots'][-1]['game_outcome']
        self.assertAlmostEqual(o['endpoint'][0],40);self.assertAlmostEqual(o['endpoint'][1],-30)
        self.assertEqual(p.data['shots'][-1]['vals'],raw)

    def test_water_penalty_replay_and_lie_classification(self):
        p=self.launch();self.simulate(p,225,-43)
        self.assertEqual(p.summary()['strokes'],2);self.assertEqual(p.summary()['penalties'],1)
        self.assertEqual(p.data['game']['position'],[0,0])
        self.assertEqual(p.data['shots'][0]['game_outcome']['destination_lie'],'water')
        for point,lie in (([0,350],'green'),([23,348],'sand'),([65,100],'nature'),([40,100],'rough'),([100,100],'out of bounds')):
            self.assertEqual(lie_at(point,COURSE),lie)

    def test_aim_is_frozen_at_acceptance_even_if_changed_before_delivery(self):
        p=self.launch();event=simulated_event(p,100)
        p.set_aim(40,100,0)
        self.assertTrue(p.add(event))
        self.assertEqual(p.data['game']['position'],[0,100])
        self.assertEqual(p.data['shots'][-1]['game_outcome']['context']['aim'],[0,350])

    def test_starting_lie_reduction_and_stable_random_draw(self):
        p=self.launch(game_variation=3)
        self.simulate(p,100,40);self.assertEqual(p.data['game']['lie'],'rough')
        event=simulated_event(p,100);p.add(event);o=p.data['shots'][-1]['game_outcome']
        self.assertAlmostEqual(o['distance_factor'],.93);self.assertLessEqual(abs(o['random_degrees']),3)
        saved=self.service.load_session(p.data['id'])
        self.assertEqual(saved.data['shots'][-1]['game_outcome'],o)

    def test_live_acknowledgement_context_and_demo_endpoint_guard(self):
        r=self.client.post('/api/practice',json={'drill':'2D golf','demo':False})
        self.assertEqual(r.status_code,409)
        r=self.client.post('/api/practice',json={'drill':'2D golf','demo':False,'game_acknowledged':True,'game_course_id':'meadow-one-v1'})
        self.assertEqual(r.status_code,200)
        p=self.service.practice
        self.assertEqual(self.simulate(p,100).status_code,409)
        import json
        self.assertEqual(self.service.input.context()['game_context'],p.context())
        event=dict(kind='record',session_id='live-test',seq=1,result='validated',practice_session_id=p.data['id'],
            game_context=p.context(),vals=dict(ball_speed=100,launch_ang=20,launch_dir=0,total=100,offline=0))
        self.service.ingest(event)
        self.assertEqual(p.data['game']['turn'],1)
        self.assertEqual(self.service.input.context()['game_context']['turn'],1)

    def test_recommendations_respect_demo_bag_exclusions_and_swing(self):
        bag=self.service.equipment['bags'][0];clubs=[bag['clubs'][10]['id']]
        self.client.post('/api/practice',json=dict(drill='Wedge matrix',range_bag_id=bag['id'],collection_clubs=clubs,swing_labels=['Half'],demo=True))
        coll=self.service.practice;sid=coll.data['id']
        self.client.post(f'/api/range/{sid}/simulate',json={'count':10})
        self.client.post(f'/api/practice/{sid}/finish',json={})
        p=self.launch(range_bag_id=bag['id'],range_club_id=clubs[0])
        rows=self.service.game_recommendations(p.data['id'])
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['count'],10);self.assertEqual(rows[0]['swing_label'],'Half')
        self.service.cleanup_range(sid,dict(action='exclude',keys=[s['key'] for s in coll.data['shots'][:6]],revision=0,reason='QA'))
        self.assertEqual(self.service.game_recommendations(p.data['id']),[])

    def test_failed_simulation_rolls_back_receipt_and_position(self):
        p=self.launch();before=copy.deepcopy(p.data)
        events=self.service.store.connection.execute('SELECT count(*) FROM ingest_events').fetchone()[0]
        with patch.object(p,'save',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):self.service.game_action(p.data['id'],'simulate',dict(distance_yd=100,offline_yd=0,turn=0))
        self.assertEqual(p.data,before)
        self.assertEqual(self.service.load_session(p.data['id']).data,before)
        self.assertEqual(self.service.store.connection.execute('SELECT count(*) FROM ingest_events').fetchone()[0],events)

