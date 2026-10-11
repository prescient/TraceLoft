"""Full-course API journeys, immutable round state and original geometry."""

import asyncio
import copy
import math
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from bundled_courses import load_bundled
from course_geometry import classify
from course_workbench import validate_edits
from golf_sim import simulated_event
from web_service import GolfService
from web_app import create_app

YARDS = [405, 533, 180, 451, 563, 378, 205, 470, 412, 376, 563, 138, 389, 360, 464, 545, 223, 487]


class CourseTests(unittest.TestCase):
    def test_geometry_and_blue_scorecard(self):
        package = load_bundled('sheboygan-straits-blue-v1')
        self.assertEqual([c['yards'] for c in package['holes']], YARDS)
        self.assertEqual(package['yards'], 7142)
        self.assertEqual(sum(c['par'] for c in package['holes']), 72)
        self.assertEqual(len({c['id'] for c in package['holes']}), 18)
        for c in package['holes']:
            with self.subTest(hole=c['hole_number']):
                validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
                self.assertEqual(classify(c['tee'], c), 'tee')
                self.assertEqual(classify(c['pin'], c), 'green')
                image = Path(__file__).parents[1] / 'web/art' / Path(c['image']['href']).name
                raw = image.read_bytes()
                self.assertEqual(raw[:8], b'\x89PNG\r\n\x1a\n')
                width, height = struct.unpack('>II', raw[16:24])
                self.assertAlmostEqual(
                    width / height, c['image']['width'] / c['image']['height'], places=3
                )
                self.assertGreaterEqual(c['bunker_count'], 10)
                import hashlib

                self.assertEqual(hashlib.sha256(raw).hexdigest(), c['provenance']['art_sha256'])
                for kind, points in c['hazard_test_points'].items():
                    for point in points:
                        self.assertEqual(classify(point, c), kind)
                line = c['playing_line']
                self.assertAlmostEqual(
                    sum(math.dist(a, b) for a, b in zip(line, line[1:])), c['yards'], places=3
                )
                for point in line:
                    self.assertIn(classify(point, c), ('tee', 'fairway', 'rough', 'green'))


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')
        r = self.client.post(
            '/api/practice',
            json=dict(
                drill='2D golf', demo=True, game_course_id='sheboygan-straits-blue-v1', game_gimme=0
            ),
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.p = self.service.practice
        self.url = f"/api/game/{self.p.data['id']}"

    def tearDown(self):
        self.client.close()
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def hit(self, target):
        p = self.p
        g = p.data['game']
        r = self.client.post(self.url + '/aim', json=dict(x=target[0], y=target[1], turn=g['turn']))
        self.assertEqual(r.status_code, 200, r.text)
        factor = 1 - p.data['game_settings'].get(g['lie'] + '_percent', 0) / 100
        # Endpoint/lifecycle fixture: explicit no-roll carry; landing behavior is tested separately.
        travel = math.dist(g['position'], target) / factor
        params = dict(distance_yd=travel, offline_yd=0, turn=g['turn'])
        if g['lie'] != 'green':
            params['carry_yd'] = travel
        r = self.client.post(self.url + '/simulate', json=params)
        self.assertEqual(r.status_code, 200, r.text)

    def next(self, turn=None):
        return self.client.post(
            self.url + '/next', json={'turn': self.p.data['game']['turn'] if turn is None else turn}
        )

    def test_bunker_recovery_water_and_completed_hole_corrections(self):
        p = self.p
        c = p.data['course']
        self.hit(c['hazard_test_points']['sand'][0])
        self.assertEqual(p.data['game']['lie'], 'sand')
        self.hit(c['playing_line'][1])
        self.assertEqual(p.data['game']['lie'], 'fairway')
        before = copy.deepcopy(p.data['game'])
        self.hit(c['hazard_test_points']['water'][0])
        self.assertEqual(p.data['game']['penalties'], 1)

        def correct(kind):
            return self.client.post(
                self.url + '/correct',
                json=dict(
                    kind=kind, key=p.latest_played_shot()['key'], turn=p.data['game']['turn']
                ),
            )

        self.assertEqual(correct('misread').status_code, 200)
        self.assertEqual(p.data['game']['position'], before['position'])
        self.assertEqual(p.data['game']['penalties'], 0)
        self.hit(c['pin'])
        self.assertTrue(p.data['game']['holed'])
        self.assertEqual(correct('mulligan').status_code, 200)
        self.assertFalse(p.data['game']['holed'])
        self.assertEqual((p.summary()['mulligans'], p.summary()['misreads']), (1, 1))
        self.assertEqual(self.service.load_session(p.data['id']).data, p.data)

    def test_all_18_holes_putting_scorecard_review_and_delete_restore(self):
        p = self.p
        sid = p.data['id']
        expected = 0
        self.assertEqual(self.next().status_code, 409)
        for index in range(18):
            c = p.data['course']
            with self.subTest(hole=index + 1):
                self.assertEqual(c['hole_number'], index + 1)
                for point in c['playing_line'][1:-1]:
                    self.hit(point)
                last = c['playing_line'][-2]
                pin = c['pin']
                d = math.dist(last, pin)
                self.hit([pin[i] + (last[i] - pin[i]) * 4 / d for i in (0, 1)])
                self.assertEqual(p.data['game']['lie'], 'green')
                self.assertAlmostEqual(p.summary()['remaining_yd'], 4)
                self.hit(pin)
                self.assertTrue(p.data['game']['holed'])
                expected += len(c['playing_line'])
                self.assertEqual(p.summary()['strokes'], expected)
                self.assertEqual(p.summary()['holes_completed'], index + 1)
                self.assertEqual(p.summary()['penalties'], 0)
                self.assertEqual(bool(p.data['ended']), index == 17)
                saved = self.service.load_session(sid)
                self.assertEqual(saved.data, p.data)
                self.assertEqual(saved.summary(), p.summary())
                if index < 17:
                    oldturn = p.data['game']['turn']
                    self.assertEqual(self.next().status_code, 200)
                    self.assertEqual(self.next(oldturn).status_code, 409)
                    self.assertEqual(p.data['game']['turn'], oldturn + 1)
                    self.assertEqual(p.data['game']['strokes'], 0)
        frozen = copy.deepcopy(p.data['round'])
        self.assertEqual(self.next().status_code, 409)
        self.assertTrue(p.summary()['round_complete'])
        self.client.post(f'/api/sessions/{sid}/exclude', json={'key': p.data['shots'][0]['key']})
        self.assertEqual(p.summary()['strokes'], expected)
        self.assertEqual(p.data['round'], frozen)
        self.assertEqual(self.client.delete(f'/api/sessions/{sid}').status_code, 200)
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/restore', json={}).status_code, 200)
        self.assertEqual(self.service.load_session(sid).summary()['strokes'], expected)

    def test_pause_late_shots_failed_next_and_resume(self):
        p = self.p
        sid = p.data['id']
        event = simulated_event(p, 100)
        event['seq'] = 99
        self.hit(p.data['course']['pin'])
        self.assertIsNone(p.data['ended'])
        score = p.summary()['strokes']
        self.assertTrue(p.add(event))
        self.assertFalse(p.data['shots'][-1]['scored'])
        self.assertEqual(p.summary()['strokes'], score)
        self.assertEqual(len(p.data['round']['results']), 1)
        before = copy.deepcopy(p.data)
        with patch.object(p, 'save', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.service.game_action(sid, 'next', {'turn': p.data['game']['turn']})
        self.assertEqual(p.data, before)
        self.assertEqual(self.service.load_session(sid).data, before)
        self.service.practice = None
        self.service.resume_practice(sid)
        self.p = p = self.service.practice
        self.assertTrue(p.data['game']['holed'])
        self.assertEqual(self.next().status_code, 200)
        stale = simulated_event(p, 100)
        stale['game_context']['hole_id'] = event['game_context']['hole_id']
        self.assertTrue(p.add(stale))
        self.assertFalse(p.data['shots'][-1]['scored'])
        self.assertEqual(p.data['game']['strokes'], 0)
        self.assertEqual(p.summary()['strokes'], score)
        self.hit(p.data['course']['pin'])
        self.assertEqual(len(p.data['round']['results']), 2)
        self.assertEqual(p.summary()['strokes'], score + 1)
