import copy
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from equipment import edit_catalog, selection
from storage import Store


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'db.sqlite3')
        self.c=self.store.connection;self.bag=self.store.equipment_catalog()['bags'][0]

    def tearDown(self):self.store.close();self.temp.cleanup()

    def session(self,receipt=None,eq=None):
        sid=uuid.uuid4().hex
        eq=eq or selection(self.store.equipment_catalog(),self.bag['id'],self.bag['clubs'][0]['id'])
        d=dict(id=sid,started='2026-10-10T12:00:00Z',ended=None,drill='Driving range',target=150,
               practice_type='full_swing',session_kind='driving_range',demo=False,shots=[dict(key='test:1',
               captured='2026-10-10T12:00:00Z',vals=dict(carry=200,total=215,offline=-8),target=150,success=False,
               excluded=False,receipt_id=receipt,**eq)],equipment_selection=eq,cleanup_history=[],cleanup_revision=0)
        self.store.save_session(d);return d

    def test_relational_authority_and_immutable_legacy_evidence(self):
        d=self.session();sid=d['id'];self.assertEqual(self.store.load_session(sid),d)
        with self.assertRaises(Exception):self.c.execute("UPDATE sessions SET payload_json='{}' WHERE id=?",(sid,))
        self.c.execute("INSERT OR REPLACE INTO metadata VALUES('equipment_catalog.v1','{}')")
        self.assertEqual(self.store.equipment_catalog()['bags'][0],self.bag)
        self.c.execute("UPDATE session_fields SET integer_value=1 WHERE session_id=? AND path='/demo'",(sid,))
        self.assertTrue(self.store.load_session(sid)['demo'])

    def test_cosmetic_rename_spec_revision_removal_and_replacement(self):
        d=self.session();old_config=self.c.execute('SELECT configuration_id FROM v_session_equipment').fetchone()[0]
        catalog=self.store.equipment_catalog();clubs=copy.deepcopy(self.bag['clubs']);clubs[0]['label']='My driver'
        updated,_=edit_catalog(catalog,1,'My bag',self.bag['id'],clubs);self.store.save_equipment_catalog(updated)
        self.assertEqual(self.c.execute('SELECT count(*) FROM club_revisions WHERE club_id=?',(clubs[0]['id'],)).fetchone()[0],1)
        self.assertEqual(self.store.load_session(d['id'])['shots'][0]['club_label'],'Driver')
        clubs[0]['loft_deg']=10.5
        updated,_=edit_catalog(updated,2,'My bag',self.bag['id'],clubs);self.store.save_equipment_catalog(updated)
        self.assertEqual(self.c.execute('SELECT count(*) FROM club_revisions WHERE club_id=?',(clubs[0]['id'],)).fetchone()[0],2)
        self.assertEqual(self.c.execute('SELECT configuration_id FROM v_session_equipment').fetchone()[0],old_config)
        clubs[0].pop('id');updated,_=edit_catalog(updated,3,'My bag',self.bag['id'],clubs);self.store.save_equipment_catalog(updated)
        self.assertNotEqual(updated['bags'][0]['clubs'][0]['id'],self.bag['clubs'][0]['id'])
        self.assertEqual(self.store.load_session(d['id'])['shots'][0]['club_id'],self.bag['clubs'][0]['id'])

    def test_profiles_ownership_and_unknown_inbound_not_assigned_to_last_viewer(self):
        d=self.session();original=self.store.active_user();uid=self.store.create_user('Other golfer','left_handed');self.store.select_user(uid)
        self.assertNotEqual(self.store.equipment_catalog()['bags'][0]['id'],self.bag['id'])
        self.assertEqual(self.store.session_owner(d['id']),original)
        with self.assertRaises(ValueError):self.session()
        event=dict(session_id='no-session',seq=1,result='validated',vals={'ball_speed':100})
        self.store.ingest(event)
        self.assertEqual(self.c.execute('SELECT count(*) FROM shots s LEFT JOIN shot_owners o ON o.shot_id=s.id WHERE o.shot_id IS NULL').fetchone()[0],1)
        with self.assertRaises(ValueError):self.store.edit_tags(d['id'],['test:1'],'Wrong golfer')
        self.assertFalse(self.c.execute('PRAGMA foreign_key_check').fetchall())

    def test_many_tags_scopes_undo_and_bulk_atomicity(self):
        receipt=uuid.uuid4().hex
        self.store.ingest(dict(receipt_id=receipt,session_id='test',seq=1,result='validated',vals=dict(carry=200,total=215,offline=-8)))
        first=self.session(receipt);second=self.session(receipt)
        batch=self.store.edit_tags(first['id'],['test:1'],'Grip',scope='shot')
        self.store.edit_tags(first['id'],['test:1'],'Wind',scope='attempt')
        self.assertEqual(len(self.store.session_tags(first['id'])['test:1']),2)
        self.assertEqual(len(self.store.session_tags(second['id'])['test:1']),1)
        self.store.edit_tags(first['id'],[], '',action='undo',batch_id=batch)
        self.assertEqual(self.store.session_tags(second['id']),{})
        before=self.c.execute('SELECT count(*) FROM shot_tag_events').fetchone()[0]
        with self.assertRaises(ValueError):self.store.edit_tags(first['id'],['test:1','unknown'],'Atomic')
        self.assertEqual(self.c.execute('SELECT count(*) FROM shot_tag_events').fetchone()[0],before)
        self.assertFalse(self.c.execute("SELECT 1 FROM tags WHERE name='Atomic'").fetchone())
        self.assertFalse(self.c.execute('PRAGMA foreign_key_check').fetchall())


if __name__=='__main__':unittest.main()
