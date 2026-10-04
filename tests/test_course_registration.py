"""Reviewed asset-pixel fixtures, current course journeys and legacy snapshots."""
import asyncio
import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from bundled_courses import COURSE_IDS, load_bundled
from course_geometry import classify, on_surface
from course_workbench import validate_edits
from web_app import create_app
from web_service import GolfService

ROOT = Path(__file__).resolve().parents[1]


def world(c, pixel):
    a,b,d,e,f,g = c['image']['transform']
    x,y = pixel
    return [b*x+e*y+g,a*x+d*y+f]


class RegistrationTests(unittest.TestCase):
    def test_all_36_reviewed_images_and_fixed_pixel_probes(self):
        review=json.loads((ROOT/'designs/course-registration/review.json').read_text())
        self.assertEqual({c['id'] for c in review['courses']},set(COURSE_IDS))
        for reviewed in review['courses']:
            package=load_bundled(reviewed['id'])
            legacy=ROOT/'courses'/f"{reviewed['legacy_id']}.json"
            self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(),reviewed['legacy_sha256'])
            self.assertEqual(package['version'],reviewed['version'])
            self.assertEqual(len(reviewed['holes']),18)
            for c,fixture in zip(package['holes'],reviewed['holes']):
                with self.subTest(course=package['id'],hole=c['hole_number']):
                    self.assertEqual(c['id'],fixture['id'])
                    validate_edits({k:c[k] for k in ('surfaces','boundary','tee','pin')})
                    fields={k:c[k] for k in ('surfaces','boundary','bounds','tee','pin','playing_line','image')}
                    digest=hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()
                    self.assertEqual(digest,fixture['geometry_sha256'])
                    raw=(ROOT/'web/art'/Path(c['image']['href']).name).read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(),fixture['art_sha256'])
                    self.assertEqual(c['provenance']['art_sha256'],fixture['art_sha256'])
                    a,b,d,e,_,_=c['image']['transform']
                    self.assertEqual((b,d),(0,0));self.assertEqual(a,e)
                    self.assertEqual(classify(c['tee'],c),'tee')
                    self.assertEqual(classify(c['pin'],c),'green')
                    self.assertEqual(classify(world(c,[-5,400]),c),'out of bounds')
                    self.assertAlmostEqual(sum(math.dist(p,q) for p,q in zip(c['playing_line'],c['playing_line'][1:])),c['yards'],places=3)
                    self.assertGreaterEqual(len(fixture['probes']),5)
                    for p in fixture['probes']:
                        self.assertEqual(classify(world(c,p['pixel']),c),p['lie'],p)

    def test_old_packages_remain_distinct_and_readable(self):
        for stem in ('pebble-boulder','sheboygan-straits'):
            old=load_bundled(stem+'-blue-v1');new=load_bundled(stem+'-blue-v2')
            self.assertEqual([h['yards'] for h in old['holes']],[h['yards'] for h in new['holes']])
            self.assertEqual([h['par'] for h in old['holes']],[h['par'] for h in new['holes']])
            self.assertEqual([h['image']['href'] for h in old['holes']],[h['image']['href'] for h in new['holes']])
            self.assertNotEqual(old['holes'][0]['surfaces'],new['holes'][0]['surfaces'])

    def test_v3_only_refines_three_fairways_and_keeps_visible_aprons_playable(self):
        old=load_bundled('pebble-boulder-blue-v2');new=load_bundled('pebble-boulder-blue-v3')
        points={6:[(1510,345),(1550,310),(1580,285),(1600,365)],
                16:[(1390,350),(830,244),(400,442)],
                18:[(1050,528),(1410,529),(1580,420)]}
        outside={6:((1480,280),'rough'),16:((1220,425),'nature'),18:((1250,605),'nature')}
        for previous,current in zip(old['holes'],new['holes']):
            number=current['hole_number']
            comparison=copy.deepcopy(current);comparison['id']=previous['id']
            if number in points:
                self.assertNotEqual(current['surfaces']['fairway'],previous['surfaces']['fairway'])
                comparison['surfaces']['fairway']=previous['surfaces']['fairway']
                comparison['provenance']=previous['provenance']
                for native in points[number]:
                    self.assertEqual(classify(world(current,[native[0]*1536/1774,native[1]*768/887]),current),'fairway')
                native,label=outside[number]
                self.assertEqual(classify(world(current,[native[0]*1536/1774,native[1]*768/887]),current),label)
                for v in current['surfaces']['green'][0]['outer']:
                    self.assertTrue(on_surface(v,current,'fairway'),'Putting apron disconnected from fairway')
            self.assertEqual(comparison,previous)

    def test_v2_snapshots_and_art_hashes_remain_intact(self):
        review=json.loads((ROOT/'designs/course-registration/review-v2.json').read_text())
        for reviewed in review['courses']:
            package=load_bundled(reviewed['id'])
            for c,fixture in zip(package['holes'],reviewed['holes']):
                fields={k:c[k] for k in ('surfaces','boundary','bounds','tee','pin','playing_line','image')}
                self.assertEqual(hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest(),fixture['geometry_sha256'])


class RevisedRoundTests(unittest.TestCase):
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

    def action(self,p,action,**args):
        return self.client.post(f"/api/game/{p.data['id']}/{action}",json=dict(turn=p.data['game']['turn'],**args))

    def hit(self,p,target,roll=0):
        g=p.data['game'];putting=g['lie']=='green'
        self.assertEqual(self.action(p,'aim',x=target[0],y=target[1]).status_code,200)
        factor=1-p.data['game_settings'].get(g['lie']+'_percent',0)/100 if not putting else 1
        carry=math.dist(g['position'],target)/factor
        params=dict(distance_yd=carry+roll,offline_yd=0)
        if not putting:params['carry_yd']=carry
        r=self.action(p,'simulate',**params)
        self.assertEqual(r.status_code,200,r.text)

    def test_both_current_courses_complete_with_putting_and_saved_review(self):
        self.assertEqual([c['id'] for c in self.client.get('/api/courses').json()],list(COURSE_IDS))
        for identity in COURSE_IDS:
            p=self.launch(identity);frozen=copy.deepcopy(p.data['round']['holes'])
            for index in range(18):
                c=p.data['course'];tee=c['tee'];pin=c['pin'];d=math.dist(tee,pin)
                with self.subTest(course=identity,hole=index+1):
                    approach=[pin[i]+(tee[i]-pin[i])*4/d for i in (0,1)]
                    self.hit(p,approach)
                    self.assertEqual(p.data['game']['lie'],'green')
                    self.hit(p,pin)
                    self.assertTrue(p.data['game']['holed'])
                    self.assertEqual(p.summary()['penalties'],0)
                    self.assertEqual(p.summary()['holes_completed'],index+1)
                    if index<17:self.assertEqual(self.action(p,'next').status_code,200)
            self.assertTrue(p.summary()['round_complete'])
            self.assertEqual(p.summary()['strokes'],36)
            self.assertEqual(p.data['round']['holes'],frozen)
            self.assertEqual(self.service.load_session(p.data['id']).data,p.data)

    def test_registered_bunker_landing_stops_before_reported_total_and_misread_restores(self):
        for identity in COURSE_IDS:
            p=self.launch(identity);c=p.data['course'];sand=c['hazard_test_points']['sand'][0]
            before=copy.deepcopy(p.data['game'])
            self.hit(p,sand,roll=20)
            o=p.data['shots'][-1]['game_outcome']
            self.assertEqual(o['landing_rollout']['landing_lie'],'sand')
            self.assertEqual(o['landing_rollout']['adjusted_rollout_yd'],0)
            self.assertEqual(p.data['game']['lie'],'sand')
            for a,b in zip(p.data['game']['position'],sand):self.assertAlmostEqual(a,b)
            self.assertEqual(self.action(p,'correct',kind='misread',key=p.data['shots'][-1]['key']).status_code,200)
            self.assertEqual(p.data['game']['position'],before['position'])
            self.assertEqual(p.data['game']['strokes'],before['strokes'])
            self.assertEqual(p.data['shots'][-1]['game_outcome'],o)
            p.finish()

    def test_legacy_active_round_resumes_with_its_original_course(self):
        p=self.launch('pebble-boulder-blue-v1');original=copy.deepcopy(p.data)
        self.service.practice=None
        self.service.resume_practice(p.data['id'])
        self.assertEqual(self.service.practice.data,original)
        self.assertEqual(self.service.practice.data['course'],load_bundled('pebble-boulder-blue-v1')['holes'][0])
        self.assertNotEqual(self.service.practice.data['course'],load_bundled('pebble-boulder-blue-v2')['holes'][0])
