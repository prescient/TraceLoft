import tempfile
import unittest
from unittest.mock import patch
from putting import PuttingSession


def record(seq=1, result="validated", speed=4.0, hla=0.0):
    return dict(session_id="capture", seq=seq, result=result,
                vals=dict(ball_speed=speed, launch_dir=hla, launch_ang=1.0))


class PuttingTests(unittest.TestCase):
    def test_random_targets_are_saved_per_shot_and_do_not_repeat(self):
        with tempfile.TemporaryDirectory() as folder, patch("putting.random.choice", side_effect=lambda choices: choices[0]):
            session = PuttingSession(folder, "Pace consistency", 4, .3, 1, 3, True, 3, 3.1)
            targets = []
            for seq in range(1, 4):
                target = session.data["target"]
                targets.append(target)
                self.assertTrue(session.add(record(seq=seq, speed=target)))
            self.assertEqual(targets, [3, 3.1, 3])
            reopened = PuttingSession.load(session.path)
            self.assertEqual([s["target"] for s in reopened.data["shots"]], targets)
            self.assertEqual(reopened.summary()["successes"], 3)
            self.assertEqual(reopened.summary()["pace_error"]["sd"], 0)

    def test_random_range_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            for minimum, maximum in ((0, 6), (3, 3), (3.01, 3.11), (3, float("inf")), (6, 3)):
                with self.subTest(minimum=minimum, maximum=maximum), self.assertRaises(ValueError):
                    PuttingSession(folder, "Pace consistency", 4, .3, 1, 3, True, minimum, maximum)
    def test_scoring_persistence_duplicates_and_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            session = PuttingSession(folder, "Pace + start line", 4, .3, 1, 2)
            self.assertFalse(session.add(record(result="failed")))
            self.assertTrue(session.add(record(speed=4.3, hla=-1)))
            self.assertFalse(session.add(record()))
            self.assertTrue(session.add(record(seq=2, speed=5)))
            self.assertFalse(session.add(record(seq=3)))
            reopened = PuttingSession.load(session.path)
            self.assertTrue(reopened.data["ended"])
            self.assertEqual(reopened.summary()["successes"], 1)
            self.assertEqual(reopened.summary()["count"], 2)
            reopened.toggle_excluded("capture:2")
            self.assertEqual(PuttingSession.load(session.path).summary()["count"], 1)

    def test_drills_score_only_their_selected_measurement(self):
        with tempfile.TemporaryDirectory() as folder:
            pace = PuttingSession(folder, "Pace consistency", 4, .3, 1, 2)
            pace.add(record(hla=5))
            line = PuttingSession(folder, "Start line", 4, .3, 1, 2)
            line.add(record(speed=10))
            self.assertEqual(pace.summary()["successes"], 1)
            self.assertEqual(line.summary()["successes"], 1)

    def test_bad_measurements_and_settings_do_not_enter_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            session = PuttingSession(folder, "Start line", 4, .3, 1, 10)
            self.assertFalse(session.add(record(speed=float("nan"))))
            self.assertFalse(session.add(record(hla=None)))
            for target, tolerance, reps in ((float("nan"), .3, 10), (4, -1, 10), (4, .3, 0)):
                with self.assertRaises(ValueError):
                    PuttingSession(folder, "Start line", target, tolerance, 1, reps)
