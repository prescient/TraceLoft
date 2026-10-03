import asyncio
import copy
import math
import tempfile
import unittest
from fastapi.testclient import TestClient
from bundled_courses import load_bundled
from golf_sim import GolfSimSession
from web_service import GolfService
from web_app import create_app


class NineHoleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')

    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()

    def action(self,p,action,**args):
        return self.client.post(f"/api/game/{p.data['id']}/{action}",json=dict(turn=p.data['game']['turn'],**args))

    def holeout(self,p):
        pin=p.data['course']['pin'];g=p.data['game']
        self.assertEqual(self.action(p,'aim',x=pin[0],y=pin[1]).status_code,200)
        r=self.action(p,'simulate',distance_yd=math.dist(g['position'],pin),offline_yd=0)
        self.assertEqual(r.status_code,200,r.text)

    def test_both_courses_front_and_back_completion_review_resume_and_correction(self):
        for course in ('pebble-boulder-blue-v1','sheboygan-straits-blue-v1'):
            package=load_bundled(course);original=copy.deepcopy(package)
            for selected,start in (('front',1),('back',10)):
                with self.subTest(course=course,selection=selected):
                    response=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,
                        game_course_id=course,game_holes=selected,game_gimme=0))
                    self.assertEqual(response.status_code,200,response.text)
                    p=self.service.practice;sid=p.data['id'];r=p.data['round']
                    self.assertEqual([h['hole_number'] for h in r['holes']],list(range(start,start+9)))
                    self.assertEqual(r['par'],sum(h['par'] for h in package['holes'][start-1:start+8]))
                    self.assertEqual(r['yards'],sum(h['yards'] for h in package['holes'][start-1:start+8]))
                    for index in range(9):
                        self.assertEqual(p.data['course']['hole_number'],start+index)
                        self.holeout(p)
                        self.assertEqual(bool(p.data['ended']),index==8)
                        if index==0:
                            # Restoring the paused round must keep the selected nine and its numbering.
                            self.service.practice=None;self.service.resume_practice(sid);p=self.service.practice
                            self.assertEqual(p.data['round']['selection'],selected)
                        if index<8:self.assertEqual(self.action(p,'next').status_code,200)
                    self.assertEqual(p.summary()['hole_count'],9)
                    self.assertEqual(p.summary()['holes_completed'],9)
                    self.assertEqual(p.summary()['strokes'],9)
                    self.assertTrue(p.summary()['round_complete'])
                    self.assertEqual(self.action(p,'next').status_code,409)
                    saved=self.service.load_session(sid)
                    self.assertEqual(saved.data,p.data)
                    # A misread on hole 9/18 reopens that selected round, not the other nine.
                    self.service.practice=None
                    response=self.action(p,'correct',kind='misread',key=p.latest_played_shot()['key'])
                    self.assertEqual(response.status_code,200,response.text)
                    p=self.service.practice
                    self.assertIsNone(p.data['ended'])
                    self.assertEqual(p.data['course']['hole_number'],start+8)
                    self.assertEqual(p.summary()['holes_completed'],8)
                    self.assertEqual(p.summary()['strokes'],8)
                    self.assertTrue(p.data['shots'][-1]['excluded'])
                    self.holeout(p)
                    self.assertEqual(p.summary()['strokes'],9)
                    self.assertTrue(p.summary()['round_complete'])
                    self.assertEqual(p.summary()['round_selection'],selected)
                    self.assertEqual(load_bundled(course),original)

    def test_validation_catalog_and_legacy_default(self):
        catalog=self.client.get('/api/courses').json()
        for row in catalog:
            self.assertEqual([v['id'] for v in row['round_options']],['full','front','back'])
            self.assertEqual(sum(v['yards'] for v in row['round_options'][1:]),row['yards'])
        self.assertEqual(self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_holes='middle')).status_code,422)
        self.assertEqual(self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id='meadow-one-v1',game_holes='back')).status_code,409)
        self.assertIsNone(self.service.practice)
        with self.assertRaises(ValueError):GolfSimSession(self.temp.name,game_holes='invalid')
        p=GolfSimSession(self.temp.name)
        self.assertEqual(len(p.data['round']['holes']),18)
        # Previously saved sessions have no selection field; review remains full-course.
        p.data['round'].pop('selection')
        self.assertEqual(p.summary()['round_selection'],'full')
