import copy
import unittest
from analysis import build_report, report_csv


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        def shot(key,v,**extra):return dict(key=key,bag_id='b',bag_name='Bag',club_id='c',club_label='PW',vals={'carry':v,'offline':-5},**extra)
        self.sessions=[dict(id='a'*32,started='2026-10-01T12:00:00Z',drill='Bag mapping',practice_type='full_swing',demo=False,
            shots=[shot('1',100),shot('2',110),shot('3',900,excluded=True),shot('4',None),shot('5',500,removed=True)]),
            dict(id='b'*32,started='2026-10-02T12:00:00Z',drill='Wedge matrix',practice_type='full_swing',demo=False,
            shots=[shot('6',60,swing_label='Half')]),
            dict(id='c'*32,started='2026-10-02T12:00:00Z',drill='Demo',demo=True,practice_type='full_swing',shots=[shot('7',300)])]

    def test_default_scope_and_per_metric_missing(self):
        before=copy.deepcopy(self.sessions);r=build_report(self.sessions,{})
        self.assertEqual(r['count'],4);self.assertEqual(r['eligible'],5);self.assertEqual(r['removed'],1)
        self.assertEqual(r['excluded'],1);self.assertEqual(r['selected']['carry']['count'],3)
        self.assertEqual(r['selected']['absolute_offline']['median'],5)
        self.assertIsNone(r['selected']['descent_ang']['median'])
        self.assertEqual(len(r['groups']),2);self.assertEqual(self.sessions,before)

    def test_dates_modes_intents_and_session_comparison(self):
        r=build_report(self.sessions,{'date_from':'2026-10-02','date_to':'2026-10-02'})
        self.assertEqual(r['selected']['carry']['median'],60)
        self.assertEqual(build_report(self.sessions,{'mode':'demo'})['count'],1)
        self.assertEqual(build_report(self.sessions,{'sessions':'a'*32})['count'],3)
        self.assertEqual(build_report(self.sessions,{'swing':'Half'})['count'],1)
        self.assertEqual(build_report(self.sessions,{'inclusion':'all'})['count'],5)
        for f in ({'date_from':'not-a-date'},{'date_from':'2026-10-02','date_to':'2026-10-01'},{'metric':'unknown'}):
            with self.assertRaises(ValueError):build_report(self.sessions,f)

    def test_effective_tags_export_and_degenerate_spread(self):
        s=self.sessions[0]['shots'][0];s['corrected_equipment']={'bag_id':'z','bag_name':'=formula','club_id':'x','club_label':'New'}
        r=build_report(self.sessions,{'bag':'z'})
        self.assertEqual(r['count'],1);self.assertIsNone(r['selected']['carry']['iqr'])
        csv=report_csv(r);self.assertIn("'=formula",csv);self.assertIn('carry (yd)',csv)
        self.assertNotIn('900',csv)
