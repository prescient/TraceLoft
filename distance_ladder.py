"""Full-swing ladders scored against reported carry/total, never putting estimates."""
import math
import statistics
import uuid
from pathlib import Path

from putting import PuttingSession, timestamp

RANGE_FIELDS = ('range_start', 'range_end', 'range_step', 'range_shots', 'range_rounds',
                'range_tolerance', 'range_order', 'range_metric', 'range_category', 'range_club',
                'range_bag_id', 'range_club_id')


def numeric(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high


class DistanceLadderSession(PuttingSession):
    # Reuse storage and lifecycle; full-swing scoring/progression are independent of putting.
    def __init__(self, folder, store=None, range_start=30, range_end=100, range_step=10,
                 range_shots=1, range_rounds=2, range_tolerance=5, range_order='ascending',
                 range_metric='carry', range_category='wedges', range_club='', equipment_selection=None):
        if range_metric not in ('carry', 'total'):
            raise ValueError('Choose carry or total distance.')
        maximum = 450 if range_metric == 'carry' else 600
        if not all(numeric(v, 1, maximum) for v in (range_start, range_end, range_step)) or range_end <= range_start:
            raise ValueError(f'Enter distances from 1–{maximum} yd, with the longest above the shortest.')
        intervals = (range_end - range_start) / range_step
        if abs(intervals - round(intervals)) > 1e-8 or intervals < 1:
            raise ValueError('Step must divide the distance range evenly.')
        if any(not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 100 for v in (range_shots, range_rounds)):
            raise ValueError('Shots per target and rounds must be whole numbers from 1–100.')
        if range_order not in ('ascending', 'descending') or range_category not in ('wedges', 'irons', 'custom'):
            raise ValueError('Choose a valid ladder order and preset.')
        if not numeric(range_tolerance, 0, 100):
            raise ValueError('Distance window must be 0–100 yd.')
        if not isinstance(range_club, str) or len(range_club.strip()) > 80:
            raise ValueError('Club/session label must be at most 80 characters.')
        targets = [range_start + i * range_step for i in range(round(intervals) + 1)]
        if range_order == 'descending':
            targets.reverse()
        repetitions = len(targets) * range_shots * range_rounds
        if repetitions > 1000:
            raise ValueError('Ladder must have at most 1000 scored shots.')
        self.folder, self.store = Path(folder), store
        self.data = dict(id=uuid.uuid4().hex, started=timestamp(), ended=None, drill='Distance ladder',
                         practice_type='full_swing', target_mode='reported_distance', target=targets[0],
                         repetitions=repetitions, shots=[], ladder_targets_yd=targets, completed_shots=0,
                         range_start=range_start, range_end=range_end, range_step=range_step,
                         range_shots=range_shots, range_rounds=range_rounds, range_tolerance=range_tolerance,
                         range_order=range_order, range_metric=range_metric, range_category=range_category,
                         range_club=range_club.strip(), equipment_selection=equipment_selection, random_pace=False)
        self.save()

    def add(self, event):
        if self.data['ended'] or event.get('result') not in ('sent', 'validated'):
            return False
        key = f"{event['session_id']}:{event['seq']}"
        if any(s['key'] == key for s in self.data['shots']):
            return False
        vals = event['vals']
        if not (numeric(vals.get('ball_speed'), 1, 220) and numeric(vals.get('launch_ang'), -10, 70)
                and numeric(vals.get('launch_dir'), -45, 45)):
            return False
        metric = self.data['range_metric']
        value = vals.get(metric)
        scored = numeric(value, 0, 450 if metric == 'carry' else 600)
        position = self.data['completed_shots']
        targets = self.data['ladder_targets_yd']
        target = self.data['target']
        error = value - target if scored else None
        equipment = event.get('equipment_selection', self.data.get('equipment_selection'))
        shot = dict(key=key, captured=event.get('captured_at') or timestamp(), vals=dict(vals),
                    target=target, target_distance_yd=target, distance_metric=metric,
                    distance_yd=value if scored else None, distance_error_yd=error, scored=scored,
                    success=scored and abs(error) <= self.data['range_tolerance'] + 1e-9, excluded=False,
                    club_label=equipment.get('club_label', '') if equipment else self.data['range_club'],
                    ladder_rung=(position // self.data['range_shots']) % len(targets) + 1,
                    ladder_round=position // (len(targets) * self.data['range_shots']) + 1)
        if equipment:
            shot.update(equipment)
        if event.get('receipt_id'):
            shot['receipt_id'] = event['receipt_id']
        if not scored:
            shot['unscored_reason'] = f'{metric.title()} unavailable or invalid; target unchanged.'
        self.data['shots'].append(shot)
        if scored:
            self.data['completed_shots'] += 1
            if self.data['completed_shots'] >= self.data['repetitions']:
                self.data['ended'] = timestamp()
            else:
                self.data['target'] = targets[(self.data['completed_shots'] // self.data['range_shots']) % len(targets)]
        self.save()
        return True

    def summary(self):
        included = [s for s in self.data['shots'] if not s['excluded']]
        scored = [s for s in included if s['scored']]
        errors = [s['distance_error_yd'] for s in scored]
        return dict(count=len(scored), successes=sum(s['success'] for s in scored),
                    recorded=len(self.data['shots']), unscored=sum(not s['scored'] for s in included),
                    distance_error_yd=dict(count=len(errors), mean=statistics.mean(errors) if errors else None,
                        sd=statistics.pstdev(errors) if errors else None,
                        short=sum(e < -1e-9 for e in errors), long=sum(e > 1e-9 for e in errors)))


def restore_model(session):
    """Choose the persisted drill's scorer without changing its data or lifecycle."""
    if session.data.get('session_kind') == 'golf_sim':
        from golf_sim import GolfSimSession
        restored = GolfSimSession.__new__(GolfSimSession)
        restored.folder, restored.store, restored.data = session.folder, session.store, session.data
        return restored
    if session.data.get('session_kind') == 'driving_range':
        from driving_range import DrivingRangeSession
        from collection import CollectionSession
        cls = CollectionSession if session.data.get('collection_kind') else DrivingRangeSession
        restored = cls.__new__(cls)
        restored.folder, restored.store, restored.data = session.folder, session.store, session.data
        return restored
    if session.data.get('practice_type') == 'full_swing':
        restored = DistanceLadderSession.__new__(DistanceLadderSession)
        restored.folder, restored.store, restored.data = session.folder, session.store, session.data
        return restored
    return session
