import asyncio
import copy
import csv
import io
from datetime import datetime, timezone
import tempfile
import unittest
from unittest.mock import patch

from analytics_demo import install
from analysis import build_report, report_csv
from web_service import GolfService


class AnalyticsDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)

    def tearDown(self):
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    @patch('driving_range.predict',return_value=dict(status='unavailable',reason='test fixture'))
    def test_history_filters_cleanup_and_repeat_install_preserve_active_round(self,_):
        self.service.create_practice(dict(drill='2D golf',demo=True))
        active=copy.deepcopy(self.service.practice.data)
        original=copy.deepcopy(self.service.equipment)
        result=install(self.service,datetime(2026,10,2,tzinfo=timezone.utc))
        self.assertEqual(self.service.practice.data,active)
        self.assertEqual(self.service.equipment['bags'][:-2],original['bags'])
        self.assertEqual(result['shot_count'],624)
        self.assertEqual((result['excluded'],result['removed'],result['retagged']),(24,6,16))
        self.assertEqual(len(result['session_ids']),20)
        before=self.service.store.list_sessions()
        self.assertTrue(install(self.service)['already_loaded'])
        self.assertEqual(self.service.store.list_sessions(),before)
        sessions=[s for s in before if s['id'] in result['session_ids']]
        self.assertTrue(all(s['demo'] and s['ended']>s['started'] for s in sessions))
        self.assertEqual(len({s['started'][:10] for s in sessions}),8)
        self.assertTrue(all(t['simulated'] for s in sessions for t in s['shots']))
        self.assertTrue(all(s['started']<=t['captured']<s['ended'] for s in sessions for t in s['shots']))
        report=build_report(sessions,dict(mode='demo'))
        self.assertEqual((report['count'],report['excluded'],report['removed']),(594,24,6))
        self.assertLess(report['selected']['descent_ang']['count'],report['count'])
        self.assertFalse(build_report(sessions,dict(mode='real'))['rows'])
        bag=self.service.equipment['bags'][-2]
        driver=bag['clubs'][0]
        filtered=build_report(sessions,dict(mode='demo',bag=bag['id'],club=driver['id']))
        self.assertEqual((len(filtered['trend']),filtered['count']),(8,40))
        csv_rows=list(csv.DictReader(io.StringIO(report_csv(filtered).lstrip('\ufeff'))))
        self.assertEqual(len(csv_rows),40)
        self.assertTrue(all(r['club_label']=='Driver' and r['simulated']=='True' for r in csv_rows))
        wedge=build_report(sessions,dict(mode='demo',bag=bag['id'],swing='Half'))
        self.assertTrue(wedge['rows'])
        self.assertTrue(all(r['swing_label']=='Half' for r in wedge['rows']))
        recent=build_report(sessions,dict(mode='demo',date_from='2026-09-25'))
        self.assertTrue(recent['rows'])
        self.assertTrue(all(r['session_started'][:10]>='2026-09-25' for r in recent['rows']))

    @patch('analytics_demo.DrivingRangeSession.add',side_effect=ValueError('fixture failure'))
    def test_failed_generation_rolls_back_catalog_sessions_and_receipts(self,_):
        catalog=copy.deepcopy(self.service.equipment)
        before=self.service.store.list_sessions()
        count=self.service.store.connection.execute('SELECT COUNT(*) FROM ingest_events').fetchone()[0]
        with self.assertRaisesRegex(ValueError,'fixture failure'):
            install(self.service)
        self.assertEqual(self.service.equipment,catalog)
        self.assertEqual(self.service.store.equipment_catalog(),catalog)
        self.assertEqual(self.service.store.list_sessions(),before)
        self.assertEqual(self.service.store.connection.execute('SELECT COUNT(*) FROM ingest_events').fetchone()[0],count)
