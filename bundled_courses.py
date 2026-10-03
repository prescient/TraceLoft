"""Explicit, versioned built-in course library; saved rounds own their copy."""
import json
from pathlib import Path

COURSE_IDS = ('meadow-one-v2', 'willow-cove-155-v1', 'pine-bend-365-v1', 'meadow-reach-525-v1')


def load_bundled(course_id):
    if course_id not in COURSE_IDS:
        raise ValueError('Choose an available course from the library.')
    return json.loads((Path(__file__).parent/'courses'/f'{course_id}.json').read_text(encoding='utf-8'))


def bundled_catalog():
    result=[]
    for course_id in COURSE_IDS:
        c=load_bundled(course_id)
        result.append(dict(id=c['id'],name=c['name'],par=c['par'],yards=c['yards'],imported=False,
            image=c['image']['href'],description=c.get('description','A generous fairway, water and two greenside bunkers.')))
    return result
