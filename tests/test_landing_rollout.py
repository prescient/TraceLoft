import copy
import tempfile
import unittest
from golf_sim import COURSE, GolfSimSession, landing_rollout, simulated_event


class LandingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.course = copy.deepcopy(COURSE)
        self.course.update(pin=[0, 400], bounds=[-80, 80, -15, 450], water=[], sand=[])

    def tearDown(self):
        self.temp.cleanup()

    def session(self, **kwargs):
        return GolfSimSession(self.temp.name, course=self.course, **kwargs)

    def hit(self, p, total=100, carry=80, offline=0):
        event = simulated_event(p, total, offline)
        event['vals']['carry'] = carry
        raw = copy.deepcopy(event['vals'])
        self.assertTrue(p.add(event))
        self.assertEqual(p.data['shots'][-1]['vals'], raw)
        return p.data['shots'][-1]['game_outcome']

    def test_sand_stops_at_carry_even_when_original_total_would_clear_bunker(self):
        self.course['sand'] = [dict(center=[0, 80], radius=5)]
        p = self.session()
        o = self.hit(p)
        self.assertEqual(p.data['game']['position'], [0, 80])
        self.assertEqual(p.data['game']['lie'], 'sand')
        self.assertEqual(o['landing_rollout']['base_endpoint'], [0, 100])
        self.assertEqual(o['landing_rollout']['adjusted_rollout_yd'], 0)
        self.assertEqual(o['adjusted_forward_yd'], 80)
        self.assertEqual(o['after']['strokes'], 1)
        self.assertIn('Sand landing stopped rollout', o['message'])
        p.correct_shot('misread', p.data['shots'][-1]['key'], p.data['game']['turn'])
        self.assertEqual(p.data['game']['position'], [0, 0])
        self.assertEqual(p.data['game']['strokes'], 0)
        self.assertEqual(p.data['shots'][-1]['game_outcome'], o)

    def test_rough_removes_75_percent_of_roll_not_carry_even_if_ball_exits_rough(self):
        self.course['fairway'] = [[-20, 84], [20, 84], [20, 450], [-20, 450]]
        p = self.session()
        o = self.hit(p)
        self.assertEqual(o['landing_rollout']['landing_lie'], 'rough')
        self.assertEqual(o['landing_rollout']['landing_point'], [0, 80])
        self.assertEqual(p.data['game']['position'], [0, 85])
        self.assertEqual(p.data['game']['lie'], 'fairway')
        self.assertEqual(o['landing_rollout']['adjusted_rollout_yd'], 5)

    def test_ob_landing_stops_at_carry_and_retains_final_ob_penalty(self):
        p = self.session()
        o = self.hit(p, offline=112.5)
        self.assertEqual(o['landing_rollout']['landing_lie'], 'out of bounds')
        self.assertEqual(o['endpoint'], [90, 80])
        self.assertEqual(o['penalty_strokes'], 1)
        self.assertEqual(p.data['game']['strokes'], 2)
        self.assertEqual(p.data['game']['position'], [0, 0])

    def test_configurable_zero_and_full_rough_reduction(self):
        for reduction, expected in [(0, 100), (50, 90), (100, 80)]:
            with self.subTest(reduction=reduction):
                self.course['fairway'] = []
                p = self.session(game_rollout_rough=reduction)
                self.hit(p)
                self.assertEqual(p.data['game']['position'], [0, expected])
        for value in [-1, 101, float('nan')]:
            with self.assertRaises(ValueError):
                self.session(game_rollout_ob=value)

    def test_missing_invalid_carry_keeps_total_and_reports_skipped_rules(self):
        self.course['sand'] = [dict(center=[0, 80], radius=5)]
        for carry in [None, -1, 101, float('nan')]:
            end, r = landing_rollout([0, 0], [0, 100], carry, 100, self.course, {})
            self.assertEqual(end, [0, 100])
            self.assertFalse(r['applied'])
        p = self.session()
        o = self.hit(p, carry=None)
        self.assertEqual(o['endpoint'], [0, 100])
        self.assertIn('Landing rules unavailable', o['message'])

    def test_starting_sand_reduction_is_applied_before_landing_rule(self):
        self.course['sand'] = [dict(center=[0, 64], radius=5)]
        p = self.session()
        p.data['game']['lie'] = 'sand'
        o = self.hit(p)
        self.assertEqual(o['distance_factor'], 0.8)
        self.assertEqual(o['landing_rollout']['landing_point'], [0, 64])
        self.assertEqual(o['endpoint'], [0, 64])

    def test_no_roll_and_sand_crossed_in_flight_do_not_shorten_fairway_landing(self):
        self.course['sand'] = [dict(center=[0, 50], radius=5)]
        p = self.session()
        o = self.hit(p, carry=100)
        self.assertEqual(o['endpoint'], [0, 100])
        self.assertEqual(o['landing_rollout']['reduction_percent'], 0)
        self.assertEqual(o['landing_rollout']['original_rollout_yd'], 0)

    def test_legacy_round_new_shots_use_defaults_and_prior_outcome_stays_frozen(self):
        self.course['fairway'] = []
        p = self.session()
        p.data['game_settings'].pop('rough_rollout_percent')
        p.data['game_settings'].pop('ob_rollout_percent')
        o = self.hit(p)
        before = copy.deepcopy(o)
        self.assertEqual(o['endpoint'], [0, 85])
        self.assertEqual(o['settings']['rough_rollout_percent'], 75)
        self.hit(p, total=50, carry=40)
        self.assertEqual(p.data['shots'][0]['game_outcome'], before)
