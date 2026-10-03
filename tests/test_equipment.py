"""Bag edits and shot tagging must never relabel measured history."""
import asyncio
import copy
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from equipment import selection
from storage import Store
from web_app import create_app
from web_service import GolfService
from tests.test_distance_ladder import event


class EquipmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name, capture_detector=lambda:False)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')
        self.bag = self.service.equipment['bags'][0]
        self.pw = next(c for c in self.bag['clubs'] if c['label'] == 'PW')
        self.sw = next(c for c in self.bag['clubs'] if c['label'] == 'SW')

    def tearDown(self):
        self.client.close()
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def launch(self):
        response = self.client.post('/api/practice', json=dict(drill='Distance ladder',
                range_bag_id=self.bag['id'], range_club_id=self.pw['id']))
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['practice']['id']

    def choose(self, sid, club=None, bag=None):
        return self.client.post(f'/api/practice/{sid}/equipment',json=dict(
            bag_id=(bag or self.bag)['id'],club_id=(club or self.sw)['id']))

    def shot(self,sid,seq,**extra):
        self.service.ingest(event(seq, practice_session_id=sid, receipt_id=f'club-shot-{seq}',**extra))

    def test_switches_freeze_per_shot_tags_and_export_without_altering_targets(self):
        sid=self.launch()
        self.shot(sid,1)
        self.assertEqual(self.choose(sid).status_code,200)
        self.shot(sid,2)
        shots=self.service.practice.data['shots']
        self.assertEqual([s['club_label'] for s in shots],['PW','SW'])
        self.assertEqual([s['target_distance_yd'] for s in shots],[30,40])
        catalog=self.service.equipment
        clubs=copy.deepcopy(self.bag['clubs'])
        next(c for c in clubs if c['id']==self.sw['id'])['label']='54° wedge'
        response=self.client.put(f"/api/equipment/bags/{self.bag['id']}",json=dict(revision=catalog['revision'],name='Gamer bag',clubs=clubs))
        self.assertEqual(response.status_code,200,response.text)
        self.shot(sid,3)
        shots=self.service.load_session(sid).data['shots']
        self.assertEqual([s['club_label'] for s in shots],['PW','SW','54° wedge'])
        self.assertEqual([s['bag_name'] for s in shots],['My bag','My bag','Gamer bag'])
        self.assertEqual(shots[1]['club_id'],shots[2]['club_id'])
        with zipfile.ZipFile(io.BytesIO(self.service.store.export())) as z:
            rows=list(csv.DictReader(io.StringIO(z.read('session_attempts.csv').decode('utf-8-sig'))))
            self.assertEqual([r['club_label'] for r in rows],['PW','SW','54° wedge'])
            self.assertEqual(rows[2]['bag_id'],self.bag['id'])
            self.assertEqual(rows[2]['selection_mode'],'manual')
        self.assertFalse(self.service.store.connection.execute('PRAGMA foreign_key_check').fetchall())

    def test_multiple_bags_stale_edits_and_invalid_membership(self):
        sid=self.launch()
        response=self.client.post('/api/equipment/bags',json=dict(revision=1,name='Practice bag'))
        self.assertEqual(response.status_code,200,response.text)
        second=response.json()['equipment']['bags'][1]
        self.assertEqual(len(second['clubs']),15)
        self.assertNotEqual(second['clubs'][0]['id'],self.bag['clubs'][0]['id'])
        self.assertEqual(self.choose(sid,self.pw,second).status_code,409)
        self.assertEqual(self.choose(sid,second['clubs'][0],second).status_code,200)
        self.shot(sid,1)
        self.assertEqual(self.service.practice.data['shots'][0]['bag_name'],'Practice bag')
        self.assertEqual(self.client.post('/api/equipment/bags',json=dict(revision=1,name='Third bag')).status_code,409)
        self.assertEqual(self.client.post('/api/equipment/bags',json=dict(revision=2,name='my BAG')).status_code,409)
        self.assertEqual(self.client.post(f'/api/practice/{sid}/equipment',json=dict(bag_id=second['id'],club_id='')).status_code,200)
        self.shot(sid,2)
        self.assertEqual(self.service.practice.data['shots'][-1]['club_label'],'')

    def test_receipt_snapshot_wins_over_later_selection_and_retries(self):
        sid=self.launch()
        original=copy.deepcopy(self.service.practice.data['equipment_selection'])
        self.choose(sid)
        self.shot(sid,1,equipment_selection=original)
        self.assertEqual(self.service.practice.data['shots'][0]['club_label'],'PW')
        with patch.object(self.service.store,'save_session',side_effect=OSError('disk full')):
            self.shot(sid,2)
            self.assertEqual(self.choose(sid,self.pw).status_code,409)
        self.service.flush_practice()
        self.assertEqual(self.service.practice.data['shots'][-1]['club_label'],'SW')
        self.assertEqual(self.service.store.count('session_attempts'),2)

    def test_failed_bag_or_selection_save_rolls_back_catalog_context_and_session(self):
        sid=self.launch()
        original=copy.deepcopy(self.service.practice.data)
        context=self.service.input.context()
        with patch.object(self.service.practice,'save',side_effect=OSError('disk full')):
            self.assertEqual(self.choose(sid).status_code,500)
            r=self.client.put(f"/api/equipment/bags/{self.bag['id']}",json=dict(revision=1,name='New name',clubs=self.bag['clubs']))
            self.assertEqual(r.status_code,500)
        self.assertEqual(self.service.practice.data,original)
        self.assertEqual(self.service.equipment['revision'],1)
        self.assertEqual(self.service.store.equipment_catalog()['revision'],1)
        self.assertEqual(self.service.input.context(),context)

    def test_remove_selected_club_clears_future_tag_without_relabeling_history(self):
        sid=self.launch();self.shot(sid,1)
        response=self.client.put(f"/api/equipment/bags/{self.bag['id']}",json=dict(revision=1,name='My bag',clubs=[c for c in self.bag['clubs'] if c['id']!=self.pw['id']]))
        self.assertEqual(response.status_code,200,response.text)
        self.shot(sid,2)
        self.assertEqual([s['club_label'] for s in self.service.practice.data['shots']],['PW',''])
        self.client.post(f'/api/practice/{sid}/finish',json={})
        self.assertEqual(self.choose(sid).status_code,409)
        self.assertEqual(self.choose('f'*32).status_code,409)

    def test_catalog_survives_snapshot_restore_with_ids_and_old_session_data(self):
        sid=self.launch();self.shot(sid,1)
        old=copy.deepcopy(self.service.practice.data)
        self.client.post('/api/equipment/bags',json=dict(revision=1,name='Travel bag'))
        from database_tools import restore_snapshot
        snapshot=self.service.store.backup()
        target=Path(self.temp.name)/'restored.sqlite3'
        restore_snapshot(snapshot,target)
        restored=Store(target)
        try:
            self.assertEqual(restored.equipment_catalog(),self.service.equipment)
            self.assertEqual(restored.load_session(sid),old)
        finally:restored.close()


    def test_invalid_catalog_edits_do_not_change_existing_data(self):
        for clubs in ([],self.bag['clubs']+[self.bag['clubs'][0]], [dict(id='f'*32,label='Fake')]):
            r=self.client.put(f"/api/equipment/bags/{self.bag['id']}",json=dict(revision=1,name='My bag',clubs=clubs))
            self.assertEqual(r.status_code,409)
        self.assertEqual(self.service.store.equipment_catalog()['revision'],1)


if __name__=='__main__':unittest.main()
