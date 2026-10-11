"""Offline vector tracing of generated artwork; never modifies the raster assets.

Design-only dependencies: opencv-python-headless, numpy. Run after the guide builder
and image generation. Thresholds/contours require visual review before publication.
The shipped application reads only the resulting JSON and PNG files.
"""

import hashlib
import json
import math
import cv2
import numpy as np
from build_sheboygan_straits import ROOT, W, H, build
from course_geometry import classify
from course_workbench import validate_edits
from course_import import polygon


def clean(mask, size=5):
    return cv2.morphologyEx(
        mask.astype('uint8') * 255, cv2.MORPH_CLOSE, np.ones((size, size), 'uint8')
    )


def contours(mask, minimum=100, epsilon=1.7):
    found, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    for c in found:
        if cv2.contourArea(c) < minimum:
            continue
        for tolerance in (epsilon, 3, 4, 6, 8, 12, 18, 24):
            ring = cv2.approxPolyDP(c, tolerance, True).reshape(-1, 2).tolist()
            try:
                polygon([ring], lambda p: p)
            except ValueError:
                continue
            result.append(ring)
            break
        else:
            if cv2.contourArea(c) > 250:
                raise ValueError('Contour needs manual repair')
    return result


def interior(ring):
    mask = np.zeros((H, W), 'uint8')
    cv2.fillPoly(mask, [np.array(ring, dtype='int32')], 255)
    mask[:2, :] = 0
    mask[-2:, :] = 0
    mask[:, :2] = 0
    mask[:, -2:] = 0
    _, _, _, point = cv2.minMaxLoc(cv2.distanceTransform(mask, cv2.DIST_L2, 5))
    return list(point)


def register(index):
    c, guide = build(index)
    path = ROOT / 'web/art' / f"{c['id']}.png"
    raw = path.read_bytes()
    bgr = cv2.resize(cv2.imdecode(np.frombuffer(raw, dtype='uint8'), cv2.IMREAD_COLOR), (W, H))
    b, g, r = [a.astype(float) for a in cv2.split(bgr)]
    sand_mask = clean(
        (r > 155) & (g > 145) & (b > 110) & (r / g < 1.3) & (b / g > 0.70) & (b / g < 0.94), 7
    )
    # Bunker regions are constrained to the guide's dune/landing area, away from surf.
    roi = np.zeros((H, W), 'uint8')
    cv2.fillPoly(roi, [np.array(p, dtype='int32') for p in guide['sand']], 255)
    roi = cv2.dilate(roi, np.ones((91, 91), 'uint8'))
    water = contours(clean((b > r * 1.12) & (g > r * 1.10) & (b > 30), 15), 1500, 3)
    wet = np.zeros((H, W), 'uint8')
    if water:
        cv2.fillPoly(wet, [np.array(p, dtype='int32') for p in water], 255)
    wet = cv2.dilate(wet, np.ones((55, 55), 'uint8'))
    sand = contours(cv2.bitwise_and(cv2.bitwise_and(sand_mask, roi), cv2.bitwise_not(wet)), 250)

    def substantial(ring):
        mask = np.zeros((H, W), 'uint8')
        cv2.fillPoly(mask, [np.array(ring, dtype='int32')], 255)
        return cv2.distanceTransform(mask, cv2.DIST_L2, 5).max() >= 5

    sand = [p for p in sand if substantial(p)]
    # Visually reviewed bright shoreline rock/fescue fragments, not sand hazards.
    rejected = {
        3: [(453, 593)],
        9: [(671, 265), (1254, 282), (1455, 251)],
        10: [(692, 110)],
        18: [(936, 268)],
    }.get(index + 1, [])
    sand = [p for p in sand if all(math.dist(interior(p), q) > 22 for q in rejected)]
    grass = clean((g > r * 1.06) & (g > b * 1.35), 15)
    grass[:4, :] = 0
    grass[-4:, :] = 0
    grass[:, :4] = 0
    grass[:, -4:] = 0
    grass_rings = contours(grass, 1500, 3)
    grass_rings = [max(grass_rings, key=lambda p: cv2.contourArea(np.array(p, dtype='int32')))]

    # Bright putting/tee surfaces are isolated within their expected regions.
    def surface(center, radius):
        area = np.zeros((H, W), 'uint8')
        cv2.circle(area, tuple(map(int, center)), radius, 255, -1)
        if center[0] > 1000 and c['par'] != 3:
            area[:, :1320] = 0
        seed = np.zeros((H, W), 'uint8')
        cv2.circle(seed, tuple(map(int, center)), radius // 2, 255, -1)
        greenish = (g > r * 1.05) & (r / g > 0.70) & (b / g < 0.69)
        threshold = max(105, float(np.percentile(g[(seed > 0) & greenish], 90)) * 0.84)
        bright = clean(greenish & (g > threshold), 7)
        rings = contours(cv2.bitwise_and(bright, area), 80)
        if not rings:
            raise ValueError(f"Missing green/tee: {c['id']}")
        return min(rings, key=lambda p: math.dist(interior(p), center))

    old_scale = c['image']['transform'][0]
    old_ty = -c['image']['transform'][5] / old_scale
    green = surface([1390, c['pin'][0] / old_scale + old_ty], 140)
    tee = surface([110, old_ty], 65)
    tee_point = interior(tee)
    pin_point = interior(green)
    fairway = contours(clean((g > r * 1.27) & (g > b * 1.55), 13), 1500, 3)
    fairway = [max(fairway, key=lambda p: cv2.contourArea(np.array(p, dtype='int32')))]
    # Use a conservative route through the center of the mown corridor.
    route = [tee_point]
    if c['par'] != 3:
        field = clean((g > r * 1.27) & (g > b * 1.55), 13)
        dist = cv2.distanceTransform(field, cv2.DIST_L2, 5)
        for old in c['playing_line'][1:-1]:
            x = round(old[1] / old_scale + 110)
            y = round(old[0] / old_scale + old_ty)
            lo = max(0, y - 80)
            hi = min(H, y + 81)
            route.append([x, int(np.argmax(dist[lo:hi, x])) + lo])
    route.append(pin_point)
    scale = c['yards'] / sum(math.dist(a, b) for a, b in zip(route, route[1:]))
    tx, ty = tee_point

    def world(p):
        return [round((p[1] - ty) * scale, 6), round((p[0] - tx) * scale, 6)]

    def poly(ring, holes=()):
        return dict(outer=[world(p) for p in ring], holes=[[world(p) for p in h] for h in holes])

    edge = [[0, 0], [W, 0], [W, H], [0, H]]
    c['tee'] = world(tee_point)
    c['pin'] = world(pin_point)
    c['playing_line'] = [world(p) for p in route]
    c['boundary'] = poly(edge)
    c['surfaces'] = dict(
        sand=[poly(p) for p in sand],
        water=[poly(p) for p in water],
        green=[poly(green)],
        tee=[poly(tee)],
        fairway=[poly(p) for p in fairway],
        nature=[poly(edge, grass_rings)],
    )
    c['bounds'] = [-ty * scale, (H - ty) * scale, -tx * scale, (W - tx) * scale]
    l, r, n, f = c['bounds']
    c['viewbox'] = [n, l, f - n, r - l]
    c['image']['transform'] = [scale, 0, 0, scale, -tx * scale, -ty * scale]
    c['hazard_test_points'] = {
        k: [world(interior(p)) for p in rings] for k, rings in [('sand', sand), ('water', water)]
    }
    c['bunker_count'] = len(sand)
    c['provenance'].update(
        geometry_review='art_contours_v1',
        art_sha256=hashlib.sha256(raw).hexdigest(),
        straight_yards=round(math.dist(c['tee'], c['pin']), 1),
        registration='Vector contours traced from finished artwork; visually reviewed, simplified edges.',
    )
    validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
    assert classify(c['tee'], c) == 'tee', (index, 'tee')
    assert classify(c['pin'], c) == 'green', (index, 'green')
    for kind, points in c['hazard_test_points'].items():
        for point in points:
            assert classify(point, c) == kind, (index, kind, point)
    assert len(sand) >= 10, (index, len(sand))
    print(
        c['hole_number'],
        len(sand),
        'bunkers',
        len(water),
        'water',
        len(fairway),
        'fairway',
        flush=True,
    )
    return c


if __name__ == '__main__':
    path = ROOT / 'courses/sheboygan-straits-blue-v1.json'
    package = json.loads(path.read_text(encoding='utf-8'))
    package['holes'] = [register(i) for i in range(18)]
    path.write_text(json.dumps(package, indent=2) + '\n', encoding='utf-8')
