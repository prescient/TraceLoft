"""Design-only, reviewed v2 course registration from the unmodified final artwork.

Needs OpenCV/NumPy outside the application environment. Run from any directory.
Thresholds are specific to these reviewed images; new artwork needs a fresh review.
Never overwrite a released package with different geometry; publish a new version.
The older v1 packages and raster images are read-only inputs.
"""

import sys, json, copy, math, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2, numpy as np
from register_sheboygan_art import contours, clean, interior
from course_geometry import classify
from course_workbench import validate_edits

W, H = 1536, 768


def maskring(mask):
    rings = contours(mask, 1500, 2)
    return max(rings, key=lambda p: cv2.contourArea(np.array(p, dtype="int32")))


def boulder(h):
    c = copy.deepcopy(h)
    im = cv2.resize(cv2.imread(str(ROOT / "web/art" / Path(c["image"]["href"]).name)), (W, H))
    sm = cv2.GaussianBlur(im, (7, 7), 0)
    b, g, r = [v.astype(float) + 0.001 for v in cv2.split(sm)]
    a, _, _, _, e, f = h["image"]["transform"]

    def px(v):
        return [(v[1] - e) / a, (v[0] - f) / a]

    route = [px(p) for p in h["playing_line"]]
    samples = np.array([sm[round(p[1]), round(p[0])] for p in route[1:-1]], float) + 0.001
    ratio = np.median(samples[:, 2] / samples[:, 1])
    brightness = np.median(samples[:, 1])
    blue = np.median(samples[:, 0] / samples[:, 1])
    field = clean((r / g < ratio + 0.025) & (g > brightness * 0.76) & (b / g < blue + 0.07), 15)
    field = cv2.morphologyEx(field, cv2.MORPH_OPEN, np.ones((7, 7), 'uint8'))
    fairway = maskring(field)
    clearing = maskring(clean((g > r * 1.10) & (g > b * 1.65) & (g > 90), 17))

    def surface(center, radius, tee=False):
        roi = np.zeros((H, W), 'uint8')
        cv2.circle(roi, tuple(map(round, center)), radius, 255, -1)
        greenish = (g > r * 1.05) & (r / g > 0.80) & (b / g < 0.70)
        if tee:
            greenish &= (b / g > (0.35 if h['hole_number'] == 5 else 0.40)) & (r / g > 0.82)
        threshold = max(110, float(np.percentile(g[(roi > 0) & greenish], 90)) * 0.88)
        mask = cv2.bitwise_and(clean(greenish & (g > threshold), 7), roi)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((11, 11), 'uint8'))
        rr = contours(mask, 100, 1.5)
        if not rr:
            raise ValueError(('surface', h['hole_number'], tee))
        return max(rr, key=lambda p: cv2.contourArea(np.array(p, 'int32')))

    tee = surface(route[0], 65, True)
    green = surface(route[-1], 140)
    sand = []
    for old in h['surfaces']['sand']:
        center = np.array([px(p) for p in old['outer']]).mean(axis=0)
        roi = np.zeros((H, W), 'uint8')
        cv2.circle(roi, tuple(map(round, center)), 85, 255, -1)
        rr = contours(
            cv2.bitwise_and(
                clean(
                    (r > 140)
                    & (g > 130)
                    & (b > 85)
                    & (r / g < 1.24)
                    & (b / g > 0.60)
                    & (b / g < 0.98)
                    & (r >= g * 0.97),
                    3,
                ),
                roi,
            ),
            200,
            1.5,
        )
        if not rr:
            raise ValueError(('sand', h['hole_number'], center))
        sand.append(max(rr, key=lambda p: cv2.contourArea(np.array(p, 'int32'))))
    water_mask = clean((b > r * 1.12) & (g > r * 1.10) & (b > 30), 7)
    wet = contours(water_mask, 1500, 2)
    ocean = max(wet, key=lambda p: cv2.contourArea(np.array(p, 'int32')))
    water = [ocean]
    for old in h['surfaces']['water'][1:]:
        center = np.array([px(v) for v in old['outer']]).mean(axis=0)
        roi = np.zeros((H, W), 'uint8')
        cv2.circle(roi, tuple(map(round, center)), 100, 255, -1)
        ponds = contours(cv2.bitwise_and(water_mask, roi), 700, 2)
        pond = min(ponds, key=lambda p: math.dist(interior(p), center))
        water.append(pond)
        # Remove the pond and any narrow color-mask connection from the ocean mask.
        cv2.fillPoly(water_mask, [np.array(pond, 'int32')], 0)
        water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, np.ones((13, 13), 'uint8'))
        water[0] = max(
            contours(water_mask, 1500, 2), key=lambda p: cv2.contourArea(np.array(p, 'int32'))
        )
    # Putting and tee shapes override mowing; include them in the enclosing grass fields.
    for ring in (tee, green):
        cv2.fillPoly(field, [np.array(ring, 'int32')], 255)
    fairway = maskring(field)
    t = interior(tee)
    p = interior(green)
    line = [t]
    dist = cv2.distanceTransform(field, cv2.DIST_L2, 5)
    for old in route[1:-1]:
        x = round(old[0])
        lo = max(0, round(old[1]) - 80)
        hi = min(H, round(old[1]) + 81)
        line.append([x, int(np.argmax(dist[lo:hi, x])) + lo])
    line.append(p)
    scale = h['yards'] / sum(math.dist(a, b) for a, b in zip(line, line[1:]))
    tx, ty = t

    def world(v):
        return [round((v[1] - ty) * scale, 6), round((v[0] - tx) * scale, 6)]

    def poly(ring, holes=()):
        return dict(
            outer=[world(v) for v in ring], holes=[[world(v) for v in cut] for cut in holes]
        )

    edge = [[0, 0], [W, 0], [W, H], [0, H]]
    c.update(
        id=c['id'].replace('-v1', '-v2'),
        tee=world(t),
        pin=world(p),
        playing_line=[world(v) for v in line],
        bounds=[-ty * scale, (H - ty) * scale, -tx * scale, (W - tx) * scale],
        boundary=poly(edge),
        surfaces=dict(
            fairway=[poly(fairway)],
            green=[poly(green)],
            tee=[poly(tee)],
            sand=[poly(v) for v in sand],
            water=[poly(v) for v in water],
            nature=[poly(edge, [clearing])],
        ),
    )
    l, r, n, f = c['bounds']
    c['viewbox'] = [n, l, f - n, r - l]
    c['image']['transform'] = [scale, 0, 0, scale, -tx * scale, -ty * scale]
    c['bunker_count'] = len(sand)
    c['hazard_test_points'] = {
        k: [world(interior(v)) for v in rings] for k, rings in [('sand', sand), ('water', water)]
    }
    c['provenance'].update(
        geometry_review='finished_art_v2',
        art_sha256=hashlib.sha256(
            (ROOT / 'web/art' / Path(c['image']['href']).name).read_bytes()
        ).hexdigest(),
        straight_yards=round(math.dist(c['tee'], c['pin']), 1),
        registration='Reviewed finished-art contours in 1536x768 reference pixels; uniform route yard scale.',
    )
    validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
    for v in c['playing_line']:
        assert classify(v, c) in ('tee', 'green', 'fairway', 'rough'), (
            h['hole_number'],
            v,
            classify(v, c),
        )
    assert classify(c['tee'], c) == 'tee'
    assert classify(c['pin'], c) == 'green'
    return c


def straits(h):
    c = copy.deepcopy(h)
    im = cv2.resize(cv2.imread(str(ROOT / 'web/art' / Path(c['image']['href']).name)), (W, H))
    sm = cv2.GaussianBlur(im, (7, 7), 0)
    b, g, r = [v.astype(float) + 0.001 for v in cv2.split(sm)]
    a, _, _, _, e, f = c['image']['transform']

    def px(v):
        return [(v[1] - e) / a, (v[0] - f) / a]

    def world(v):
        return [round(v[1] * a + f, 6), round(v[0] * a + e, 6)]

    field = clean((g > r * 1.18) & (g > b * 1.45), 17)
    field = cv2.morphologyEx(field, cv2.MORPH_OPEN, np.ones((9, 9), 'uint8'))
    if h['hole_number'] == 10:
        center = px(h['pin'])
        roi = np.zeros((H, W), 'uint8')
        cv2.circle(roi, tuple(map(round, center)), 140, 255, -1)
        greenish = (g > r * 1.05) & (r / g > 0.72) & (b / g < 0.70)
        threshold = max(90, float(np.percentile(g[(roi > 0) & greenish], 90)) * 0.83)
        mask = cv2.bitwise_and(clean(greenish & (g > threshold), 9), roi)
        ring = max(contours(mask, 500, 1.5), key=lambda p: cv2.contourArea(np.array(p, 'int32')))
        c['surfaces']['green'] = [dict(outer=[world(v) for v in ring], holes=[])]
    for kind in ('tee', 'green'):
        for poly in c['surfaces'][kind]:
            cv2.fillPoly(field, [np.array([px(v) for v in poly['outer']], 'int32')], 255)
    ring = maskring(field)
    c['surfaces']['fairway'] = [dict(outer=[world(v) for v in ring], holes=[])]
    c['id'] = c['id'].replace('-v1', '-v2')
    c['provenance'].update(
        geometry_review='finished_art_v2',
        registration='Re-reviewed finished artwork; refined mown fairway edges and hole 10 putting surface. Original sand/water tracing retained.',
    )
    validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
    assert classify(c['tee'], c) == 'tee'
    assert classify(c['pin'], c) == 'green'
    return c


def publish(package):
    path = ROOT / 'courses' / f"{package['id']}.json"
    text = json.dumps(package, indent=2) + '\n'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise ValueError(
            'Existing course version differs. Review and publish a new version instead.'
        )
    path.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    package = json.loads((ROOT / 'courses/pebble-boulder-blue-v1.json').read_text())
    package['holes'] = [boulder(h) for h in package['holes']]
    package.update(id='pebble-boulder-blue-v2', version=2)
    publish(package)
    print('Built', len(package['holes']))
    package = json.loads((ROOT / 'courses/sheboygan-straits-blue-v1.json').read_text())
    package['holes'] = [straits(h) for h in package['holes']]
    package.update(id='sheboygan-straits-blue-v2', version=2)
    publish(package)
