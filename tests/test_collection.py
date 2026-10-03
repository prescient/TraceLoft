import asyncio
import tempfile
import unittest
from fastapi.testclient import TestClient
from web_service import GolfService
from web_app import create_app
from collection import CollectionSession


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)
        self.client=TestClient(create_app(self.service),base_url='http://localhost')
        self.bag=self.service.equipment['bags'][0]
        self.ids=[c['id'] for c in self.bag['clubs'][6:8]]

    def tearDown(self):
        self.client.close();asyncio.run(self.service.shutdown());self.temp.cleanup()

    def launch(self,**extra):
        return self.client.post('/api/practice',json=dict(drill='Bag mapping',range_bag_id=self.bag['id'],
            collection_clubs=self.ids,collection_samples=5,demo=True,**extra))

    def test_plan_roundtrip_selection_cleanup_and_recovery(self):
        response=self.launch();self.assertEqual(response.status_code,200,response.text)
        data=response.json()['practice'];sid=data['id']
        self.assertEqual(len(data['collection_plan']),2)
        self.assertEqual(self.client.post(f'/api/range/{sid}/simulate',json={'count':10}).status_code,200)
        old=self.service.practice.data['shots'][0]['club_id']
        self.assertEqual(self.client.post(f'/api/practice/{sid}/equipment',json={'bag_id':self.bag['id'],'club_id':self.ids[1]}).status_code,200)
        self.client.post(f'/api/range/{sid}/simulate',json={'count':1})
        self.assertEqual(self.service.practice.data['shots'][0]['club_id'],old)
        self.assertEqual(self.service.practice.data['shots'][-1]['club_id'],self.ids[1])
        self.client.post(f'/api/range/{sid}/cleanup',json={'action':'exclude','keys':[self.service.practice.data['shots'][0]['key']], 'revision':0,'reason':'Warmup'})
        self.client.post(f'/api/practice/{sid}/finish',json={})
        restored=self.service.load_session(sid)
        self.assertIsInstance(restored,CollectionSession)
        self.assertEqual(restored.summary()['count'],10)
        self.assertEqual(restored.data['collection_plan'],data['collection_plan'])
        self.client.delete(f'/api/sessions/{sid}')
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/restore',json={}).status_code,200)
        self.assertEqual(len(self.service.load_session(sid).data['shots']),11)

    def test_invalid_plan_and_live_demo_separation(self):
        for clubs in ([],[self.ids[0],self.ids[0]],['unknown']):
            r=self.client.post('/api/practice',json={'drill':'Bag mapping','range_bag_id':self.bag['id'],'collection_clubs':clubs})
            self.assertEqual(r.status_code,409,r.text)
        self.launch();p=self.service.practice
        self.assertFalse(p.add(dict(session_id='live',seq=1,result='validated',vals={'ball_speed':100,'launch_ang':20,'launch_dir':0})))
        self.assertEqual(p.data['shots'],[])

    def test_wedge_context_frozen_selection_and_missing_label(self):
        r=self.client.post('/api/practice',json=dict(drill='Wedge matrix',range_bag_id=self.bag['id'],collection_clubs=self.ids,swing_labels=['Half','Full'],demo=True))
        self.assertEqual(r.status_code,200,r.text);sid=r.json()['practice']['id']
        self.client.post(f'/api/range/{sid}/simulate',json={'count':1})
        self.assertEqual(self.service.practice.data['shots'][0]['swing_label'],'Half')
        self.client.post(f'/api/collection/{sid}/cell',json={'club_id':self.ids[1],'swing_label':'Full'})
        from driving_range import demo_event
        event=demo_event(self.service.practice,2);event['collection_context']={'swing_label':'Half'}
        self.service.practice.add(event)
        self.assertEqual(self.service.practice.data['shots'][-1]['swing_label'],'Half')
        event=demo_event(self.service.practice,3);event['collection_context']=None
        self.service.practice.add(event)
        self.assertIsNone(self.service.practice.data['shots'][-1]['swing_label'])
        self.assertEqual(self.service.load_session(sid).data['swing_label'],'Full')
        bad=self.client.post(f'/api/collection/{sid}/cell',json={'club_id':self.ids[1],'swing_label':'Unknown'})
        self.assertEqual(bad.status_code,409)
