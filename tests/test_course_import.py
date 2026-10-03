import asyncio
import copy
import json
import math
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from course_import import inspect, preview, save, catalog, load, ring, fetch_osm
from course_geometry import classify
from web_service import GolfService
from web_app import create_app

SCALE=.9144/6371008.8*180/math.pi
def coords(points):return [[x*SCALE,y*SCALE] for x,y in points]
def feature(kind,points,tag,identity):
    return dict(type='Feature',id=identity,properties={'golf':tag,'ref':'2','par':'4'},
                geometry=dict(type=kind,coordinates=[coords(points)] if kind=='Polygon' else coords(points)))
def source():
    return dict(type='FeatureCollection',features=[
        feature('LineString',[[0,0],[30,150],[0,300]],'hole','hole-2'),
        feature('Polygon',[[-20,280],[20,280],[20,320],[-20,320],[-20,280]],'green','g'),
        feature('Polygon',[[-25,-5],[35,-5],[35,280],[-25,280],[-25,-5]],'fairway','f'),
        feature('Polygon',[[35,180],[55,180],[55,210],[35,210],[35,180]],'bunker','b')])
def params():return dict(data=source(),hole_id='hole-2',name='Test hole',par=4,scorecard_yards=400,
                         source_url='https://example.org/course',tee_label='Test tee')


class GeometryImportTests(unittest.TestCase):
    def test_scale_dogleg_no_stretch_and_lies(self):
        data=params();original=copy.deepcopy(data);c=preview(**data)
        self.assertEqual(data,original)
        self.assertEqual(c['pin'],[0,300])
        self.assertAlmostEqual(c['provenance']['route_yards'],305.9,places=1)
        self.assertEqual(c['yards'],400)
        self.assertTrue(any('differ' in w for w in c['warnings']))
        self.assertEqual(classify([0,300],c),'green')
        self.assertEqual(classify([45,195],c),'sand')
        self.assertEqual(classify([0,0],c),'tee')

    def test_bad_geometry_and_missing_green(self):
        for bad in ([[0,0],[1,1],[0,1],[1,0]],[[0,0],[1,0],[0,0]],[[0,0],[1,float('nan')],[0,1]]):
            with self.assertRaises(ValueError):ring(bad)
        p=params();p['data']['features']=[p['data']['features'][0]]
        with self.assertRaisesRegex(ValueError,'mapped green'):preview(**p)
        p=params();p['source_url']='javascript:alert(1)'
        with self.assertRaises(ValueError):preview(**p)
        p=params();p['data']['crs']={'name':'EPSG:3857'}
        with self.assertRaises(ValueError):preview(**p)

    def test_multipolygon_holes_and_missing_fairway_warning(self):
        p=params();p['data']['features']=p['data']['features'][:2]
        outer=coords([[25,100],[55,100],[55,140],[25,140],[25,100]])
        inner=coords([[30,110],[40,110],[40,120],[30,120],[30,110]])
        p['data']['features'].append(dict(type='Feature',properties={'natural':'water'},geometry={'type':'MultiPolygon','coordinates':[[outer,inner]]}))
        c=preview(**p)
        self.assertEqual(classify([45,125],c),'water')
        self.assertEqual(classify([35,115],c),'rough')
        self.assertTrue(any('No mapped fairway' in w for w in c['warnings']))

    def test_download_failure_is_actionable(self):
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError,'saved GeoJSON'):fetch_osm(123)
        with self.assertRaises(ValueError):fetch_osm('https://example.com')


class ImportAPITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')
    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()

    def test_review_save_idempotency_launch_and_immutable_round(self):
        p=params()
        self.assertEqual(self.client.post('/api/courses/inspect',json={'data':p['data']}).json()['holes'][0]['id'],'hole-2')
        self.assertEqual(self.client.post('/api/courses/save',json=p).status_code,409)
        c=self.client.post('/api/courses/save',json=dict(p,reviewed=True)).json()
        self.assertEqual(self.client.post('/api/courses/save',json=dict(p,reviewed=True)).json()['id'],c['id'])
        self.assertEqual(len(catalog(self.service.store)),5)
        r=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id=c['id']))
        self.assertEqual(r.status_code,200,r.text);active=copy.deepcopy(self.service.practice.data)
        p['name']='Revision two';save(self.service.store,p,True)
        self.assertEqual(self.service.practice.data,active)
        self.assertEqual(self.service.load_session(active['id']).data['course'],c)
        self.assertEqual(len(catalog(self.service.store)),6)
        self.assertTrue(self.service.store.backup().exists())
        self.assertEqual(self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id=c['id'])).status_code,409)

    def test_invalid_course_and_preview_never_save(self):
        self.assertEqual(self.client.post('/api/courses/preview',json=params()).status_code,200)
        self.assertEqual(len(catalog(self.service.store)),4)
        self.assertIsNone(self.service.practice)
        r=self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id='../../evil'))
        self.assertEqual(r.status_code,409)

    def test_bundled_example_is_available_offline_and_warns_about_coverage(self):
        with patch('urllib.request.urlopen',side_effect=OSError('offline')):
            result=self.client.get('/api/courses/example')
        self.assertEqual(result.status_code,200)
        data=result.json()['data'];self.assertEqual(len(result.json()['holes']),27)
        c=preview(data,'way/692435441','Jackson Park · Hole 18 · prototype',4,
                  source_url='https://www.openstreetmap.org/way/23060588')
        self.assertTrue(any('coverage appears incomplete' in w for w in c['warnings']))
        self.assertEqual(c['provenance']['kind'],'osm_import')
        self.assertIn('ODbL',c['provenance']['attribution'])
