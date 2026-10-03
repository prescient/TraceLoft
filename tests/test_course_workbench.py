import copy
import json
from contextlib import closing
import unittest
from course_import import preview, catalog, load
from course_workbench import validate_edits
from tests import test_course_import as fixtures
params=fixtures.params


class WorkbenchTests(unittest.TestCase):
    setUp=fixtures.ImportAPITests.setUp
    tearDown=fixtures.ImportAPITests.tearDown
    def edit_params(self):
        p=params();c=preview(**p)
        p['edits']={k:copy.deepcopy(c[k]) for k in ('surfaces','boundary','tee','pin')}
        return p

    def test_incomplete_draft_can_be_repaired_but_not_published(self):
        p=params();p['data']['features']=p['data']['features'][:1]
        result=self.client.post('/api/courses/preview',json=p)
        self.assertEqual(result.status_code,200,result.text)
        c=result.json();self.assertTrue(c['blocking_issues'])
        saved=self.client.post('/api/course-drafts',json={'params':p}).json()
        self.assertEqual(self.client.get('/api/course-drafts/'+saved['id']).json()['params']['data'],p['data'])
        self.assertEqual(self.client.post('/api/courses/save',json=dict(p,reviewed=True)).status_code,409)
        p['edits']={k:c[k] for k in ('surfaces','boundary','tee','pin')}
        p['edits']['surfaces']['green']=[{'outer':[[-10,290],[10,290],[10,310],[-10,310]],'holes':[]}]
        result=self.client.post('/api/courses/save',json=dict(p,reviewed=True))
        self.assertEqual(result.status_code,200,result.text)
        self.assertFalse(result.json()['blocking_issues'])

    def test_draft_revision_and_versioned_round_do_not_change_active_session(self):
        p=self.edit_params();old_source=copy.deepcopy(p['data'])
        first=self.client.post('/api/course-drafts',json={'params':p}).json()
        p['edits']['surfaces']['water']=[{'outer':[[10,100],[20,100],[20,120],[10,120]],'holes':[]}]
        second=self.client.post('/api/course-drafts',json={'params':p,'id':first['id'],'revision':1}).json()
        self.assertEqual(second['revision'],2)
        self.assertEqual(self.client.post('/api/course-drafts',json={'params':p,'id':first['id'],'revision':1}).status_code,409)
        self.assertEqual(len(self.client.get('/api/course-drafts').json()),1)
        self.assertEqual(len(catalog(self.service.store)),4)
        c=self.client.post('/api/courses/save',json=dict(p,reviewed=True)).json()
        self.client.post('/api/practice',json=dict(drill='2D golf',demo=True,game_course_id=c['id']))
        active=copy.deepcopy(self.service.practice.data)
        p['edits']['tee']=[5,0];p['name']='Edited tee'
        newer=self.client.post('/api/courses/save',json=dict(p,reviewed=True)).json()
        self.assertNotEqual(c['id'],newer['id']);self.assertEqual(self.service.practice.data,active)
        self.assertEqual(load(self.service.store,c['id']),c);self.assertEqual(p['data'],old_source)
        snapshot=self.service.store.backup()
        import sqlite3
        with closing(sqlite3.connect(snapshot)) as con:
            backup=json.loads(con.execute('SELECT value FROM metadata WHERE key=?',('course_draft.v1.'+first['id'],)).fetchone()[0])
            self.assertEqual(backup,second)

    def test_geometry_validation_hazards_bounds_and_nonfinite(self):
        p=self.edit_params()
        for bad in (float('nan'),float('inf'),True,5001):
            e=copy.deepcopy(p['edits']);e['tee']=[bad,0]
            with self.assertRaises(ValueError):validate_edits(e)
        for outer in ([[0,0],[20,20],[0,20],[20,0]],[[0,0],[1,1]]):
            e=copy.deepcopy(p['edits']);e['surfaces']['water']=[dict(outer=outer,holes=[])]
            with self.assertRaises(ValueError):validate_edits(e)
        p['edits']['pin']=[0,250]
        self.assertTrue(preview(**p,allow_incomplete=True)['blocking_issues'])
        with self.assertRaises(ValueError):preview(**p)
        p['edits']['pin']=[0,300];p['edits']['tee']=[200,0]
        with self.assertRaisesRegex(ValueError,'boundary'):preview(**p)
        p['edits']['tee']=[0,0];p['edits']['surfaces']['water']=[dict(outer=[[-5,-5],[5,-5],[5,5],[-5,5]],holes=[])]
        with self.assertRaisesRegex(ValueError,'water or sand'):preview(**p)

    def test_geometry_identity_and_review_rejection(self):
        p=self.edit_params();old=preview(**p)
        self.assertEqual(self.client.post('/api/courses/save',json=p).status_code,409)
        p['edits']['pin']=[2,301]
        new=preview(**p)
        self.assertNotEqual(old['id'],new['id'])
        self.assertEqual(old['provenance']['transform'],new['provenance']['transform'])


    def test_draft_disk_reopen_and_portable_copy(self):
        from storage import Store
        from course_workbench import load_draft,save_draft,list_drafts
        p=self.edit_params()
        p['edits']['surfaces']['water']=[dict(outer=[[30,100],[50,100],[50,140],[30,140]],holes=[[[35,110],[40,110],[40,120],[35,120]]])]
        saved=save_draft(self.service.store,p)
        with closing(Store(self.service.store.path)) as reopened:
            restored=load_draft(reopened,saved['id'])
            self.assertEqual(restored,saved)
            portable=json.loads(json.dumps(dict(format='traceloft-course-draft-v1',params=restored['params'])))
            separate=save_draft(reopened,portable['params'])
            self.assertNotEqual(separate['id'],saved['id'])
            self.assertEqual(preview(**separate['params']),preview(**p))
            self.assertEqual(len(list_drafts(reopened)),2)
        self.assertEqual(self.client.get('/api/course-drafts/not-an-id').status_code,409)
        self.assertEqual(self.client.post('/api/course-drafts',json={'params':p,'id':saved['id'],'revision':0}).status_code,409)
