"""Input profiles: how to read a standard Open Connect sender that cannot say what it measured (D74).

A plain GSPro Open Connect packet has no way to mark a value as estimated or a zero as "not measured".
Connectors fill both in: rēlā, for a Foresight LPi, sends its own model's face angle, lie, loft,
closure rate, impact location and carry next to the club speed, attack angle and path the LPi
measures, and zero spin for putts (rēlā's own log labels each value measured or "SIE-physics+MLP").

The golfer chooses the profile on the Relay page. It applies only to standard senders; a sender
using the TraceLoft extension (TraceCapture) classifies its own values. Every decision is recorded
per field, so the Relay diagnostics can show what was confirmed and why.
"""

from open_connect import BALL, CLUB

SPIN_FIELDS = ('back_spin', 'side_spin', 'total_spin', 'spin_axis')
WIRE = {**{f: ('BallData', k) for k, f in BALL.items()}, **{f: ('ClubData', k) for k, f in CLUB.items()}}

PROFILES = {
    'standard': dict(
        title='Standard Open Connect',
        description='Every value the sender supplies is stored as a measurement.',
    ),
    'rela_lpi': dict(
        title='rēlā · Foresight LPi',
        description=(
            'The LPi measures ball data plus club speed, attack angle and path. rēlā estimates face '
            'angle, lie, loft, closure rate, impact location and carry: those are kept as rēlā '
            'estimates, never measurements. All-zero spin means no spin was measured (putts).'
        ),
        estimator='rela',
        source_name='rēlā',  # named in "not connected" alerts
        measured_club=('club_speed', 'attack_angle', 'club_path'),
        estimated=(
            'face_angle',
            'dynamic_lie',
            'dynamic_loft',
            'closure_rate',
            'impact_horizontal',
            'impact_vertical',
            'carry',
        ),
    ),
}
DEFAULT = 'standard'


def describe():
    """The profiles for the Relay page."""
    return [dict(id=key, title=p['title'], description=p['description']) for key, p in PROFILES.items()]


def sent_value(packet, field):
    """The value the sender put on the wire for a TraceLoft field, or None."""
    block, key = WIRE[field]
    data = packet.get(block)
    return data.get(key) if isinstance(data, dict) else None


def classify(profile_id, packet, vals):
    """Apply a profile to one validated standard packet.

    vals: what open_connect.validate_packet read (wire values under TraceLoft field names).
    Returns (vals to store as measurements, estimates {field: value} or {}, fields), where fields is
    one diagnostics row per wire value: {field, block, key, sent, stored: 'measurement' | 'estimate' |
    'missing' | 'evidence', reason}. Raw packets are kept whole either way.
    """
    profile = PROFILES[profile_id]
    measured = dict(vals)
    estimates = {}
    rows = {}

    def row(field, stored, reason):
        block, key = WIRE[field]
        rows[field] = dict(field=field, block=block, key=key, sent=sent_value(packet, field),
                           stored=stored, reason=reason)

    club_declared = packet['ShotDataOptions'].get('ContainsClubData')
    for field in WIRE:
        sent = sent_value(packet, field)
        if sent is None:
            continue
        block = WIRE[field][0]
        if block == 'ClubData' and not club_declared:
            row(field, 'evidence', 'ContainsClubData is false')
        elif field in vals:
            row(field, 'measurement', 'sent by the source')
        else:
            row(field, 'evidence', 'kept in the raw packet only')

    if profile_id == 'standard':
        return measured, estimates, list(rows.values())

    spins = {k: vals[k] for k in SPIN_FIELDS if vals.get(k) is not None}
    if spins and all(v == 0 for v in spins.values()):
        for field in spins:
            measured[field] = None
            row(field, 'missing', 'all spin 0: no spin measured (putt)')
    club = packet.get('ClubData') if club_declared else None
    club_speed = club.get('Speed') if isinstance(club, dict) else None
    for field in profile['estimated']:
        value = sent_value(packet, field)
        if value is None or (field != 'carry' and not club_declared):
            continue
        measured.pop(field, None)
        if value == 0:
            row(field, 'missing', 'exactly 0: not measured')
        elif field != 'carry' and not club_speed:
            row(field, 'evidence', 'no club speed: club data ignored')
        else:
            estimates[field] = value
            row(field, 'estimate', f"{profile['source_name']} estimate; the device does not measure it")
    for field in profile['measured_club']:
        value = sent_value(packet, field)
        if value is None or not club_declared:
            continue
        if not club_speed:
            measured.pop(field, None)
            row(field, 'evidence', 'no club speed: club data ignored')
        elif value == 0:
            measured.pop(field, None)
            row(field, 'missing', 'exactly 0: not measured')
    return measured, estimates, list(rows.values())
