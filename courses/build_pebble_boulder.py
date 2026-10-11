"""Build original coastal geometry and optional schematic guides (Pillow for guides only).

No downloaded imagery. Yardages/pars follow the official January 2026 Blue scorecard.
Run with --guides to draw geometry references for the image generation workflow.
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from course_geometry import classify
from course_workbench import validate_edits

YARDS = [378, 509, 397, 333, 189, 498, 107, 416, 483, 444, 370, 202, 401, 559, 392, 400, 182, 541]
PARS = [4, 5, 4, 4, 3, 5, 3, 4, 4, 4, 4, 3, 4, 5, 4, 4, 3, 5]
NAMES = [
    'Cypress Welcome',
    'Driftwood Reach',
    'Otter Bend',
    'Sandpiper Run',
    'Tidepool',
    'Headland Rise',
    'Boulder Point',
    'Saltwater Crossing',
    'Pacific Edge',
    'Gull Rock',
    'Cypress Hollow',
    'Foam Cove',
    'Heather Turn',
    'Longshore',
    'Dune Lantern',
    'Seal Passage',
    'Breakwater',
    'Last Light',
]
# Lateral centerline positions along a left-to-right original playing route.
LINES = [
    [270, 250, 225, 245, 270],
    [310, 320, 210, 180, 200],
    [190, 220, 340, 310, 260],
    [320, 270, 210, 220, 190],
    [290, 275, 250, 240, 230],
    [180, 240, 315, 285, 200],
    [250, 250, 250, 250, 250],
    [190, 210, 300, 295, 240],
    [250, 180, 170, 245, 290],
    [295, 290, 220, 175, 170],
    [290, 230, 160, 170, 220],
    [190, 210, 250, 300, 300],
    [160, 190, 260, 310, 270],
    [270, 310, 250, 170, 180],
    [210, 260, 300, 275, 210],
    [310, 275, 200, 200, 230],
    [265, 240, 215, 205, 220],
    [190, 200, 285, 300, 220],
]
W, H = 1536, 768


def oval(cx, cy, rx, ry, phase=0, n=36):
    return [
        [
            cx + rx * (1 + 0.10 * math.sin(3 * t + phase)) * math.cos(t),
            cy + ry * (1 + 0.08 * math.sin(2 * t + phase)) * math.sin(t),
        ]
        for t in [i * math.tau / n for i in range(n)]
    ]


def build(index):
    number = index + 1
    yard = YARDS[index]
    par = PARS[index]
    # Work in a 1024 x 512 design plane, then scale raster coordinates by 1.5.
    xs = [80, 285, 510, 735, 940]
    ys = LINES[index]
    route = [[x * 1.5, y * 1.5] for x, y in zip(xs, ys)]
    scale = yard / sum(math.dist(a, b) for a, b in zip(route, route[1:]))
    tx, ty = route[0]

    def world(p):
        return [round((p[1] - ty) * scale, 6), round((p[0] - tx) * scale, 6)]

    def poly(r, holes=()):
        return dict(outer=[world(p) for p in r], holes=[[world(p) for p in h] for h in holes])

    # Dense smoothly blended ribbon; physical width varies along the hole.
    center = []
    for j in range(4):
        for k in range(18):
            t = k / 18
            s = t * t * (3 - 2 * t)
            x = (xs[j] + (xs[j + 1] - xs[j]) * t) * 1.5
            y = (ys[j] + (ys[j + 1] - ys[j]) * s) * 1.5
            width = (19 + 6 * math.sin((j + t) * 2.1 + index * 0.7)) / scale
            if par == 3:
                width *= 0.62
            center.append((x, y, width))
    center.append((1410, ys[-1] * 1.5, 18 / scale))
    fairway = [[x, y - w] for x, y, w in center] + [[x, y + w] for x, y, w in reversed(center)]
    # Green radius stays in playable yards; cap screen extent for short holes.
    gr = min(13 / scale, 105)
    green = oval(1410, ys[-1] * 1.5, gr * 1.2, gr, index * 0.4)
    tee = oval(120, ys[0] * 1.5, min(6 / scale, 55), min(4 / scale, 36), index * 0.2)
    sand = []
    for j, (x, y, r) in enumerate(
        [
            (1370, ys[-1] * 1.5 - gr - 25, 22),
            (1435, ys[-1] * 1.5 + gr + 24, 25),
            (route[2][0] + 65, route[2][1] + (70 if index % 2 else -75), 30),
        ]
    ):
        if par == 3 and j == 2:
            continue
        sand.append(oval(x, y, r * (1 + 0.15 * (index % 3)), r * 0.60, index + j))
    # Coast occupies a deliberately varied outer margin, away from safe centerline.
    coast = []
    bottom = index % 3 != 1
    for k in range(33):
        x = W * k / 32
        y = (
            (630 + 35 * math.sin(k * 0.55 + index * 0.6) + 12 * math.sin(k * 1.7))
            if bottom
            else (90 + 30 * math.sin(k * 0.5 + index * 0.4))
        )
        coast.append([x, y])
    ocean = coast + ([[W, H], [0, H]] if bottom else [[W, 0], [0, 0]])
    water = [ocean]
    if index in (2, 7, 10, 15):
        x = route[1][0] + 65
        y = route[1][1] + (122 if bottom else -122)
        water.append(oval(x, y, 62, 35, index))
    edge = [[0, 0], [W, 0], [W, H], [0, H]]
    # A generous rough corridor around playable grass; woods/scrub outside it.
    clearing = [[x, max(110, y - w - 58)] for x, y, w in center] + [
        [x, min(645, y + w + 58)] for x, y, w in reversed(center)
    ]
    # Extend corridor caps to contain tee and green surroundings.
    clearing[0][0] = 35
    clearing[-1][0] = 35
    clearing[len(center) - 1][0] = 1510
    clearing[len(center)][0] = 1510
    surfaces = {
        'fairway': [poly(fairway)],
        'green': [poly(green)],
        'tee': [poly(tee)],
        'sand': [poly(r) for r in sand],
        'water': [poly(r) for r in water],
        'nature': [poly(edge, [clearing])],
    }
    identity = f'pebble-boulder-{number:02d}-v1'
    c = dict(
        id=identity,
        name=NAMES[index],
        hole_number=number,
        par=par,
        yards=yard,
        tee_label='Blue',
        description=(
            'An original coastal '
            + ('par three' if par == 3 else 'par five' if par == 5 else 'par four')
            + ' with rugged shoreline, dune rough and sculpted sand.'
        ),
        tee=world(route[0]),
        pin=world(route[-1]),
        playing_line=[world(p) for p in route],
        bounds=[-ty * scale, (H - ty) * scale, -tx * scale, (W - tx) * scale],
        boundary=poly(edge),
        surfaces=surfaces,
        image=dict(
            href=f'/assets/art/{identity}.png',
            width=W,
            height=H,
            transform=[scale, 0, 0, scale, -tx * scale, -ty * scale],
        ),
        provenance=dict(
            kind='original_generated',
            created='2026-10-03',
            geometry_review='designed_coastal_v1',
            route_yards=yard,
            straight_yards=round(math.dist(route[0], route[-1]) * scale, 1),
            attribution='Boulder Beach · original coastal design · AI artwork',
            yardage_source='https://www.pebblebeach.com/content/uploads/PebbleBeach-Scorecard.pdf',
            scorecard_edition='January 2026 Blue tees',
        ),
        warnings=[
            'Original coastal layout; Blue yardages inspired by the January 2026 Pebble Beach scorecard.',
            'Listed yardage follows the playing route; map distances are straight line.',
            'Flat greens; water/OB replay with +1 penalty. No elevation or tree collision.',
        ],
    )
    l, r, n, f = c['bounds']
    c['viewbox'] = [n, l, f - n, r - l]
    validate_edits({k: c[k] for k in ('surfaces', 'boundary', 'tee', 'pin')})
    assert classify(c['tee'], c) == 'tee', (number, 'tee')
    assert classify(c['pin'], c) == 'green', (number, 'pin')
    return c, dict(
        edge=edge, clearing=clearing, fairway=fairway, green=green, tee=tee, sand=sand, water=water
    )


def guides(c, p):
    from PIL import Image, ImageDraw

    im = Image.new('RGB', (W, H), '#244936')
    d = ImageDraw.Draw(im)

    def draw(r, fill):
        d.polygon([tuple(v) for v in r], fill=fill)

    draw(p['clearing'], '#678151')
    draw(p['fairway'], '#82a455')
    draw(p['green'], '#afd27b')
    draw(p['tee'], '#afd27b')
    for r in p['sand']:
        draw(r, '#efdbac')
    for r in p['water']:
        draw(r, '#126284')
    folder = ROOT / 'designs/pebble-boulder'
    folder.mkdir(exist_ok=True)
    im.save(folder / f"{c['id']}-guide.png")


if __name__ == '__main__':
    holes = []
    for i in range(18):
        c, p = build(i)
        holes.append(c)
        if '--guides' in sys.argv:
            guides(c, p)
    package = dict(
        id='pebble-boulder-blue-v1',
        name='Boulder Beach',
        tee_label='Blue',
        par=sum(PARS),
        yards=sum(YARDS),
        description='Eighteen original coastal holes. Rugged shores, cypress groves and dune-lined approaches.',
        holes=holes,
        version=1,
    )
    (ROOT / 'courses/pebble-boulder-blue-v1.json').write_text(
        json.dumps(package, indent=2) + '\n', encoding='utf-8'
    )
    print('Built', len(holes), 'holes;', sum(YARDS), 'yards; par', sum(PARS))
