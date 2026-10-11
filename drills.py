"""The drill registry: catalog identity, session creation and restoration in one place.

Two names identify a drill and both are persisted, so neither is display copy:
  - `id` is the stable catalog/route identifier the browser uses.
  - `drill` is stored in every session; saved sessions and analysis group by it.
Change `title` and `description` freely; never rename `id` or `drill`.

Adding a drill:
  1. Add a Drill entry to CATALOG (choose a new id and drill name).
  2. If it needs its own scorer, register a factory in FACTORIES (keyed by `drill`). Otherwise it
     falls through to the putting scorer.
  3. If its sessions need a different scorer class when reopened, give the persisted data a
     distinguishing field, extend session_kind() and add the class to _session_class().
  4. Add request fields to web_app.PracticeParams, browser setup/runner modules, tests,
     and update NAVIGATION.md.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Drill:
    id: str
    title: str
    description: str
    drill: str
    random_pace: bool = False
    category: str | None = None

    def entry(self):
        """The /api/drills DTO; putting drills have no category key."""
        result = dict(id=self.id, title=self.title, description=self.description, drill=self.drill)
        if self.category:
            result['category'] = self.category
        result['random_pace'] = self.random_pace
        return result


CATALOG = (
    Drill(
        'golf-sim',
        'Meadow One · 2D golf',
        'Play an original par four with estimated lies and putting.',
        '2D golf',
        category='PLAY',
    ),
    Drill(
        'wedge-matrix',
        'Wedge matrix',
        'Map each wedge at your own swing lengths and find a shot for every yardage.',
        'Wedge matrix',
        category='WEDGES',
    ),
    Drill(
        'bag-mapping',
        'Bag mapping / gapping',
        'Collect per-club samples and discover distance gaps and overlaps.',
        'Bag mapping',
        category='FULL SWING',
    ),
    Drill(
        'driving-range',
        'Driving range',
        'Free practice, shot dispersion, flight estimates and a workspace to review your shots.',
        'Driving range',
        category='FULL SWING',
    ),
    Drill(
        'distance-ladder',
        'Distance ladder',
        'Build carry or total-distance control with wedges, irons and custom yardages.',
        'Distance ladder',
        category='FULL SWING',
    ),
    Drill(
        'pace',
        'Pace consistency',
        'Repeat a speed target and build a consistent stroke.',
        'Pace consistency',
    ),
    Drill(
        'line', 'Start line', 'Train your launch direction inside a chosen window.', 'Start line'
    ),
    Drill(
        'combined',
        'Pace + start line',
        'Combine pace and direction in one scored session.',
        'Pace + start line',
    ),
    Drill(
        'random',
        'Random pace',
        'A fresh target after every putt. Stay adaptable.',
        'Pace + start line',
        random_pace=True,
    ),
    Drill(
        'ladder',
        'Putting ladder',
        'Climb distance targets on a flat virtual green. Train estimated short/long control.',
        'Putting ladder',
    ),
)


def catalog():
    return [drill.entry() for drill in CATALOG]


def _folder(service):
    return service.root / 'practice_sessions'


def _selected(service, params):
    from equipment import selection

    return selection(
        service.equipment, params.get('range_bag_id', ''), params.get('range_club_id', '')
    )


def create_golf(service, params):
    from course_import import load
    from golf_sim import GAME_FIELDS, GolfSimSession

    return GolfSimSession(
        _folder(service),
        store=service.store,
        equipment_selection=_selected(service, params),
        course=load(service.store, params.get('game_course_id', 'pebble-boulder-blue-v3')),
        **{k: v for k, v in params.items() if k in GAME_FIELDS or k in ('demo', 'stimp')},
    )


def create_collection(service, params):
    from collection import CollectionSession

    return CollectionSession(
        _folder(service),
        service.equipment,
        params.get('range_bag_id', ''),
        params.get('collection_clubs', []),
        samples=params.get('collection_samples', 5),
        metric=params.get('range_metric', 'carry'),
        demo=params.get('demo', False),
        handedness=params.get('handedness', 'right_handed'),
        store=service.store,
        swing_labels=params.get('swing_labels') if params['drill'] == 'Wedge matrix' else None,
    )


def create_range(service, params):
    from driving_range import DRIVING_FIELDS, DrivingRangeSession

    return DrivingRangeSession(
        _folder(service),
        store=service.store,
        equipment_selection=_selected(service, params),
        **{k: v for k, v in params.items() if k in DRIVING_FIELDS},
    )


def create_distance_ladder(service, params):
    from distance_ladder import RANGE_FIELDS, DistanceLadderSession

    return DistanceLadderSession(
        _folder(service),
        store=service.store,
        equipment_selection=_selected(service, params),
        **{
            k: v
            for k, v in params.items()
            if k in RANGE_FIELDS and k not in ('range_bag_id', 'range_club_id')
        },
    )


def create_putting(service, params):
    """Putting drills, and the validating fallback for unknown drill names."""
    from collection import COLLECTION_FIELDS
    from distance_ladder import RANGE_FIELDS
    from driving_range import DRIVING_FIELDS
    from golf_sim import GAME_FIELDS
    from putting import PuttingSession

    other = set(RANGE_FIELDS) | set(DRIVING_FIELDS) | set(COLLECTION_FIELDS) | set(GAME_FIELDS)
    return PuttingSession(
        _folder(service),
        store=service.store,
        **{k: v for k, v in params.items() if k not in other},
    )


FACTORIES = {
    '2D golf': create_golf,
    'Bag mapping': create_collection,
    'Wedge matrix': create_collection,
    'Driving range': create_range,
    'Distance ladder': create_distance_ladder,
}


def create(service, params):
    """Create and persist a new session for validated PracticeParams."""
    return FACTORIES.get(params['drill'], create_putting)(service, params)


def session_kind(data):
    """Which scorer owns persisted session data. Derived from existing fields; no migration."""
    if data.get('session_kind') == 'golf_sim':
        return 'golf_sim'
    if data.get('session_kind') == 'driving_range':
        return 'collection' if data.get('collection_kind') else 'driving_range'
    if data.get('practice_type') == 'full_swing':
        return 'distance_ladder'
    return 'putting'


def _session_class(kind):
    if kind == 'golf_sim':
        from golf_sim import GolfSimSession

        return GolfSimSession
    if kind == 'collection':
        from collection import CollectionSession

        return CollectionSession
    if kind == 'driving_range':
        from driving_range import DrivingRangeSession

        return DrivingRangeSession
    if kind == 'distance_ladder':
        from distance_ladder import DistanceLadderSession

        return DistanceLadderSession
    from putting import PuttingSession

    return PuttingSession


def restore(session):
    """Rewrap a loaded session in its scorer class without changing data or lifecycle."""
    cls = _session_class(session_kind(session.data))
    if type(session) is cls:
        return session
    restored = cls.__new__(cls)
    restored.folder, restored.store, restored.data = session.folder, session.store, session.data
    return restored
