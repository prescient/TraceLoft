"""Artwork registration and real API round journeys for the original hole pack."""
import asyncio
import copy
import math
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from bundled_courses import load_bundled, COURSE_IDS
from course_geometry import classify
from course_workbench import validate_edits
from golf_sim import GolfSimSession
from web_service import GolfService
from web_app import create_app

PIXELS = {
    'willow-cove-155-v1': {'tee':(205,426),'green':(1415,436),'fairway':(950,460),'sand':(1250,294),'water':(1500,100),'rough':(965,575),'nature':(200,150)},
    'pine-bend-365-v1': {'tee':(129,151),'green':(1612,480),'fairway':(1090,544),'sand':(880,313),'rough':(1450,632),'nature':(900,170)},
    'meadow-reach-525-v1': {'tee':(97,197),'green':(1658,296),'fairway':(860,486),'sand':(1070,317),'water':(1500,500),'rough':(1000,552),'nature':(850,170)},
}

def world(c,p):
    a,b,d,e,f,g=c['image']['transform'];x,y=p
    return [b*x+e*y+g,a*x+d*y+f]


class FictionalGeometryTests(unittest.TestCase):
    def test_registration_scale_surfaces_and_assets(self):
        for identity,samples in PIXELS.items():
            with self.subTest(hole=identity):
                c=load_bundled(identity)
                validate_edits({k:c[k] for k in ('surfaces','boundary','tee','pin')})
                route=c['playing_line']
                self.assertAlmostEqual(sum(math.dist(a,b) for a,b in zip(route,route[1:])),c['yards'],places=4)
                self.assertAlmostEqual(math.dist(world(c,[0,0]),world(c,[100,0])),math.dist(world(c,[0,0]),world(c,[0,100])))
                for lie,p in samples.items():self.assertEqual(classify(world(c,p),c),lie,(identity,lie))
                self.assertEqual(classify(world(c,[-1,400]),c),'out of bounds')
                self.assertTrue((Path(__file__).parents[1]/'web/art'/f'{identity}.png').exists())
                # Sample the intended safe route; its center must avoid water/sand/nature.
                for a,b in zip(route,route[1:]):
                    for t in range(21):
                        p=[a[i]+(b[i]-a[i])*t/20 for i in (0,1)]
                        self.assertIn(classify(p,c),('tee','fairway','green','rough'))

    def test_constructor_uses_independent_versioned_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            for identity in PIXELS:
                p=GolfSimSession(folder,game_course_id=identity)
                c=load_bundled(identity);c['pin'][0]+=99
                self.assertNotEqual(c['pin'],p.data['course']['pin'])
            with self.assertRaises(ValueError):load_bundled('../../README')


class FictionalPlayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')
    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()
    def launch(self,identity):
        r=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id=identity,game_gimme=0))
        self.assertEqual(r.status_code,200,r.text)
        return self.service.practice
    def hit(self,p,target):
        g=p.data['game'];sid=p.data['id'];d=math.dist(g['position'],target)
        r=self.client.post(f'/api/game/{sid}/aim',json=dict(x=target[0],y=target[1],turn=g['turn']))
        self.assertEqual(r.status_code,200,r.text)
        factor=1-p.data['game_settings'].get(g['lie']+'_percent',0)/100
        r=self.client.post(f'/api/game/{sid}/simulate',json=dict(distance_yd=d/factor,offline_yd=0,turn=g['turn']))
        self.assertEqual(r.status_code,200,r.text)
    def test_library_and_full_rounds_putting_review_and_exclusion(self):
        rows=self.client.get('/api/courses').json()
        self.assertEqual([c['id'] for c in rows],list(COURSE_IDS))
        for identity in PIXELS:
            with self.subTest(hole=identity):
                p=self.launch(identity);c=p.data['course'];sid=p.data['id']
                original=copy.deepcopy(c)
                self.assertEqual(self.client.get(c['image']['href']).status_code,200)
                for point in c['playing_line'][1:-1]:self.hit(p,point)
                last=c['playing_line'][-2];pin=c['pin'];d=math.dist(last,pin)
                approach=[pin[i]+(last[i]-pin[i])*4/d for i in (0,1)]
                self.hit(p,approach)
                self.assertEqual(p.data['game']['lie'],'green')
                self.assertAlmostEqual(p.summary()['remaining_yd'],4,places=4)
                self.assertGreater(p.summary()['required_pace_mph'],0)
                self.hit(p,pin)
                self.assertTrue(p.data['game']['holed'])
                self.assertEqual(p.data['game']['strokes'],len(c['playing_line']))
                self.assertEqual(p.data['game']['penalties'],0)
                self.assertEqual(p.data['game']['concessions'],0)
                saved=copy.deepcopy(p.data)
                self.assertEqual(self.service.load_session(sid).data,saved)
                self.client.post(f'/api/sessions/{sid}/exclude',json={'key':p.data['shots'][0]['key']})
                self.assertEqual(p.data['game'],saved['game'])
                self.assertEqual(p.data['course'],original)
                r=self.client.post(f'/api/game/{sid}/simulate',json=dict(distance_yd=1,offline_yd=0,turn=p.data['game']['turn']))
                self.assertEqual(r.status_code,409)

    def test_hazard_penalty_replays_then_sand_reduction_and_lifecycle(self):
        for identity,samples in PIXELS.items():
            with self.subTest(hole=identity):
                p=self.launch(identity);c=p.data['course'];sid=p.data['id']
                if 'water' in samples:
                    self.hit(p,world(c,samples['water']))
                    self.assertEqual(p.data['game']['position'],c['tee'])
                    self.assertEqual(p.data['game']['penalties'],1)
                    self.assertEqual(p.data['game']['strokes'],2)
                self.hit(p,world(c,samples['sand']))
                self.assertEqual(p.data['game']['lie'],'sand')
                self.hit(p,world(c,samples['fairway']))
                self.assertEqual(p.data['game']['lie'],'fairway')
                self.assertAlmostEqual(p.data['shots'][-1]['game_outcome']['distance_factor'],.8)
                p.finish()
                self.assertEqual(self.service.load_session(sid).data['game'],p.data['game'])
