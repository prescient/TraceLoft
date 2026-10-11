"""Explicit, versioned built-in course library; saved rounds own their copy."""

import json
from pathlib import Path

COURSE_IDS = ('sheboygan-straits-blue-v2', 'pebble-boulder-blue-v3', 'judges-course-v1')
# Retain versioned assets/load compatibility for historical rounds and archived links.
RETIRED_IDS = (
    'meadow-one-v2',
    'willow-cove-155-v1',
    'pine-bend-365-v1',
    'meadow-reach-525-v1',
    'sheboygan-straits-blue-v1',
    'pebble-boulder-blue-v1',
    'pebble-boulder-blue-v2',
)


def load_bundled(course_id):
    if course_id not in COURSE_IDS + RETIRED_IDS:
        raise ValueError('Choose an available course from the library.')
    return json.loads(
        (Path(__file__).parent / 'courses' / f'{course_id}.json').read_text(encoding='utf-8')
    )


def bundled_catalog():
    result = []
    for course_id in COURSE_IDS:
        c = load_bundled(course_id)
        first = c.get('holes', [c])[0]
        holes = c.get('holes', [c])
        options = [
            dict(
                id='full',
                label=f'Full {len(holes)}' if len(holes) > 1 else 'Single hole',
                par=c['par'],
                yards=c['yards'],
            )
        ]
        if len(holes) == 18:
            options += [
                dict(
                    id=key,
                    label=label,
                    par=sum(h['par'] for h in selected),
                    yards=sum(h['yards'] for h in selected),
                )
                for key, label, selected in [
                    ('front', 'Front 9', holes[:9]),
                    ('back', 'Back 9', holes[9:]),
                ]
            ]
        result.append(
            dict(
                id=c['id'],
                name=c['name'],
                par=c['par'],
                yards=c['yards'],
                imported=False,
                image=first['image']['href'],
                hole_count=len(c.get('holes', [c])),
                tee_label=c.get('tee_label'),
                round_options=options,
                description=c.get(
                    'description', 'A generous fairway, water and two greenside bunkers.'
                ),
            )
        )
    return result
