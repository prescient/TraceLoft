"""Persistent putting sessions with measured launch data and labeled distance estimates."""
import json
import math
import statistics
import uuid
import random
from datetime import datetime, timezone
from pathlib import Path
from putting_distance import distance_ft, required_speed_mph, model_context, finite_number, DEFAULT_MODEL_ID


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class PuttingSession:
    def __init__(self, folder, drill, target, speed_tolerance, angle_tolerance, repetitions,
                 random_pace=False, minimum=3.0, maximum=6.0, store=None,
                 stimp=10.0, target_mode='speed', target_distance=10.0, distance_tolerance=2.0,
                 ladder_start=5.0, ladder_end=25.0, ladder_step=5.0, ladder_rounds=2,
                 ladder_direction='ascending', distance_model=DEFAULT_MODEL_ID):
        numbers = (target, speed_tolerance, angle_tolerance)
        if not all(math.isfinite(float(n)) for n in numbers) or target <= 0 or min(speed_tolerance, angle_tolerance) < 0:
            raise ValueError("Enter a positive speed and nonnegative, finite tolerances.")
        if drill not in ("Pace consistency", "Start line", "Pace + start line", "Putting ladder"):
            raise ValueError("Choose a putting drill.")
        if not isinstance(repetitions, int) or not 1 <= repetitions <= 1000:
            raise ValueError("Repetitions must be 1–1000.")
        if random_pace and (not all(math.isfinite(n) for n in (minimum, maximum)) or
                            minimum < 1 or maximum > 15 or maximum - minimum < .1 - 1e-9):
            raise ValueError("Random pace range must be 1–15 mph, with max at least 0.1 mph above min.")
        if random_pace and math.floor(maximum * 10 + 1e-9) - math.ceil(minimum * 10 - 1e-9) < 1:
            raise ValueError("Random range must contain at least two targets in steps of 0.1 mph.")
        model = model_context(stimp, distance_model)
        finite_number(distance_tolerance, 'Distance tolerance (ft)', 0, 100)
        if target_mode not in ('speed', 'distance'):
            raise ValueError('Choose a speed or distance target.')
        ladder = drill == 'Putting ladder'
        targets = []
        if ladder:
            finite_number(ladder_start, 'Ladder shortest distance (ft)', .5, 300)
            finite_number(ladder_end, 'Ladder longest distance (ft)', .5, 300)
            finite_number(ladder_step, 'Ladder step (ft)', .5, 300)
            if ladder_end <= ladder_start or ladder_direction not in ('ascending', 'descending'):
                raise ValueError('Choose ascending/descending and a longest distance above the shortest.')
            intervals = (ladder_end - ladder_start) / ladder_step
            if abs(intervals - round(intervals)) > 1e-8:
                raise ValueError('Ladder step must divide the distance range evenly.')
            if not isinstance(ladder_rounds, int) or isinstance(ladder_rounds, bool) or not 1 <= ladder_rounds <= 100:
                raise ValueError('Ladder rounds must be 1–100.')
            targets = [ladder_start + i * ladder_step for i in range(round(intervals) + 1)]
            if ladder_direction == 'descending':
                targets.reverse()
            repetitions = len(targets) * ladder_rounds
            if repetitions > 1000:
                raise ValueError('Ladder must have at most 1000 putts.')
            required_speed_mph(ladder_end, stimp, distance_model)
            target_mode, target_distance = 'distance', targets[0]
        if (ladder or target_mode == 'distance') and random_pace:
            raise ValueError('Distance targets use a fixed target or the ladder, not Random pace.')
        if target_mode == 'distance' and drill == 'Start line':
            raise ValueError('Start line scores direction only. Choose a pace drill for distance targets.')
        if target_mode == 'distance':
            target = required_speed_mph(target_distance, stimp, distance_model)
        else:
            finite_number(target, 'Putting speed (mph)', .1, 15)
            target_distance = distance_ft(target, stimp, distance_model)
        self.folder = Path(folder)
        self.store = store
        self.data = dict(id=uuid.uuid4().hex, started=timestamp(), ended=None, drill=drill,
                         target=target, speed_tolerance=speed_tolerance,
                         angle_tolerance=angle_tolerance, repetitions=repetitions, shots=[],
                         random_pace=random_pace, minimum=minimum, maximum=maximum)
        self.data.update(stimp=stimp, distance_model=model, target_mode=target_mode,
                         target_distance_ft=target_distance, distance_tolerance=distance_tolerance)
        if ladder:
            self.data.update(ladder_targets_ft=targets, ladder_start=ladder_start, ladder_end=ladder_end,
                             ladder_step=ladder_step, ladder_rounds=ladder_rounds,
                             ladder_direction=ladder_direction)
        if random_pace:
            self.data["target"] = self.next_target()
            self.data['target_distance_ft'] = distance_ft(self.data['target'], stimp, distance_model)
        self.save()

    def next_target(self):
        candidates = [n / 10 for n in range(math.ceil(self.data["minimum"] * 10 - 1e-9),
                                          math.floor(self.data["maximum"] * 10 + 1e-9) + 1)
                      if abs(n / 10 - self.data["target"]) > .01]
        return random.choice(candidates)

    @classmethod
    def load(cls, path):
        session = cls.__new__(cls)
        session.folder = Path(path).parent
        session.store = None
        session.data = json.loads(Path(path).read_text(encoding="utf-8"))
        return session

    @classmethod
    def from_store(cls, store, session_id, deleted=False):
        session = cls.__new__(cls)
        session.store = store
        session.folder = store.path.parent
        session.data = store.load_session(session_id, deleted=deleted)
        return session

    @property
    def path(self):
        return self.folder / (self.data["id"] + ".json")

    def save(self):
        if self.store is not None:
            self.store.save_session(self.data)
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, allow_nan=False), encoding="utf-8")
        temporary.replace(self.path)

    def add(self, event):
        """Only confirmed records are scored; duplicate telemetry is ignored."""
        if self.data["ended"] or event.get("result") not in ("sent", "validated"):
            return False
        key = f"{event['session_id']}:{event['seq']}"
        if any(s["key"] == key for s in self.data["shots"]):
            return False
        vals = event["vals"]
        if not all(isinstance(vals.get(k), (int, float)) and math.isfinite(vals[k])
                   for k in ("ball_speed", "launch_dir", "launch_ang")):
            return False
        if isinstance(vals['ball_speed'], bool) or not 0 <= vals['ball_speed'] <= 15:
            return False
        pace = abs(vals["ball_speed"] - self.data["target"]) <= self.data["speed_tolerance"] + 1e-9
        line = abs(vals["launch_dir"]) <= self.data["angle_tolerance"] + 1e-9
        success = pace if self.data["drill"] == "Pace consistency" else line if self.data["drill"] == "Start line" else pace and line
        estimate = None
        if self.data.get('distance_model'):
            estimate = distance_ft(vals['ball_speed'], self.data['stimp'], self.data['distance_model']['id'])
            if self.data['target_mode'] == 'distance':
                pace = abs(estimate - self.data['target_distance_ft']) <= self.data['distance_tolerance'] + 1e-9
                success = pace and line if self.data['drill'] == 'Pace + start line' else pace
        self.data["shots"].append(dict(key=key, captured=timestamp(), vals=dict(vals),
                                       success=success, excluded=False, target=self.data["target"]))
        if estimate is not None:
            shot = self.data['shots'][-1]
            shot.update(estimated_distance_ft=estimate, target_distance_ft=self.data['target_distance_ft'],
                        distance_error_ft=estimate-self.data['target_distance_ft'],
                        distance_model_id=self.data['distance_model']['id'], stimp_ft=self.data['stimp'])
            if self.data['drill'] == 'Putting ladder':
                shot['ladder_rung'] = (len(self.data['shots'])-1) % len(self.data['ladder_targets_ft']) + 1
                shot['ladder_round'] = (len(self.data['shots'])-1) // len(self.data['ladder_targets_ft']) + 1
        if event.get('receipt_id'):
            self.data['shots'][-1]['receipt_id'] = event['receipt_id']
        if len(self.data["shots"]) >= self.data["repetitions"]:
            self.data["ended"] = timestamp()
        elif self.data.get("random_pace"):
            self.data["target"] = self.next_target()
            if self.data.get('distance_model'):
                self.data['target_distance_ft'] = distance_ft(self.data['target'], self.data['stimp'], self.data['distance_model']['id'])
        elif self.data['drill'] == 'Putting ladder':
            self.data['target_distance_ft'] = self.data['ladder_targets_ft'][len(self.data['shots']) % len(self.data['ladder_targets_ft'])]
            self.data['target'] = required_speed_mph(self.data['target_distance_ft'], self.data['stimp'], self.data['distance_model']['id'])
        self.save()
        return True

    def toggle_excluded(self, key):
        for shot in self.data["shots"]:
            if shot["key"] == key:
                shot["excluded"] = not shot["excluded"]
                self.save()
                return

    def finish(self):
        self.data["ended"] = self.data["ended"] or timestamp()
        self.save()

    def abandon(self):
        if self.data["ended"]:
            raise ValueError("This session has already ended.")
        self.data["ended"] = timestamp()
        self.data["abandoned"] = True
        self.save()

    def summary(self):
        shots = [s for s in self.data["shots"] if not s["excluded"]]
        result = dict(count=len(shots), successes=sum(s["success"] for s in shots))
        errors = [s["vals"]["ball_speed"] - s.get("target", self.data["target"]) for s in shots]
        result["pace_error"] = dict(mean=statistics.mean(errors) if errors else None,
                                     sd=statistics.pstdev(errors) if errors else None)
        for field in ("ball_speed", "launch_dir", "launch_ang"):
            values = [s["vals"][field] for s in shots]
            result[field] = dict(mean=statistics.mean(values) if values else None,
                                 sd=statistics.pstdev(values) if values else None)
        errors = [s['distance_error_ft'] for s in shots if 'distance_error_ft' in s]
        result['distance_error_ft'] = dict(count=len(errors), mean=statistics.mean(errors) if errors else None,
                                          sd=statistics.pstdev(errors) if errors else None,
                                          short=sum(e < -1e-9 for e in errors), long=sum(e > 1e-9 for e in errors))
        return result
