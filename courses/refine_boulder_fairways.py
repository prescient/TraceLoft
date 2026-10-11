"""Publish Boulder Beach v3 with reviewed, stripe-independent fairway edges.

Control points are traced on the original 1774x887 artwork. Only fairway polygons
on holes 6, 16 and 18 change; all yard registration, hazards and other surfaces
are copied from the immutable v2 package. No image processing dependencies.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from course_workbench import validate_edits

EDGES = {
    6: [(136,230),(215,250),(330,307),(535,328),(720,377),(855,410),
        (1110,405),(1290,412),(1380,370),(1450,326),(1510,282),
        (1570,270),(1635,269),(1680,286),(1690,319),(1670,350),
        (1600,370),(1500,402),(1400,465),(1320,490),(1160,550),
        (970,578),(890,584),(770,562),(720,540),(650,508),
        (500,452),(350,393),(230,351),(134,327)],
    16: [(168,494),(230,455),(380,428),(515,390),(650,348),(750,285),
         (800,245),(860,239),(940,252),(1100,283),(1290,301),(1450,326),
         (1550,331),(1580,340),(1630,334),(1680,359),(1695,399),
         (1675,439),(1615,456),(1510,435),(1380,403),(1220,395),
         (1080,400),(1030,405),(985,404),(946,393),(915,421),
         (845,444),(720,471),(520,514),(360,540),(235,564),(164,564)],
    18: [(147,275),(330,265),(480,254),(600,267),(690,305),(760,380),
         (810,410),(930,438),(1130,453),(1300,467),(1400,417),
         (1480,358),(1570,326),(1640,327),(1675,350),(1690,383),
         (1670,412),(1585,426),(1540,454),(1440,520),(1400,540),(1330,558),
         (1260,570),(1130,555),(1000,545),(855,528),(770,518),
         (710,491),(675,450),(620,428),(500,414),(330,391),(220,371),(138,358)],
}


def smooth_ring(points, steps=8):
    """Closed Catmull-Rom curve sampled densely enough for the scoring polygon."""
    result = []
    for i, p1 in enumerate(points):
        p0, p2, p3 = points[i-1], points[(i+1)%len(points)], points[(i+2)%len(points)]
        for step in range(steps):
            t = step/steps
            result.append([.5*(2*p1[j]+(-p0[j]+p2[j])*t+
                (2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+
                (-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t*t*t) for j in (0,1)])
    return result


def build():
    package = json.loads((ROOT/'courses/pebble-boulder-blue-v2.json').read_text(encoding='utf-8'))
    package = copy.deepcopy(package)
    package.update(id='pebble-boulder-blue-v3', version=3)
    for c in package['holes']:
        c['id'] = c['id'].replace('-v2','-v3')
        number = c['hole_number']
        if number not in EDGES:
            continue
        a,b,d,e,f,g = c['image']['transform']
        def world(p):
            x,y = p[0]*1536/1774, p[1]*768/887
            return [round(b*x+e*y+g,6),round(a*x+d*y+f,6)]  # noqa: B023 - called only in this iteration
        c['surfaces']['fairway'] = [dict(outer=[world(p) for p in smooth_ring(EDGES[number])],holes=[])]
        c['provenance'].update(geometry_review='fairway_edge_v3',
            fairway_registration='Reviewed native-art control points; smooth perimeter ignores mowing stripes and joins the putting apron.')
        validate_edits({k:c[k] for k in ('surfaces','boundary','tee','pin')})
    return package


if __name__ == '__main__':
    package = build()
    path = ROOT/'courses'/f"{package['id']}.json"
    text = json.dumps(package,indent=2)+'\n'
    if path.exists() and path.read_text(encoding='utf-8') != text:
        raise ValueError('Released version differs; publish a new version instead.')
    path.write_text(text,encoding='utf-8')
    print(path)
