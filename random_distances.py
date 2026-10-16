"""Random distances: the range draws a new carry target after every scored shot (D67).

The golfer chooses the club for each target; nothing suggests one. Shots are scored like the
range, on OpenGolfCoach carry within ±depth/2 (D63). A shot without a usable carry is recorded
unscored and keeps the same target. Each scored shot advances; the session finishes itself after
`repetitions` scored shots. Exclusion and removal change statistics, never progression.
"""

import math
import random
import statistics
import uuid
from pathlib import Path

from driving_range import DrivingRangeSession
from distance_ladder import numeric
from putting import timestamp

RANDOM_FIELDS = (
    'random_min',
    'random_max',
    'random_step',
    'random_gap',
    'random_count',
    'range_width',
    'range_depth',
    'handedness',
    'demo',
)


def target_grid(low, high, step):
    """Every drawable target: `low` and each `step` above it, up to `high`."""
    return [round(low + i * step, 6) for i in range(math.floor((high - low) / step + 1e-9) + 1)]


def candidates(grid, current, gap):
    """Targets at least `gap` yd from the current one, so the next shot needs a new swing."""
    if current is None:
        return list(grid)
    return [t for t in grid if abs(t - current) >= max(gap, 1e-6) - 1e-9]


class RandomDistanceSession(DrivingRangeSession):
    def __init__(
        self,
        folder,
        store=None,
        equipment_selection=None,
        random_min=60,
        random_max=180,
        random_step=5,
        random_gap=15,
        random_count=20,
        range_width=30,
        range_depth=20,
        handedness='right_handed',
        demo=False,
    ):
        if not all(numeric(v, 1, 450) for v in (random_min, random_max)) or not (
            random_max > random_min
        ):
            raise ValueError('Enter distances from 1–450 yd, with the longest above the shortest.')
        if not numeric(random_step, 1, 50) or not numeric(random_gap, 0, 200):
            raise ValueError('Rounding must be 1–50 yd and the minimum change 0–200 yd.')
        if type(random_count) is not int or not 1 <= random_count <= 200:
            raise ValueError('Choose 1–200 targets.')
        if not numeric(range_width, 1, 200) or not numeric(range_depth, 1, 200):
            raise ValueError('Target width and distance window must be 1–200 yd.')
        if handedness not in ('right_handed', 'left_handed') or not isinstance(demo, bool):
            raise ValueError('Choose a valid handedness and range mode.')
        grid = target_grid(random_min, random_max, random_step)
        if len(grid) < 2 or any(not candidates(grid, t, random_gap) for t in grid):
            raise ValueError(
                'Every target needs another at least the minimum change away. Widen the '
                'distance range, or lower the rounding or the minimum change.'
            )
        self.folder, self.store = Path(folder), store
        first = random.choice(grid)
        self.data = dict(
            id=uuid.uuid4().hex,
            started=timestamp(),
            ended=None,
            drill='Random distances',
            practice_type='full_swing',
            session_kind='driving_range',
            target_plan='random',
            random_pace=False,
            target=first,
            range_target=first,
            range_width=range_width,
            range_depth=range_depth,
            random_min=random_min,
            random_max=random_max,
            random_step=random_step,
            random_gap=random_gap,
            repetitions=random_count,
            completed_shots=0,
            handedness=handedness,
            demo=demo,
            equipment_selection=equipment_selection,
            shots=[],
            cleanup_revision=0,
            cleanup_history=[],
        )
        self.save()

    def shot_context(self, event):
        # The session's own draw is the target, even if a shot arrived before the source saw it.
        return {k: self.data[k] for k in ('range_target', 'range_width', 'range_depth')}

    def advance(self, shot):
        if not shot['scored']:
            shot['unscored_reason'] = 'Carry unavailable; target unchanged.'
            return
        self.data['completed_shots'] += 1
        shot['target_number'] = self.data['completed_shots']
        if self.data['completed_shots'] >= self.data['repetitions']:
            self.data['ended'] = timestamp()
            return
        grid = target_grid(
            self.data['random_min'], self.data['random_max'], self.data['random_step']
        )
        target = random.choice(candidates(grid, self.data['range_target'], self.data['random_gap']))
        self.data.update(target=target, range_target=target)

    def summary(self):
        result = super().summary()
        scored = [
            s
            for s in self.data['shots']
            if s['scored'] and not s.get('excluded') and not s.get('removed')
        ]
        errors = [s['distance_error_yd'] for s in scored]
        result['targets'] = dict(
            completed=self.data['completed_shots'],
            total=self.data['repetitions'],
            scored=len(scored),
            in_window=sum(s['success'] for s in scored),
            mean_error=statistics.mean(errors) if errors else None,
            mean_absolute_error=statistics.mean(abs(e) for e in errors) if errors else None,
            short=sum(e < -1e-9 for e in errors),
            long=sum(e > 1e-9 for e in errors),
        )
        return result
