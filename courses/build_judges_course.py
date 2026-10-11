"""Design-only registration of Judges Course's finished aerials.

OpenCV/NumPy stay outside the application. Reviewed control points describe turf;
color contours describe pale sand/blue lakes and retain grass islands inside sand.
Input coordinates use a 1000-pixel-wide reference at the native aspect ratio.
Never overwrite a released version with changed geometry.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from course_geometry import classify
from course_import import polygon
from course_workbench import validate_edits

YARDS = [353, 460, 157, 365, 372, 496, 380, 153, 330, 362, 552, 322, 335, 137, 424, 145, 442, 378]
PARS = [4, 5, 3, 4, 4, 5, 4, 3, 4, 4, 5, 4, 4, 3, 4, 3, 5, 4]
IDENTITY = 'judges-course-v1'


def smooth(points, steps=4):
    """Closed smooth perimeter; explicit points ignore mowing-stripe false edges."""
    result = []
    for i, p1 in enumerate(points):
        p0, p2, p3 = points[i - 1], points[(i + 1) % len(points)], points[(i + 2) % len(points)]
        for k in range(steps):
            t = k / steps
            result.append(
                [
                    round(
                        0.5
                        * (
                            2 * p1[j]
                            + (-p0[j] + p2[j]) * t
                            + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                            + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t * t * t
                        ),
                        3,
                    )
                    for j in (0, 1)
                ]
            )
    return result


def rings(mask, minimum=45):
    """CCOMP keeps islands; unlike RETR_EXTERNAL it never fills ring bunkers."""
    found, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    if hierarchy is None:
        return result

    def simplify(c):
        for epsilon in (1, 1.5, 2, 3, 4, 6, 8, 12):
            ring = cv2.approxPolyDP(c, epsilon, True).reshape(-1, 2).tolist()
            try:
                polygon([ring], lambda p: p)
            except ValueError:
                continue
            return ring
        raise ValueError('Contour needs explicit repair')

    for i, c in enumerate(found):
        if hierarchy[0, i, 3] != -1 or cv2.contourArea(c) < minimum:
            continue
        holes = []
        child = hierarchy[0, i, 2]
        while child != -1:
            if cv2.contourArea(found[child]) >= 60:
                holes.append(simplify(found[child]))
            child = hierarchy[0, child, 0]
        p = dict(outer=simplify(c), holes=holes)
        try:
            polygon([p['outer'], *p['holes']], lambda p: p)
        except ValueError:
            raise ValueError('Contour cutouts need explicit repair')
        result.append(p)
    return result


def interior(p, width, height):
    mask = np.zeros((height, width), 'uint8')
    cv2.fillPoly(mask, [np.array(p['outer'], 'int32')], 255)
    for hole in p['holes']:
        cv2.fillPoly(mask, [np.array(hole, 'int32')], 0)
    _, _, _, point = cv2.minMaxLoc(cv2.distanceTransform(mask, cv2.DIST_L2, 5))
    return list(point)


def register(number, guide):
    print('Registering hole', number, flush=True)
    path = ROOT / 'web/art' / f'{IDENTITY}-hole-{number:02d}.png'
    raw = path.read_bytes()
    native = cv2.imdecode(np.frombuffer(raw, 'uint8'), cv2.IMREAD_COLOR)
    nh, nw = native.shape[:2]
    w = 1000
    h = round(nh * w / nw)
    image = cv2.resize(native, (w, h))
    b, g, r = [v.astype(float) + 0.001 for v in cv2.split(cv2.GaussianBlur(image, (3, 3), 0))]

    def mask(test, size=3):
        return cv2.morphologyEx(
            test.astype('uint8') * 255, cv2.MORPH_CLOSE, np.ones((size, size), 'uint8')
        )

    # Near-neutral pale sand; gray cart paths are darker and remain scenery.
    sandmask = mask(
        (r > 100)
        & (g > 100)
        & (b > 80)
        & (r >= g * 0.98)
        & (r / g < 1.24)
        & (b / g > 0.70)
        & (b / g < 1.06)
    )
    sandmask = cv2.morphologyEx(sandmask, cv2.MORPH_OPEN, np.ones((3, 3), 'uint8'))
    # Reviewed bunker seeds prevent pale shoreline rocks/cart paths becoming sand.
    labels_count, labels, _, _ = cv2.connectedComponentsWithStats(sandmask)
    selected = np.zeros_like(sandmask)
    for x, y in guide.get('sand_seeds', []):
        label = labels[y, x]
        if label == 0:
            ys, xs = np.where(sandmask > 0)
            nearest = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
            if math.dist((x, y), (int(xs[nearest]), int(ys[nearest]))) > 12:
                raise ValueError((number, 'Missing sand seed', x, y))
            label = labels[ys[nearest], xs[nearest]]
        selected[labels == label] = 255
    sand = rings(selected, 45)
    water = (
        rings(mask((b > r * 1.12) & (g > r * 1.04) & (b > 45), 9), 500)
        if number in (7, 8, 9, 15, 16, 17)
        else []
    )
    # Only reviewed blue lakes: discard disconnected blue shadow fragments.
    water = [
        p
        for p in water
        if any(
            cv2.pointPolygonTest(np.array(p['outer'], 'float32'), tuple(q), False) >= 0
            for q in guide.get('water_seeds', [])
        )
    ]
    for pond in water:
        pond['holes'] = []  # Reviewed lake interiors contain reflections, no land islands.
        pond['outer'] = (
            cv2.approxPolyDP(np.array(pond['outer'], 'int32'), 3, True).reshape(-1, 2).tolist()
        )

    def perimeter(r):
        return [[min(w - 0.01, max(0.01, x)), min(h - 0.01, max(0.01, y))] for x, y in smooth(r)]

    turf = {
        k: [dict(outer=perimeter(r), holes=[]) for r in guide.get(k, [])]
        for k in ('green', 'tee', 'fairway')
    }
    edge = [[0, 0], [w, 0], [w, h], [0, h]]
    clearings = [perimeter(r) for r in guide['clearing']]
    turf.update(sand=sand, water=water, nature=[dict(outer=edge, holes=clearings)])
    t = guide['tee_point']
    p = guide['pin']
    line = [t, *guide.get('route', []), p]
    scale = YARDS[number - 1] / sum(math.dist(a, b) for a, b in zip(line, line[1:]))

    def world(v):
        return [round((v[1] - t[1]) * scale, 6), round((v[0] - t[0]) * scale, 6)]

    def poly(p):
        return dict(
            outer=[world(v) for v in p['outer']],
            holes=[[world(v) for v in cut] for cut in p['holes']],
        )

    c = dict(
        id=f'{IDENTITY}-hole-{number:02d}',
        name=f'Hole {number}',
        hole_number=number,
        par=PARS[number - 1],
        yards=YARDS[number - 1],
        tee=world(t),
        pin=world(p),
        playing_line=[world(v) for v in line],
        boundary=poly(dict(outer=edge, holes=[])),
        bounds=[-t[1] * scale, (h - t[1]) * scale, -t[0] * scale, (w - t[0]) * scale],
        surfaces={k: [poly(v) for v in ps] for k, ps in turf.items()},
        image=dict(
            href=f'/assets/art/{path.name}',
            width=nw,
            height=nh,
            transform=[scale * w / nw, 0, 0, scale * w / nw, -t[0] * scale, -t[1] * scale],
        ),
        provenance=dict(
            source='User-supplied 18 illustrated hole maps and four parkland/lakeside photographs',
            geometry_review='judges_finished_art_v1',
            art_sha256=hashlib.sha256(raw).hexdigest(),
            reference_pixels=[w, h],
            registration='Finished-art contours and reviewed turf control points; middle pictured tee; uniform approximate yard scale along playing route.',
            straight_yards=round(math.dist(world(t), world(p)), 1),
            scorecard_yardage='User supplied; drawing widths and elevations are not surveyed.',
        ),
        strategy=guide.get(
            'strategy', 'Choose a landing area, then aim for the center of the green.'
        ),
        bunker_count=len(sand),
    )
    # Native image's full width defines scale; actual height is kept without stretching.
    c['bounds'][1] = (nh * w / nw - t[1]) * scale
    c['boundary'] = poly(dict(outer=[[0, 0], [w, 0], [w, nh * w / nw], [0, nh * w / nw]], holes=[]))
    l, r, n, f = c['bounds']
    c['viewbox'] = [n, l, f - n, r - l]
    c['hazard_test_points'] = {
        k: [world(interior(v, w, h)) for v in ps] for k, ps in [('sand', sand), ('water', water)]
    }
    try:
        validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
    except ValueError as error:
        raise ValueError(f'Hole {number}: {error}') from error
    assert classify(c['tee'], c) == 'tee', (number, 'tee')
    assert classify(c['pin'], c) == 'green', (number, 'pin')
    for kind, points in c['hazard_test_points'].items():
        for q in points:
            assert classify(q, c) == kind, (number, kind, q)
    return c


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path)
    args = parser.parse_args()
    guides = json.loads((ROOT / 'courses/judges-art-controls.json').read_text())
    package = dict(
        id=IDENTITY,
        version=1,
        name='Judges Course',
        tee_label='Provided yardages',
        par=sum(PARS),
        yards=sum(YARDS),
        description='Wooded parkland, stone-banked lakes, winding fairways and grass-island bunker complexes. Map scale is approximate.',
        holes=[register(i, guides[str(i)]) for i in range(1, 19)],
    )
    path = args.candidate or ROOT / 'courses' / f'{IDENTITY}.json'
    text = json.dumps(package, indent=2) + '\n'
    if not args.candidate and path.exists() and path.read_text() != text:
        raise ValueError('Publish a new immutable version instead of changing released geometry')
    path.write_text(text, encoding='utf-8')
    print(
        f'{path}: {package["yards"]} yd / par {package["par"]}; {sum(h["bunker_count"] for h in package["holes"])} sand regions'
    )


if __name__ == '__main__':
    main()
