"""Design-only contact sheets and fixed pixel probes for finished course artwork.

Requires Pillow/OpenCV/NumPy; never edits course packages or original image assets.
Run after registration, then visually review the sheets and probes before release.
"""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from course_geometry import classify

OUTPUT = ROOT / 'designs/course-registration'
COLORS = dict(water='#00ffff', sand='#ff00ff', green='#ffff00', tee='#ffff00',
              fairway='#ffffff', nature='#ad88ff')


def pixel(c, p):
    a, _, _, d, e, f = c['image']['transform']
    return [(p[1]-e)/a, (p[0]-f)/d]


def world(c, p):
    a, b, d, e, f, g = c['image']['transform']
    return [b*p[0]+e*p[1]+g, a*p[0]+d*p[1]+f]


def geometry_hash(c):
    fields = {k:c[k] for k in ('surfaces','boundary','bounds','tee','pin','playing_line','image')}
    return hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()


def overlay(c):
    im = Image.open(ROOT/'web/art'/Path(c['image']['href']).name).convert('RGB').resize((1536,768))
    d = ImageDraw.Draw(im)
    for kind in ('nature','fairway','green','tee','sand','water'):
        for p in c['surfaces'][kind]:
            for ring in [p['outer'],*p.get('holes',[])]:
                points = [tuple(pixel(c,v)) for v in ring]
                d.line(points+[points[0]], fill=COLORS[kind], width=2)
    return im


def probes(c):
    # Centers of the visible surfaces are saved as fixed asset-pixel fixtures after review.
    result = []
    for kind in ('water','sand','green','tee','fairway','nature'):
        mask = np.zeros((768,1536),'uint8')
        for p in c['surfaces'][kind]:
            single = np.zeros_like(mask)
            cv2.fillPoly(single,[np.array([pixel(c,v) for v in p['outer']], 'int32')],255)
            for cut in p.get('holes',[]):
                cv2.fillPoly(single,[np.array([pixel(c,v) for v in cut], 'int32')],0)
            mask = cv2.bitwise_or(mask,single)
        # Hazard test points already represent each independently reviewed visible hazard.
        points = [pixel(c,p) for p in c.get('hazard_test_points',{}).get(kind,[])]
        if not points and mask.any():
            _,_,_,point = cv2.minMaxLoc(cv2.distanceTransform(mask,cv2.DIST_L2,5))
            points = [list(point)]
        for p in points:
            p = [round(v) for v in p]
            if classify(world(c,p),c) == kind:
                result.append(dict(pixel=p,lie=kind))
    # Trees/shadow patches that the first automatic blue mask falsely identified as water.
    if c['id'].startswith('pebble-boulder'):
        extra = {3:[(1100,75)],4:[(345,200)],7:[(650,90)],9:[(1300,160)],
                 12:[(500,100)],14:[(1110,645)],17:[(560,700)],18:[(1100,150)]}
        for p in extra.get(c['hole_number'],[]):
            assert classify(world(c,p),c) == 'nature'
            result.append(dict(pixel=list(p),lie='nature'))
        if c['hole_number']==1:
            result.extend([dict(pixel=[1410,375],lie='green'),dict(pixel=[1375,306],lie='sand'),
                           dict(pixel=[1437,445],lie='sand'),dict(pixel=[1340,375],lie='fairway')])
    elif c['hole_number']==10:
        result.extend([dict(pixel=[1367,388],lie='green'),dict(pixel=[1400,410],lie='green')])
    return result


def main():
    OUTPUT.mkdir(exist_ok=True)
    report = dict(reference_pixels=[1536,768],review_date='2026-10-03',courses=[])
    for identity in ('pebble-boulder-blue-v2','sheboygan-straits-blue-v2'):
        package = json.loads((ROOT/'courses'/f'{identity}.json').read_text(encoding='utf-8'))
        legacy=ROOT/'courses'/identity.replace('-v2','-v1')
        legacy=legacy.with_suffix('.json')
        record = dict(id=identity,legacy_sha256=hashlib.sha256(legacy.read_bytes()).hexdigest(),holes=[])
        for offset in range(0,18,6):
            sheet = Image.new('RGB',(1800,660),'#111827')
            d = ImageDraw.Draw(sheet)
            for k,c in enumerate(package['holes'][offset:offset+6]):
                im = overlay(c)
                x=(k%3)*600; y=(k//3)*330
                sheet.paste(im.resize((600,300)),(x,y))
                d.text((x+8,y+307),f"{package['name']} {c['hole_number']} / v2",fill='white')
                raw=(ROOT/'web/art'/Path(c['image']['href']).name).read_bytes()
                record['holes'].append(dict(id=c['id'],number=c['hole_number'],art_sha256=hashlib.sha256(raw).hexdigest(),
                    geometry_sha256=geometry_hash(c),probes=probes(c)))
                if (identity.startswith('pebble') and c['hole_number']==1) or (identity.startswith('sheboygan') and c['hole_number']==10):
                    px,py=pixel(c,c['pin'])
                    im.crop((px-150,py-150,px+150,py+150)).save(OUTPUT/f'{identity}-green.png')
            sheet.save(OUTPUT/f'{identity}-{offset+1:02d}.jpg',quality=95)
        report['courses'].append(record)
    (OUTPUT/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
