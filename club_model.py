"""Estimated club delivery from measured launch and club data (D64).

The LPi measures ball speed, launch angle and direction, spin, club speed, attack angle and club path,
but not the face. Ball-flight (D-plane) relationships estimate the rest:

- Start direction is mostly face: launch_dir = k * face + (1 - k) * path, so
  face = (launch_dir - (1 - k) * path) / k.
- Launch angle is mostly dynamic loft: launch_ang = a * loft + (1 - a) * attack, so
  loft = (launch_ang - (1 - a) * attack) / a.
- Face to path = face - path; spin loft = dynamic loft - attack angle.
- Cross-check: the spin axis tilts with face to path over spin loft, so
  face_to_path_from_spin = spin_loft * tan(spin_axis) is an independent estimate. The two agree on a
  centered strike; a large gap suggests an off-center hit (gear effect), which the LPi cannot see.

Angles are target-relative like the measurements (right positive; attack and loft upward-positive), so
a positive face angle is open for a right-hander and closed for a left-hander. The weights are typical
values per club type, not fitted to this player; nothing here is ever written into measurements.
"""

import math

MODEL = 'traceloft-dplane-v1'
# club type -> (k: face share of start direction, a: loft share of launch angle)
WEIGHTS = {
    'driver': (0.85, 0.85),
    'wood': (0.80, 0.82),
    'hybrid': (0.78, 0.80),
    'iron': (0.75, 0.78),
    'wedge': (0.65, 0.75),
    'putter': (0.90, 0.90),
}
PUTT_SPEED = 25.0  # mph: an untagged shot slower than this is treated as a putt


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def club_type(equipment, vals):
    """(type, how it was chosen) from the shot's club tag, else from ball speed."""
    label = str((equipment or {}).get('club_label') or '').strip().upper()
    if label in ('D', 'DR', 'DRIVER') or 'DRIVER' in label:
        return 'driver', 'tag'
    if label in ('PT', 'PUTTER') or 'PUTT' in label:
        return 'putter', 'tag'
    if label in ('PW', 'GW', 'AW', 'SW', 'LW', 'UW') or 'WEDGE' in label or '°' in label:
        return 'wedge', 'tag'
    if label.endswith('W') or 'WOOD' in label:
        return 'wood', 'tag'
    if label.endswith('H') or 'HYBRID' in label:
        return 'hybrid', 'tag'
    if label.endswith('I') or 'IRON' in label:
        return 'iron', 'tag'
    speed = vals.get('ball_speed')
    return ('putter' if finite(speed) and speed < PUTT_SPEED else 'iron'), 'default'


def estimate(vals, equipment=None, club=None):
    """Estimated face angle, face to path, dynamic loft and spin loft (None when inputs are missing).

    club: an explicit (type, how it was chosen) that overrides club_type(), for callers that know more
    than the ball speed, e.g. a shot with measured spin is not a putt however slow it is (D71)."""
    kind, source = club or club_type(equipment, vals)
    k, a = WEIGHTS[kind]
    hla, path = vals.get('launch_dir'), vals.get('club_path')
    vla, attack = vals.get('launch_ang'), vals.get('attack_angle')
    face = (hla - (1 - k) * path) / k if finite(hla) and finite(path) else None
    face_to_path = face - path if face is not None else None
    loft = (vla - (1 - a) * attack) / a if finite(vla) and finite(attack) else None
    spin_loft = loft - attack if loft is not None else None
    axis = vals.get('spin_axis')
    if not finite(axis) and finite(vals.get('back_spin')) and finite(vals.get('side_spin')):
        axis = math.degrees(math.atan2(vals['side_spin'], vals['back_spin']))
    from_spin = (
        spin_loft * math.tan(math.radians(axis))
        if spin_loft is not None and finite(axis) and abs(axis) < 80
        else None
    )
    return dict(
        model=MODEL,
        club_type=kind,
        club_type_source=source,
        face_angle=face,
        face_to_path=face_to_path,
        dynamic_loft=loft,
        spin_loft=spin_loft,
        face_to_path_from_spin=from_spin,
    )
