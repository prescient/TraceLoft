"""Design-only contact sheets and fixed pixel probes for finished course artwork.

Requires Pillow/OpenCV/NumPy; never edits course packages or original image assets.
Run after registration, then visually review the sheets and probes before release.
"""
import argparse
import hashlib
from html import escape
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from course_geometry import classify
from bundled_courses import COURSE_IDS

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


def overlay(c, native=False):
    im = Image.open(ROOT/'web/art'/Path(c['image']['href']).name).convert('RGB')
    if not native:
        im = im.resize((1536,768))
    sx, sy = im.width/1536, im.height/768
    d = ImageDraw.Draw(im)
    def points(ring):
        return [(p[0]*sx,p[1]*sy) for p in (pixel(c,v) for v in ring)]
    for kind in ('nature','fairway','green','tee','sand','water'):
        for p in c['surfaces'][kind]:
            for ring in [p['outer'],*p.get('holes',[])]:
                line = points(ring)
                d.line(line+[line[0]], fill=COLORS[kind], width=max(2,round(2*sx)))
    if native:
        line = points(c['boundary']['outer'])
        d.line(line+[line[0]], fill='#ff74b4', width=3)
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
        if c['provenance'].get('geometry_review') == 'fairway_edge_v3':
            native = {6:[(1510,345),(1550,310),(1580,285),(1600,365)],
                      16:[(1390,350),(830,244),(400,442)],
                      18:[(1050,528),(1410,529),(1580,420)]}
            for x,y in native[c['hole_number']]:
                result.append(dict(pixel=[round(x*1536/1774),round(y*768/887)],lie='fairway'))
    elif c['hole_number']==10:
        result.extend([dict(pixel=[1367,388],lie='green'),dict(pixel=[1400,410],lie='green')])
    return result


def export_gallery(output, entries, files):
    nav, sections = [], []
    for package, holes in entries:
        identity = package['id']
        title = escape(package['name'])
        nav.append(f'<a href="#{identity}">{title}</a>')
        jumps = ' '.join(f'<a href="#{c["id"]}">{c["hole_number"]}</a>' for c in holes)
        sections.append(f'<section id="{identity}"><h2>{title}</h2><nav aria-label="{title} holes">{jumps}</nav>')
        for c in holes:
            filename = f'{identity}-hole-{c["hole_number"]:02d}.jpg'
            label = escape(f'{package["name"]} · Hole {c["hole_number"]} · {c["name"]} · Par {c["par"]} · {c["yards"]} yd')
            sections.append(f'<article id="{c["id"]}"><h3>{label}</h3><a href="{filename}"><img loading="lazy" src="{filename}" alt="{label} with scoring boundaries"></a><p><a href="{filename}">Open full-size image</a> · <a href="#{identity}">Back to hole list</a></p></article>')
        sections.append('</section>')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TraceLoft course boundary review</title><style>
body{margin:0 auto;padding:24px;max-width:1774px;font:16px/1.5 system-ui;color:#102238;background:#fff}
h1{font-size:28px}a{color:#1851df}nav{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}
nav a{padding:8px 14px;border:1px solid #cbd2dc}img{width:100%;height:auto;display:block}
article{margin:40px 0}h3{font-size:20px}section{margin-top:48px}.legend{display:flex;gap:16px;flex-wrap:wrap}
.swatch{display:inline-block;width:16px;height:4px;vertical-align:middle;margin-right:6px;background:var(--color)}
</style><h1>TraceLoft · Course boundary review</h1>
<p>All 36 current holes. Click a hole image to inspect it at its original artwork resolution.
These are the scoring polygons used by new rounds; saved older rounds retain their layouts.</p>
<div class="legend">'''
    for label, color in [('Sand','#ff00ff'),('Water','#00ffff'),('Green / tee','#ffff00'),
                         ('Fairway','#ffffff'),('Nature','#ad88ff'),('Map OB limit','#ff74b4')]:
        html += f'<span><i class="swatch" style="--color:{color};outline:1px solid #777"></i>{label}</span>'
    html += '</div><p>Soft turf and shoreline transitions are simplified. The pink map perimeter is a game limit.</p><nav>' + ''.join(nav) + '</nav>' + ''.join(sections) + '</html>'
    index = output/'index.html'
    index.write_text(html,encoding='utf-8')
    files.append(index)
    bundle = output/'course-boundary-review.zip'
    with ZipFile(bundle,'w',compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path,path.relative_to(output))
    print(f'Gallery: {index}\nBundle: {bundle}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUTPUT,help='Review artifact directory')
    parser.add_argument('--individual',action='store_true',help='Also export native-resolution holes, an offline gallery and ZIP')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    files, entries = [], []
    report = dict(reference_pixels=[1536,768],review_date='2026-10-03',courses=[])
    for identity in COURSE_IDS:
        package = json.loads((ROOT/'courses'/f'{identity}.json').read_text(encoding='utf-8'))
        entries.append((package,package['holes']))
        version=package['version']
        legacy_id=identity.rsplit('-v',1)[0]+f'-v{version-1}'
        legacy=ROOT/'courses'/legacy_id
        legacy=legacy.with_suffix('.json')
        record = dict(id=identity,version=version,legacy_id=legacy_id,legacy_sha256=hashlib.sha256(legacy.read_bytes()).hexdigest(),holes=[])
        for offset in range(0,18,6):
            sheet = Image.new('RGB',(1800,660),'#111827')
            d = ImageDraw.Draw(sheet)
            for k,c in enumerate(package['holes'][offset:offset+6]):
                im = overlay(c)
                if args.individual:
                    path = output/f'{identity}-hole-{c["hole_number"]:02d}.jpg'
                    overlay(c,native=True).save(path,quality=95,subsampling=0)
                    files.append(path)
                x=(k%3)*600; y=(k//3)*330
                sheet.paste(im.resize((600,300)),(x,y))
                d.text((x+8,y+307),f"{package['name']} {c['hole_number']} / v{version}",fill='white')
                raw=(ROOT/'web/art'/Path(c['image']['href']).name).read_bytes()
                record['holes'].append(dict(id=c['id'],number=c['hole_number'],art_sha256=hashlib.sha256(raw).hexdigest(),
                    geometry_sha256=geometry_hash(c),probes=probes(c)))
                if (identity.startswith('pebble') and c['hole_number']==1) or (identity.startswith('sheboygan') and c['hole_number']==10):
                    px,py=pixel(c,c['pin'])
                    path = output/f'{identity}-green.png'
                    im.crop((px-150,py-150,px+150,py+150)).save(path)
                    files.append(path)
            path = output/f'{identity}-{offset+1:02d}.jpg'
            sheet.save(path,quality=95)
            files.append(path)
        report['courses'].append(record)
    manifest = output/'review.json'
    manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    files.append(manifest)
    if args.individual:
        export_gallery(output,entries,files)


if __name__=='__main__':
    main()
