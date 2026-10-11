import copy
import csv
import io
import json
import unittest
from analysis import build_report, report_csv


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.sessions = [
            dict(
                id='s',
                started='2026-10-01T12:00:00Z',
                drill='Range',
                practice_type='full_swing',
                shots=[
                    dict(
                        key=str(i),
                        bag_id='b',
                        club_id=club,
                        vals=dict(carry=carry, offline=off),
                        excluded=excluded,
                    )
                    for i, (club, carry, off, excluded) in enumerate(
                        [
                            ('a', 100, -5, False),
                            ('b', 120, 10, False),
                            ('c', 130, 15, False),
                            ('a', 150, None, False),
                            ('b', 900, 20, True),
                        ]
                    )
                ],
            )
        ]

    def test_multi_club_and_ranges_apply_to_stats_rows_and_csv(self):
        before = copy.deepcopy(self.sessions)
        r = build_report(
            self.sessions,
            dict(
                clubs='a,b,a',
                workspace='1',
                ranges=json.dumps({'absolute_offline': {'min': 5, 'max': 10}}),
            ),
        )
        self.assertEqual(r['filters']['clubs'], 'a,b')
        self.assertEqual(r['count'], 2)
        self.assertEqual(r['context_count'], 3)
        self.assertEqual(r['selected']['carry']['median'], 110)
        self.assertEqual(len(r['groups']), 2)
        self.assertEqual(r['trend'][0]['count'], 2)
        exported = list(csv.DictReader(io.StringIO(report_csv(r).lstrip('\ufeff'))))
        self.assertEqual({x['key'] for x in exported}, {'0', '1'})
        self.assertEqual(self.sessions, before)

    def test_missing_bounds_and_exclusion_policy(self):
        f = dict(clubs='a,b', ranges='{"carry":{"min":100}}')
        self.assertEqual(build_report(self.sessions, f)['count'], 3)
        self.assertEqual(build_report(self.sessions, {**f, 'inclusion': 'all'})['count'], 4)
        r = build_report(self.sessions, dict(ranges='{"descent_ang":{"min":0}}', workspace='1'))
        self.assertEqual(r['count'], 0)
        self.assertEqual(r['context_count'], 4)
        self.assertEqual(build_report(self.sessions, dict(club='c'))['count'], 1)
        self.assertEqual(build_report(self.sessions, dict(mode='demo'))['count'], 0)

    def test_reject_invalid_predicates(self):
        for ranges in (
            'bad',
            '[]',
            '{"unknown":{"min":1}}',
            '{"carry":{}}',
            '{"carry":{"min":true}}',
            '{"carry":{"min":NaN}}',
            '{"carry":{"min":2,"max":1}}',
            '{"carry":{"wat":2}}',
        ):
            with self.subTest(ranges=ranges), self.assertRaises(ValueError):
                build_report(self.sessions, dict(ranges=ranges))
