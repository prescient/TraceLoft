import copy
import unittest
import club_model
from analysis import METRICS, build_report, report_csv
from analysis_schema import metric_values
from shot_schema import SOURCE_FIELDS


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        def shot(key, v, **extra):
            return dict(
                key=key,
                bag_id='b',
                bag_name='Bag',
                club_id='c',
                club_label='PW',
                vals={'carry': v, 'offline': -5},
                **extra,
            )

        self.sessions = [
            dict(
                id='a' * 32,
                started='2026-10-01T12:00:00Z',
                drill='Bag mapping',
                practice_type='full_swing',
                demo=False,
                shots=[
                    shot('1', 100),
                    shot('2', 110),
                    shot('3', 900, excluded=True),
                    shot('4', None),
                    shot('5', 500, removed=True),
                ],
            ),
            dict(
                id='b' * 32,
                started='2026-10-02T12:00:00Z',
                drill='Wedge matrix',
                practice_type='full_swing',
                demo=False,
                shots=[shot('6', 60, swing_label='Half')],
            ),
            dict(
                id='c' * 32,
                started='2026-10-02T12:00:00Z',
                drill='Demo',
                demo=True,
                practice_type='full_swing',
                shots=[shot('7', 300)],
            ),
        ]

    def test_default_scope_and_per_metric_missing(self):
        before = copy.deepcopy(self.sessions)
        r = build_report(self.sessions, {})
        self.assertEqual(r['count'], 4)
        self.assertEqual(r['eligible'], 5)
        self.assertEqual(r['removed'], 1)
        self.assertEqual(r['excluded'], 1)
        self.assertEqual(r['selected']['carry']['count'], 3)
        self.assertEqual(r['selected']['absolute_offline']['median'], 5)
        self.assertIsNone(r['selected']['descent_ang']['median'])
        self.assertEqual(len(r['groups']), 2)
        self.assertEqual(self.sessions, before)

    def test_dates_modes_intents_and_session_comparison(self):
        r = build_report(self.sessions, {'date_from': '2026-10-02', 'date_to': '2026-10-02'})
        self.assertEqual(r['selected']['carry']['median'], 60)
        self.assertEqual(build_report(self.sessions, {'mode': 'demo'})['count'], 1)
        self.assertEqual(build_report(self.sessions, {'sessions': 'a' * 32})['count'], 3)
        self.assertEqual(build_report(self.sessions, {'swing': 'Half'})['count'], 1)
        self.assertEqual(build_report(self.sessions, {'inclusion': 'all'})['count'], 5)
        for f in (
            {'date_from': 'not-a-date'},
            {'date_from': '2026-10-02', 'date_to': '2026-10-01'},
            {'metric': 'unknown'},
        ):
            with self.assertRaises(ValueError):
                build_report(self.sessions, f)

    def test_effective_tags_export_and_degenerate_spread(self):
        s = self.sessions[0]['shots'][0]
        s['corrected_equipment'] = {
            'bag_id': 'z',
            'bag_name': '=formula',
            'club_id': 'x',
            'club_label': 'New',
        }
        r = build_report(self.sessions, {'bag': 'z'})
        self.assertEqual(r['count'], 1)
        self.assertIsNone(r['selected']['carry']['iqr'])
        csv = report_csv(r)
        self.assertIn("'=formula", csv)
        self.assertIn('carry (yd)', csv)
        self.assertNotIn('900', csv)
        self.assertIn('face_angle (°)', csv)


class ClubEstimateMetricTests(unittest.TestCase):
    """D64 club estimates in Analyze: both bases, from source readings and the club tag."""

    def row(self, club_label='7 iron', **source):
        values = dict(
            launch_dir=2.0, club_path=4.0, launch_ang=18.0, attack_angle=-3.0, spin_axis=5.0
        )
        values.update(source)
        row = {SOURCE_FIELDS[k][0]: values.get(k) for k in METRICS if k in SOURCE_FIELDS}
        row.update(
            club_label=club_label,
            flight_status=None,
            calculated_smash_factor=None,
            source_rollout_yd=None,
            estimated_distance_ft=None,
            distance_error_ft=None,
        )
        return row

    def test_estimates_match_the_range_page_model(self):
        vals = metric_values(self.row(), 'flight')
        expected = club_model.estimate(
            dict(launch_dir=2.0, club_path=4.0, launch_ang=18.0, attack_angle=-3.0, spin_axis=5.0),
            dict(club_label='7 iron'),
        )
        for key in ('face_angle', 'face_to_path', 'dynamic_loft', 'spin_loft'):
            self.assertAlmostEqual(vals[key], expected[key])
        self.assertAlmostEqual(vals['face_angle'], (2.0 - 0.25 * 4.0) / 0.75)   # iron weights

    def test_both_bases_carry_them_and_missing_inputs_stay_unavailable(self):
        # Analyze opens on the source basis; the estimates have no source reading to replace.
        self.assertEqual(
            metric_values(self.row(), 'source')['face_angle'],
            metric_values(self.row(), 'flight')['face_angle'],
        )
        vals = metric_values(self.row(club_path=None, attack_angle=None), 'source')
        self.assertIsNone(vals['face_angle'])
        self.assertIsNone(vals['dynamic_loft'])
        self.assertEqual(METRICS['face_angle'], ('Estimated face angle', '°'))
