"""Pinned OpenGolfCoach predictions; never overwrite provider measurements."""
import json
import math
from importlib.metadata import version

MODEL = 'opengolfcoach-0.3.0/golfdata-adapter-v1'
ASSUMPTIONS = {'temperature_kelvin': 298.15, 'pressure_pascals': 101325.0,
               'humidity_percent': 50.0, 'elevation_meters': 0.0,
               'ground': 'typical fairway; upstream rollout', 'wind': 'none',
               'coordinates': '+X forward, +Y right, +Z up', 'trajectory_hz': 10}


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def predict(vals, handedness='right_handed'):
    result = dict(model=MODEL, status='unavailable', assumptions=ASSUMPTIONS.copy())
    fields = {'ball_speed': ('ball_speed_meters_per_second', .44704, 1, 220),
              'launch_ang': ('vertical_launch_angle_degrees', 1, -10, 70),
              'launch_dir': ('horizontal_launch_angle_degrees', 1, -45, 45),
              'total_spin': ('total_spin_rpm', 1, 0, 20000),
              'spin_axis': ('spin_axis_degrees', 1, -180, 180)}
    missing = [k for k, (_, _, lo, hi) in fields.items()
               if not finite(vals.get(k)) or not lo <= vals[k] <= hi]
    if missing:
        return dict(result, reason='Needs valid ' + ', '.join(k.replace('_', ' ') for k in missing))
    inputs = {name: vals[k] * factor for k, (name, factor, _, _) in fields.items()}
    inputs.update(trajectory_enabled=True, trajectory_output_framerate_hz=10)
    result['inputs'] = inputs
    try:
        import opengolfcoach
        if version('opengolfcoach') != '0.3.0':
            return dict(result, reason='Install the pinned OpenGolfCoach 0.3.0 dependency.')
        derived = json.loads(opengolfcoach.calculate_derived_values(json.dumps(inputs)))['open_golf_coach']
        keys = {'carry_yd': ('carry_distance_meters', 1/.9144), 'total_yd': ('total_distance_meters', 1/.9144),
                'offline_yd': ('offline_distance_meters', 1/.9144), 'apex_ft': ('peak_height_meters', 1/.3048),
                'descent_deg': ('descent_angle_degrees', 1), 'hang_time_s': ('hang_time_seconds', 1)}
        metrics = {k: derived.get(source)*factor if finite(derived.get(source)) else None
                   for k, (source, factor) in keys.items()}
        p, v = derived['landing_position'], derived['landing_velocity']
        if not all(finite(p.get(k)) and finite(v.get(k)) for k in ('x', 'y', 'z')):
            raise ValueError('Invalid landing coordinates')
        # Recover the upstream total endpoint along its horizontal landing-velocity heading.
        # Upstream returns the magnitude of this vector, but only exposes landing offline.
        norm = math.hypot(v['x'], v['y'])
        hx, hy = (v['x']/norm, v['y']/norm) if norm > .01 else (1., 0.)
        dot = p['x']*hx+p['y']*hy
        total = derived['total_distance_meters']
        roll = max(0., -dot + math.sqrt(max(0., dot*dot+total*total-sum(p[k]**2 for k in ('x','y','z')))))
        points = [{k: round(point[k], 5) for k in ('t','x','y','z')}
                  for point in derived.get('trajectory', {}).get('points', [])]
        if len(points)>400 or any(not finite(n) for point in points for n in point.values()):
            raise ValueError('Invalid trajectory')
        result.update(status='ready', metrics=metrics, shape=derived.get('shot_name',{}).get(handedness, 'Unclassified'),
                      handedness=handedness, trajectory=points,
                      carry_point_yd={'forward': p['x']/.9144, 'right': p['y']/.9144},
                      total_point_yd={'forward': (p['x']+hx*roll)/.9144, 'right': (p['y']+hy*roll)/.9144},
                      endpoint_method='upstream total radius + landing heading reconstruction v1')
        json.dumps(result, allow_nan=False)
        return result
    except Exception as exc:
        return dict(model=MODEL, status='unavailable', assumptions=ASSUMPTIONS.copy(), inputs=inputs,
                    reason=f'Flight estimate unavailable ({type(exc).__name__}). Reported shots remain saved.')
