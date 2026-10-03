"""Flat-green estimates: a constant-Stimp baseline and independently integrated Fuse braking.

This is an estimate, not the complete Fuse engine or observed stopping distance.
Model assumptions and the pinned research source are in docs/PUTTING_DISTANCE.md.
"""
import math

MODEL_ID = 'fuse-flat-braking-v1'
BASELINE_ID = 'stimp-constant-deceleration-v1'
DEFAULT_MODEL_ID = BASELINE_ID
SOURCE_REVISION = 'bd9e6225aaa7aeb3b1ce5e4feb234e55bcefdc42'
RELEASE_MPS = 1.83
BRAKING_SCALE = .3
STOP_MPS = .18
MPH_TO_MPS = .44704
FEET_TO_METERS = .3048


def finite_number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be {minimum}–{maximum}.')
    return value


def distance_ft(speed_mph, stimp, model_id=DEFAULT_MODEL_ID):
    """Travel until the green's stop threshold, with zero slope/skid/cup effects."""
    finite_number(speed_mph, 'Putting speed (mph)', 0, 15)
    finite_number(stimp, 'Stimp (ft)', 3, 20)
    speed = speed_mph * MPH_TO_MPS
    if model_id == BASELINE_ID:
        return stimp * (speed / RELEASE_MPS) ** 2
    if model_id != MODEL_ID:
        raise ValueError('Choose a supported distance model.')
    if speed <= STOP_MPS:
        return 0.0
    base = RELEASE_MPS ** 2 / (2 * stimp * FEET_TO_METERS)
    offset = 1 - BRAKING_SCALE * RELEASE_MPS
    # Integrate distance = integral(v / a(v), v=stop..initial).
    span = speed - STOP_MPS
    ratio = BRAKING_SCALE * span / (offset + BRAKING_SCALE * STOP_MPS)
    integral = span / BRAKING_SCALE - offset / BRAKING_SCALE ** 2 * math.log1p(ratio)
    return integral / base / FEET_TO_METERS


def required_speed_mph(target_ft, stimp, model_id=DEFAULT_MODEL_ID):
    finite_number(target_ft, 'Target distance (ft)', .5, 300)
    if target_ft > distance_ft(15, stimp, model_id):
        raise ValueError('Distance target requires more than 15 mph at this Stimp. Reduce the distance.')
    low, high = 0.0, 15.0
    for _ in range(55):
        middle = (low + high) / 2
        if distance_ft(middle, stimp, model_id) < target_ft:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def model_context(stimp, model_id=DEFAULT_MODEL_ID):
    finite_number(stimp, 'Stimp (ft)', 3, 20)
    if model_id not in (MODEL_ID, BASELINE_ID):
        raise ValueError('Choose a supported distance model.')
    return dict(id=model_id, source_revision=SOURCE_REVISION if model_id==MODEL_ID else 'Penner-2002-constant-rolling-Stimp', stimp_ft=stimp,
                release_speed_mps=RELEASE_MPS, braking_scale=BRAKING_SCALE if model_id==MODEL_ID else 0,
                stop_speed_mps=STOP_MPS if model_id==MODEL_ID else 0, slope_percent=0, method='estimated',
                assumptions='Flat green; launch speed used as rolling speed; no skid, slope or cup; uncalibrated.')
