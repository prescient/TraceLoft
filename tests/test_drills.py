import asyncio
import tempfile
import unittest

from fastapi.testclient import TestClient

import drills
from collection import CollectionSession
from distance_ladder import DistanceLadderSession
from driving_range import DrivingRangeSession
from golf_sim import GolfSimSession
from putting import PuttingSession
from web_app import create_app
from web_service import GolfService


# The /api/drills DTO the browser depends on. Ids and drill names are persisted identifiers.
EXPECTED_CATALOG = [
    ('golf-sim', '2D golf', 'PLAY', False),
    ('wedge-matrix', 'Wedge matrix', 'WEDGES', False),
    ('bag-mapping', 'Bag mapping', 'FULL SWING', False),
    ('driving-range', 'Driving range', 'FULL SWING', False),
    ('distance-ladder', 'Distance ladder', 'FULL SWING', False),
    ('pace', 'Pace consistency', None, False),
    ('line', 'Start line', None, False),
    ('combined', 'Pace + start line', None, False),
    ('random', 'Pace + start line', None, True),
    ('ladder', 'Putting ladder', None, False),
]


class DrillCatalogTests(unittest.TestCase):
    def test_catalog_identity_and_dto_shape_are_stable(self):
        catalog = drills.catalog()
        self.assertEqual(
            [(d['id'], d['drill'], d.get('category'), d['random_pace']) for d in catalog],
            EXPECTED_CATALOG,
        )
        for entry in catalog:
            expected = {'id', 'title', 'description', 'drill', 'random_pace'}
            if entry.get('category'):
                expected.add('category')
            self.assertEqual(set(entry), expected)
            self.assertTrue(entry['title'] and entry['description'])

    def test_ids_are_unique_and_factories_name_catalog_drills(self):
        ids = [d.id for d in drills.CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        names = {d.drill for d in drills.CATALOG}
        self.assertLessEqual(set(drills.FACTORIES), names)

    def test_session_kind_is_derived_from_persisted_fields(self):
        cases = [
            (dict(session_kind='golf_sim'), 'golf_sim', GolfSimSession),
            (dict(session_kind='driving_range'), 'driving_range', DrivingRangeSession),
            (dict(session_kind='driving_range', collection_kind='wedge'), 'collection', CollectionSession),
            (dict(practice_type='full_swing'), 'distance_ladder', DistanceLadderSession),
            (dict(practice_type='putting'), 'putting', PuttingSession),
            ({}, 'putting', PuttingSession),
        ]
        for data, kind, cls in cases:
            self.assertEqual(drills.session_kind(data), kind)
            session = PuttingSession.__new__(PuttingSession)
            session.folder = session.store = None
            session.data = data
            restored = drills.restore(session)
            self.assertIs(type(restored), cls)
            self.assertIs(restored.data, data)


class DrillLifecycleTests(unittest.TestCase):
    """Every catalog drill launches through the registry and reopens with the same scorer."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.client = TestClient(create_app(self.service), base_url='http://localhost')
        bag = self.service.equipment['bags'][0]
        clubs = [c['id'] for c in bag['clubs'][6:8]]
        self.extra = {
            '2D golf': dict(demo=True, game_course_id='meadow-one-v1'),
            'Bag mapping': dict(range_bag_id=bag['id'], collection_clubs=clubs, demo=True),
            'Wedge matrix': dict(range_bag_id=bag['id'], collection_clubs=clubs, demo=True),
        }

    def tearDown(self):
        self.client.close()
        asyncio.run(self.service.shutdown())
        self.temp.cleanup()

    def test_each_catalog_drill_round_trips_through_its_scorer(self):
        listed = self.client.get('/api/drills').json()
        self.assertEqual(listed, drills.catalog())
        for entry in listed:
            with self.subTest(drill=entry['id']):
                body = dict(drill=entry['drill'], random_pace=entry['random_pace'])
                body.update(self.extra.get(entry['drill'], {}))
                response = self.client.post('/api/practice', json=body)
                self.assertEqual(response.status_code, 200, response.text)
                live = self.service.practice
                self.assertEqual(live.data['drill'], entry['drill'])
                reopened = self.service.load_session(live.data['id'])
                self.assertIs(type(reopened), type(live))
                self.assertEqual(reopened.data, live.data)
                self.service.change_practice(live.data['id'], 'abandon')

    def test_unknown_drill_is_rejected_by_the_putting_fallback(self):
        response = self.client.post('/api/practice', json=dict(drill='Not a drill'))
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self.service.practice)


if __name__ == '__main__':
    unittest.main()
