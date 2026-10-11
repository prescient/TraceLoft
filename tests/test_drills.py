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
        self.assertLessEqual(set(drills.SCORERS), names)

    def test_session_kind_is_derived_from_persisted_fields(self):
        cases = [
            (dict(session_kind='golf_sim'), 'golf_sim', GolfSimSession),
            (dict(session_kind='driving_range'), 'driving_range', DrivingRangeSession),
            (
                dict(session_kind='driving_range', collection_kind='wedge'),
                'collection',
                CollectionSession,
            ),
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


class TypedParamsTests(unittest.TestCase):
    def test_each_scorer_declares_exactly_the_fields_its_session_receives(self):
        from collection import COLLECTION_FIELDS
        from distance_ladder import RANGE_FIELDS
        from driving_range import DRIVING_FIELDS
        from golf_sim import GAME_FIELDS

        expected = {
            '2D golf': {*GAME_FIELDS, 'demo', 'stimp', 'range_bag_id', 'range_club_id'},
            'Bag mapping': {
                *COLLECTION_FIELDS,
                'range_bag_id',
                'range_club_id',
                'range_metric',
                'demo',
                'handedness',
            },
            'Driving range': {*DRIVING_FIELDS, 'range_bag_id', 'range_club_id'},
            'Distance ladder': set(RANGE_FIELDS),
        }
        for drill, fields in expected.items():
            with self.subTest(drill=drill):
                self.assertEqual(set(drills.scorer(drill).params.model_fields) - {'drill'}, fields)
        other = set().union(*expected.values())
        putting = set(drills.scorer('Pace consistency').params.model_fields) - {'drill'}
        self.assertFalse(putting & (other - {'stimp'}))

    def test_envelope_is_the_union_and_rejects_unknown_keys(self):
        import pydantic

        from drill_params import SCORER_PARAMS, PracticeParams

        union = set().union(*(model.model_fields for model in SCORER_PARAMS))
        self.assertEqual(set(PracticeParams.model_fields), union)
        self.assertEqual(len(union), 48)
        with self.assertRaises(pydantic.ValidationError):
            PracticeParams(drill='Driving range', not_a_field=1)

    def test_conflicting_shared_field_is_rejected_at_definition(self):
        from pydantic import Field

        from drill_params import DrillParams, RangeParams, envelope

        class Conflict(DrillParams):
            range_target: float = Field(default=1, ge=0)

        with self.assertRaises(TypeError):
            envelope((RangeParams, Conflict))

    def test_scorer_validates_bounds_ignores_other_drills_fields_and_applies_defaults(self):
        import pydantic

        params = drills.scorer('Driving range').params.model_validate(
            dict(drill='Driving range', game_rough=12, range_width=40)
        )
        self.assertEqual((params.range_width, params.range_target), (40, 150))
        self.assertFalse(hasattr(params, 'game_rough'))
        with self.assertRaises(pydantic.ValidationError):
            drills.scorer('Driving range').params.model_validate(
                dict(drill='Driving range', range_width=0)
            )


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

    def test_direct_service_launch_gets_the_api_defaults(self):
        api = self.client.post('/api/practice', json=dict(drill='Driving range')).json()['practice']
        self.service.change_practice(api['id'], 'abandon')
        direct = self.service.create_practice(dict(drill='Driving range'))
        ignored = {'id', 'started', 'shots', 'equipment_selection'}
        self.assertEqual(
            {k: v for k, v in direct.items() if k not in ignored},
            {k: v for k, v in api.items() if k not in ignored},
        )

    def test_unknown_drill_is_rejected_by_the_putting_fallback(self):
        response = self.client.post('/api/practice', json=dict(drill='Not a drill'))
        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self.service.practice)


if __name__ == '__main__':
    unittest.main()
