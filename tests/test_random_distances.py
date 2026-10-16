import asyncio
import copy
import tempfile
import unittest

from fastapi.testclient import TestClient

from random_distances import RandomDistanceSession, candidates, target_grid
from web_app import create_app
from web_service import GolfService

# A full swing the model can fly; the reported carry/total are only a fallback (D63).
VALUES = dict(ball_speed=120, launch_ang=18, launch_dir=2, total_spin=5000, spin_axis=8)
# No spin and no reported carry: the model cannot run, so the shot is unscored.
NO_CARRY = dict(ball_speed=120, launch_ang=18, launch_dir=2)


class TargetGridTests(unittest.TestCase):
    def test_grid_steps_from_the_shortest_target(self):
        self.assertEqual(target_grid(60, 80, 5), [60, 65, 70, 75, 80])
        self.assertEqual(target_grid(60, 82, 5), [60, 65, 70, 75, 80])

    def test_next_target_respects_the_minimum_change_and_never_repeats(self):
        grid = target_grid(60, 100, 10)
        self.assertEqual(candidates(grid, 80, 15), [60, 100])
        self.assertEqual(candidates(grid, 80, 0), [60, 70, 90, 100])
        self.assertEqual(candidates(grid, None, 15), grid)


class RandomDistanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')
        self.bag = self.service.equipment['bags'][0]
        self.seq = 0

    def tearDown(self):
        self.client.close()
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def launch(self, **extra):
        body = dict(drill='Random distances', range_bag_id=self.bag['id'])
        body.update(extra)
        response = self.client.post('/api/practice', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.sid = response.json()['practice']['id']
        return response.json()['practice']

    def shot(self, vals=VALUES, **extra):
        self.seq += 1
        self.service.ingest(
            dict(
                kind='record',
                session_id='random-test',
                seq=self.seq,
                receipt_id=f'random-test-{self.seq}',
                result='validated',
                practice_session_id=self.sid,
                vals=copy.deepcopy(vals),
                **extra,
            )
        )
        return self.service.practice.data

    def test_each_scored_shot_draws_a_new_target_until_the_count_is_reached(self):
        data = self.launch(
            random_min=60, random_max=180, random_step=5, random_gap=15, random_count=4
        )
        self.assertEqual(
            (data['drill'], data['session_kind'], data['target_plan']),
            ('Random distances', 'driving_range', 'random'),
        )
        grid = target_grid(60, 180, 5)
        self.assertIn(data['range_target'], grid)
        targets = [data['range_target']]
        for number in range(1, 5):
            data = self.shot()
            shot = data['shots'][-1]
            self.assertTrue(shot['scored'])
            self.assertEqual(shot['target_distance_yd'], targets[-1])
            self.assertEqual(shot['target_number'], number)
            self.assertEqual(shot['distance_basis'], 'opengolfcoach')
            self.assertEqual(shot['success'], abs(shot['distance_error_yd']) <= 10)
            if number < 4:
                self.assertIsNone(data['ended'])
                self.assertIn(data['range_target'], grid)
                self.assertGreaterEqual(abs(data['range_target'] - targets[-1]), 15)
                self.assertEqual(data['target'], data['range_target'])
                # The source is told the new target (published input context).
                self.assertEqual(
                    self.service.input_context['range_context']['range_target'],
                    data['range_target'],
                )
                targets.append(data['range_target'])
        self.assertIsNotNone(data['ended'])
        self.assertEqual(data['completed_shots'], 4)
        summary = self.client.get(f'/api/sessions/{self.sid}').json()['summary']
        self.assertEqual(summary['targets']['completed'], 4)
        self.assertEqual(summary['targets']['scored'], 4)

    def test_a_shot_without_carry_is_recorded_and_keeps_the_target(self):
        data = self.launch(random_count=2)
        target = data['range_target']
        data = self.shot(NO_CARRY)
        shot = data['shots'][-1]
        self.assertFalse(shot['scored'])
        self.assertIsNone(shot['distance_yd'])
        self.assertIn('target unchanged', shot['unscored_reason'])
        self.assertEqual((data['range_target'], data['completed_shots']), (target, 0))
        data = self.shot()
        self.assertEqual(data['shots'][-1]['target_distance_yd'], target)
        self.assertEqual(data['completed_shots'], 1)

    def test_the_session_target_wins_over_a_stale_published_context(self):
        data = self.launch()
        stale = dict(range_target=999, range_width=1, range_depth=1)
        data = self.shot(range_context=stale)
        self.assertEqual(data['shots'][-1]['target_width_yd'], 30)
        self.assertNotEqual(data['shots'][-1]['target_distance_yd'], 999)

    def test_change_target_is_refused(self):
        data = self.launch()
        response = self.client.post(
            f'/api/range/{self.sid}/target', json=dict(target=100, width=30, depth=20)
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn('Random distances choose each target', response.text)
        self.assertEqual(self.service.practice.data['range_target'], data['range_target'])

    def test_invalid_setups_are_rejected_with_guidance(self):
        for body, message in (
            (dict(random_min=150, random_max=100), 'longest above the shortest'),
            (dict(random_min=100, random_max=110, random_gap=15), 'minimum change'),
            (dict(random_min=100, random_max=104, random_step=5), 'minimum change'),
        ):
            with self.subTest(body=body):
                response = self.client.post(
                    '/api/practice', json=dict(drill='Random distances', **body)
                )
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn(message, response.text)
                self.assertIsNone(self.service.practice)
        response = self.client.post(
            '/api/practice', json=dict(drill='Random distances', random_count=0)
        )
        self.assertEqual(response.status_code, 422)

    def test_exclusion_changes_statistics_not_progression(self):
        self.launch(random_count=5)
        self.shot()
        data = self.shot()
        key = data['shots'][0]['key']
        response = self.client.post(f'/api/practice/{self.sid}/exclude', json=dict(key=key))
        self.assertEqual(response.status_code, 200, response.text)
        targets = response.json()['summary']['targets']
        self.assertEqual((targets['completed'], targets['scored']), (2, 1))
        self.assertEqual(self.service.practice.data['completed_shots'], 2)
        # Statistics use only the included shot.
        included = self.service.practice.data['shots'][1]['distance_error_yd']
        self.assertAlmostEqual(targets['mean_error'], included)
        self.assertAlmostEqual(targets['mean_absolute_error'], abs(included))

    def test_a_reopened_session_keeps_drawing_targets(self):
        self.launch(random_count=3)
        self.shot()
        reopened = self.service.load_session(self.sid)
        self.assertIs(type(reopened), RandomDistanceSession)
        self.assertEqual(reopened.data, self.service.practice.data)
        target = reopened.data['range_target']
        # As after a restart: an idle service resumes the saved session.
        self.service.practice = None
        self.service.resume_practice(self.sid)
        self.assertIs(type(self.service.practice), RandomDistanceSession)
        data = self.shot()
        self.assertEqual(data['shots'][-1]['target_distance_yd'], target)
        self.assertEqual(data['completed_shots'], 2)

    def test_demo_shots_aim_at_the_drawn_target(self):
        self.launch(demo=True, random_count=12)
        response = self.client.post(f'/api/range/{self.sid}/simulate', json=dict(count=10))
        self.assertEqual(response.status_code, 200, response.text)
        shots = self.service.practice.data['shots']
        self.assertEqual(len(shots), 10)
        self.assertTrue(all(s['simulated'] and s['scored'] for s in shots))
        # Every ninth demo shot is a deliberate mishit; the rest land near their targets.
        close = [s for s in shots if abs(s['distance_error_yd']) <= 25]
        self.assertGreaterEqual(len(close), 8)

    def test_shots_reach_analyze_and_the_database_export(self):
        import io
        import zipfile

        self.launch(demo=True, random_count=5, range_club_id=self.bag['clubs'][6]['id'])
        self.client.post(f'/api/range/{self.sid}/simulate', json=dict(count=1))
        self.client.post(f'/api/range/{self.sid}/simulate', json=dict(count=1))
        self.client.post(f'/api/range/{self.sid}/simulate', json=dict(count=1))
        report = self.client.get('/api/analysis', params=dict(mode='demo')).json()
        self.assertEqual(report['count'], 3)
        archive = zipfile.ZipFile(io.BytesIO(self.client.get('/api/exports/csv').content))
        exported = '\n'.join(archive.read(name).decode('utf-8') for name in archive.namelist())
        self.assertIn(self.sid, exported)
        self.assertIn('Random distances', exported)


if __name__ == '__main__':
    unittest.main()
