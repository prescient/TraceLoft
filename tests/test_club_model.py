"""Estimated club delivery (club_model.py, D64)."""

import math
import unittest

from club_model import WEIGHTS, club_type, estimate


class ClubModelTests(unittest.TestCase):
    def test_iron_face_loft_and_spin_cross_check(self):
        vals = dict(
            ball_speed=110,
            launch_dir=2.0,
            club_path=4.0,
            launch_ang=18.0,
            attack_angle=-4.0,
            spin_axis=-5.0,
        )
        e = estimate(vals, dict(club_label='7i'))
        k, a = WEIGHTS['iron']
        self.assertEqual(e['club_type'], 'iron')
        self.assertAlmostEqual(
            e['face_angle'], (2.0 - (1 - k) * 4.0) / k
        )  # 1.333: face right of target
        self.assertAlmostEqual(
            e['face_to_path'], e['face_angle'] - 4.0
        )  # closed to an in-to-out path
        self.assertAlmostEqual(e['dynamic_loft'], (18.0 + (1 - a) * 4.0) / a)
        self.assertAlmostEqual(e['spin_loft'], e['dynamic_loft'] + 4.0)
        self.assertAlmostEqual(
            e['face_to_path_from_spin'], e['spin_loft'] * math.tan(math.radians(-5.0))
        )
        self.assertLess(
            e['face_to_path_from_spin'], 0
        )  # draw axis agrees in sign with closed-to-path

    def test_club_types_from_tags_and_untagged_speed(self):
        for label, kind in [
            ('D', 'driver'),
            ('3W', 'wood'),
            ('4H', 'hybrid'),
            ('9i', 'iron'),
            ('PW', 'wedge'),
            ('56°', 'wedge'),
            ('PT', 'putter'),
        ]:
            self.assertEqual(club_type(dict(club_label=label), {}), (kind, 'tag'))
        self.assertEqual(club_type({}, dict(ball_speed=4.3)), ('putter', 'default'))
        self.assertEqual(club_type(None, dict(ball_speed=110)), ('iron', 'default'))

    def test_missing_inputs_stay_unavailable(self):
        putt = estimate(dict(ball_speed=4.3, launch_dir=-1.2, launch_ang=0.0, club_path=0.5))
        self.assertEqual(putt['club_type'], 'putter')
        self.assertIsNotNone(putt['face_angle'])
        self.assertIsNone(putt['dynamic_loft'])  # no attack angle
        self.assertIsNone(putt['face_to_path_from_spin'])  # no spin on putts
        self.assertIsNone(estimate({})['face_angle'])


if __name__ == '__main__':
    unittest.main()
