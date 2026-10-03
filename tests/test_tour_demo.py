import asyncio
import copy
import tempfile
import unittest
from unittest.mock import patch
from web_service import GolfService
from tour_demo import install, SOURCE, SAMPLES
from analysis import build_report


class TourDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name,capture_detector=lambda:False)

    def tearDown(self):
        asyncio.run(self.service.shutdown());self.temp.cleanup()

    def test_atomic_idempotent_separate_profiles_and_active_session(self):
        self.service.create_practice(dict(drill='2D golf',demo=True))
        active=copy.deepcopy(self.service.practice.data)
        original=copy.deepcopy(self.service.equipment)
        result=install(self.service)
        self.assertEqual(self.service.practice.data,active)
        self.assertEqual(self.service.equipment['bags'][0],original['bags'][0])
        self.assertEqual(install(self.service)['session_ids'],result['session_ids'])
        sessions=[self.service.load_session(s).data for s in result['session_ids']]
        self.assertEqual(sum(len(s['shots']) for s in sessions),324)
        self.assertTrue(all(s['demo'] and s['ended'] for s in sessions))
        self.assertTrue(all(t['simulated'] for s in sessions for t in s['shots']))
        self.assertEqual(len(sessions[1]['shots']),12*SAMPLES)
        report=build_report(sessions,dict(mode='demo',bag=result['bag_id'],metric='carry'))
        pw=[g for g in report['groups'] if g['club_label']=='PW' and g['swing_label']]
        self.assertEqual(len(pw),3)
        distances={g['swing_label']:g['metrics']['carry']['median'] for g in pw}
        self.assertLess(distances['Half'],distances['Three-quarter'])
        self.assertLess(distances['Three-quarter'],distances['Full'])
        self.assertFalse(build_report(sessions,dict(mode='real',metric='carry'))['groups'])
        self.assertEqual(SOURCE['clubs'][0]['carry_yd'],282)
        eq=self.service.equipment['bags'][-1]
        self.service.select_equipment(active['id'],eq['id'],eq['clubs'][0]['id'])
        self.assertTrue(self.service.game_recommendations(active['id']))
        before_preview=copy.deepcopy(self.service.practice.data)
        preview=self.service.game_preview(active['id'])
        self.assertEqual(preview['profiles'][0]['included'],SAMPLES)
        self.assertEqual(len(preview['profiles'][0]['views']['reported_total']['points']),SAMPLES)
        self.assertEqual(self.service.practice.data,before_preview)

    def test_failed_install_rolls_back_catalog_and_sessions(self):
        original=copy.deepcopy(self.service.equipment)
        before=self.service.store.list_sessions()
        with patch('tour_demo.CollectionSession.add',side_effect=ValueError('test failure')):
            with self.assertRaises(ValueError):install(self.service)
        self.assertEqual(self.service.equipment,original)
        self.assertEqual(self.service.store.equipment_catalog(),original)
        self.assertEqual(self.service.store.list_sessions(),before)
