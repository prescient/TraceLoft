import asyncio
import copy
import tempfile
import unittest
from fastapi.testclient import TestClient
from web_service import GolfService
from web_app import create_app
from analysis import build_report
from analysis_schema import preview_sessions


class SQLAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')
        self.store = self.service.store
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: asyncio.run(self.service.shutdown()))
        self.addCleanup(self.client.close)
        self.bag = self.service.equipment['bags'][0]
        self.club = self.bag['clubs'][6]
        r = self.client.post(
            '/api/practice',
            json=dict(
                drill='Bag mapping',
                range_bag_id=self.bag['id'],
                collection_clubs=[self.club['id']],
                collection_samples=5,
                demo=True,
            ),
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.sid = self.service.practice.data['id']
        for _ in range(5):
            r = self.client.post(f'/api/range/{self.sid}/simulate', json={'count': 1})
            self.assertEqual(r.status_code, 200, r.text)

    def test_sql_report_parity_and_new_source_columns(self):
        legacy = build_report(self.store.list_sessions(), dict(mode='demo'))
        sql = self.store.analysis(dict(mode='demo'))
        for field in (
            'selected',
            'all_recorded',
            'count',
            'eligible',
            'excluded',
            'removed',
            'groups',
            'trend',
            'rows',
        ):
            self.assertEqual(sql[field], legacy[field], field)
        self.assertIn('club_speed', sql['metrics'])
        self.assertIn('total', sql['metrics'])
        self.assertEqual(self.client.get('/api/analysis?mode=demo&format=csv').status_code, 200)

    def test_tag_any_all_without_multiplication_and_golfer_scope(self):
        keys = [s['key'] for s in self.service.practice.data['shots']]
        self.store.edit_tags(self.sid, keys, 'Grip')
        self.store.edit_tags(self.sid, keys[:2], 'Wind', scope='shot')
        self.assertEqual(
            self.store.analysis(dict(mode='demo', tags='Grip, Wind', tag_match='any'))['count'], 5
        )
        self.assertEqual(
            self.store.analysis(dict(mode='demo', tags='Grip, Wind', tag_match='all'))['count'], 2
        )
        uid = self.store.create_user('Other')
        self.store.select_user(uid)
        self.assertEqual(self.store.analysis(dict(mode='demo'))['count'], 0)
        with self.assertRaises(ValueError):
            self.store.select_equipment_profile(self.sid)

    def test_frozen_cohort_cleanup_staleness_and_republication(self):
        before = self.store.collection_analysis(self.sid)
        aid = before['analysis_id']
        self.assertEqual(before['rows'][0]['count'], 5)
        self.store.select_equipment_profile(self.sid)
        game = dict(
            demo=True, equipment_selection=dict(bag_id=self.bag['id'], club_id=self.club['id'])
        )
        self.assertEqual(len(preview_sessions(self.store.connection, game)[0][0]['shots']), 5)
        shot = self.service.practice.data['shots'][0]
        r = self.client.post(
            f'/api/range/{self.sid}/cleanup',
            json=dict(action='exclude', keys=[shot['key']], revision=0, reason='Warmup'),
        )
        self.assertEqual(r.status_code, 200, r.text)
        after = self.store.collection_analysis(self.sid)
        self.assertNotEqual(aid, after['analysis_id'])
        self.assertEqual(after['rows'][0]['count'], 4)
        self.assertEqual(
            self.store.connection.execute(
                'SELECT available_count FROM group_metric_results WHERE result_id=? AND metric=?',
                (before['rows'][0]['result_id'], 'carry'),
            ).fetchone()[0],
            5,
        )
        self.assertTrue(preview_sessions(self.store.connection, game)[1])
        self.assertFalse(preview_sessions(self.store.connection, game)[0])
        self.store.select_equipment_profile(self.sid)
        self.assertFalse(preview_sessions(self.store.connection, game)[1])

    def test_configuration_changes_do_not_fill_old_plan_or_profile(self):
        catalog = self.service.equipment
        clubs = copy.deepcopy(self.bag['clubs'])
        clubs[6]['loft_deg'] = 28
        self.service.edit_bag(catalog['revision'], self.bag['name'], self.bag['id'], clubs)
        r = self.client.post(f'/api/range/{self.sid}/simulate', json={'count': 1})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.store.collection_analysis(self.sid)['rows'][0]['count'], 5)
        config = self.store.connection.execute(
            'SELECT configuration_id FROM club_revisions WHERE club_id=? ORDER BY revision DESC',
            (self.club['id'],),
        ).fetchone()[0]
        self.assertEqual(self.store.analysis(dict(mode='demo', configuration=config))['count'], 1)
        game = dict(
            demo=True, equipment_selection=dict(bag_id=self.bag['id'], club_id=self.club['id'])
        )
        self.assertEqual(len(preview_sessions(self.store.connection, game)[0][0]['shots']), 1)

    def test_workspace_numeric_selection_and_context_lineage(self):
        import json

        params = dict(
            mode='demo',
            workspace='1',
            clubs=self.club['id'],
            ranges=json.dumps({'carry': {'min': 10000}}),
        )
        r = self.client.get('/api/analysis', params=params)
        self.assertEqual(r.status_code, 200, r.text)
        report = r.json()
        self.assertEqual(report['count'], 0)
        self.assertEqual(report['context_count'], 5)
        self.assertEqual(len(report['lineage']), 5)
        exported = self.client.get('/api/analysis', params={**params, 'format': 'csv'})
        self.assertEqual(len(exported.text.strip().splitlines()), 1)
        bad = self.client.get('/api/analysis', params={'ranges': '{"carry":{"min":2,"max":1}}'})
        self.assertEqual(bad.status_code, 409)
        self.assertIn('Minimum must not exceed maximum', bad.json()['detail'])


if __name__ == '__main__':
    unittest.main()
