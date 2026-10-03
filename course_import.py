"""Assisted, one-hole OSM/GeoJSON import. Geometry is reviewed before immutable publication."""
import copy
import hashlib
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from course_geometry import in_polygon, in_ring
from putting import timestamp

PREFIX='course_import.v1.'
LIMIT=2_000_000
SURFACES={'fairway':'fairway','green':'green','tee':'tee','bunker':'sand','water_hazard':'water',
          'lateral_water_hazard':'water','water':'water','wood':'nature','scrub':'nature'}


def source_size(data):
    if not isinstance(data,dict): raise ValueError('Use an Overpass JSON or GeoJSON FeatureCollection object.')
    try: raw=json.dumps(data,allow_nan=False)
    except (ValueError,TypeError): raise ValueError('Source coordinates must be finite JSON values.')
    if len(raw.encode())>LIMIT: raise ValueError('Import one course at a time (maximum 2 MB).')


def point(p):
    if (not isinstance(p,(list,tuple)) or len(p)<2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p[:2])
        or not -180<=p[0]<=180 or not -85<=p[1]<=85):
        raise ValueError('Use WGS84 longitude/latitude coordinates within ±85° latitude.')
    return list(p[:2])


def ring(raw, coordinate=point):
    if not isinstance(raw,list):raise ValueError('Polygon coordinates must be an array.')
    points=[coordinate(p) for p in raw]
    if len(points)>1 and points[0]==points[-1]:points.pop()
    if not 3<=len(points)<=600 or len({tuple(p) for p in points})!=len(points):
        raise ValueError('Polygon rings need 3–600 distinct vertices; simplify or repair the source.')
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
    if abs(area)<1e-12:raise ValueError('A polygon has no usable area.')
    # Reject crossings/touches between nonadjacent edges; do not guess how to repair a ring.
    edges=list(zip(points,points[1:]+points[:1]))
    for i,(a,b) in enumerate(edges):
        for j in range(i+2,len(edges)):
            if i==0 and j==len(edges)-1:continue
            if intersects(a,b,*edges[j]):raise ValueError('A polygon crosses or touches itself. Repair it before importing.')
    return points


def intersects(a,b,c,d):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if max(a[0],b[0])<min(c[0],d[0]) or max(c[0],d[0])<min(a[0],b[0]) or max(a[1],b[1])<min(c[1],d[1]) or max(c[1],d[1])<min(a[1],b[1]):return False
    return cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0


def polygon(rings, coordinate=point):
    if not isinstance(rings,list) or not 1<=len(rings)<=30:raise ValueError('Invalid polygon ring collection.')
    outer=ring(rings[0],coordinate);holes=[ring(r,coordinate) for r in rings[1:]]
    for i,h in enumerate(holes):
        if not all(in_ring(p,outer) for p in h):raise ValueError('An interior ring is outside its polygon.')
        for other in [outer]+holes[:i]:
            if any(intersects(a,b,c,d) for a,b in zip(h,h[1:]+h[:1]) for c,d in zip(other,other[1:]+other[:1])):
                raise ValueError('Polygon rings intersect; repair the source.')
            if other is not outer and (in_ring(h[0],other) or in_ring(other[0],h)):
                raise ValueError('Interior rings overlap.')
    return dict(outer=outer,holes=holes)


def features(data):
    source_size(data); warnings=[];out=[]
    if data.get('type')=='FeatureCollection':
        if data.get('crs'):raise ValueError('Export standard WGS84 GeoJSON without a custom CRS.')
        raw=data.get('features',[])
        if not isinstance(raw,list) or len(raw)>2000:raise ValueError('Use at most 2,000 source features.')
        for i,f in enumerate(raw):
            if not isinstance(f,dict):raise ValueError('Invalid GeoJSON feature.')
            props=f.get('properties') or {};g=f.get('geometry') or {}
            if not isinstance(props,dict) or not isinstance(g,dict):raise ValueError('Invalid feature properties/geometry.')
            out.append(dict(id=str(f.get('id',i)),tags=props,kind=g.get('type'),coordinates=g.get('coordinates',[])))
    elif isinstance(data.get('elements'),list):
        if len(data['elements'])>2000:raise ValueError('Use at most 2,000 OSM elements.')
        for e in data['elements']:
            if not isinstance(e,dict):raise ValueError('Invalid OSM element.')
            tags=e.get('tags',{});g=e.get('geometry',[])
            if not isinstance(tags,dict) or not isinstance(g,list):raise ValueError('Invalid OSM tags or geometry.')
            if e.get('type')=='relation':
                warnings.append(f"Relation {e.get('id')}: export as GeoJSON to include its multipolygon geometry.")
                continue
            if not g:continue
            if any(not isinstance(p,dict) or 'lon' not in p or 'lat' not in p for p in g):raise ValueError('OSM geometry needs longitude and latitude.')
            coords=[[p['lon'],p['lat']] for p in g]
            closed=len(coords)>3 and coords[0]==coords[-1]
            out.append(dict(id=f"way/{e.get('id','unknown')}",tags=tags,kind='Polygon' if closed else 'LineString',coordinates=[coords] if closed else coords))
    else:raise ValueError('Use Overpass JSON with geometry, or GeoJSON FeatureCollection.')
    parsed=[]
    for f in out:
        tags=f['tags'];tag=tags.get('golf') or tags.get('natural') or tags.get('surface')
        if not isinstance(tag,str):continue
        if not isinstance(f['coordinates'],list):raise ValueError('Feature coordinates must be an array.')
        if tag=='hole' and f['kind']=='LineString':
            line=[point(p) for p in f['coordinates']]
            if not 2<=len(line)<=100:raise ValueError('Hole paths need 2–100 points.')
            parsed.append(dict(id=f['id'],kind='hole',tags=tags,line=line))
        elif tag in SURFACES and f['kind'] in ('Polygon','MultiPolygon'):
            sets=[f['coordinates']] if f['kind']=='Polygon' else f['coordinates']
            for coords in sets:parsed.append(dict(id=f['id'],kind=SURFACES[tag],polygon=polygon(coords),tags=tags))
    holes=[f for f in parsed if f['kind']=='hole']
    if not holes:raise ValueError('No golf=hole path found. Include a tee-to-green LineString tagged golf=hole.')
    if len({h['id'] for h in holes})!=len(holes):raise ValueError('Hole identities must be distinct.')
    return parsed,warnings


def inspect(data):
    parsed,warnings=features(data)
    return dict(holes=[dict(id=f['id'],label=f"Hole {f['tags'].get('ref','?')} · {f['id']}",par=f['tags'].get('par')) for f in parsed if f['kind']=='hole'],warnings=warnings)


def preview(data,hole_id,name,par,scorecard_yards=None,tee_label='Mapped tee',source_url='',edits=None,allow_incomplete=False):
    parsed,warnings=features(data)
    selected=next((f for f in parsed if f['kind']=='hole' and f['id']==hole_id),None)
    if not selected:raise ValueError('Choose one of the mapped holes.')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100:raise ValueError('Enter a course/hole name (1–100 characters).')
    if type(par) is not int or not 3<=par<=6:raise ValueError('Set par between 3 and 6.')
    if scorecard_yards is not None and (type(scorecard_yards) not in (int,float) or not math.isfinite(scorecard_yards) or not 30<=scorecard_yards<=1000):raise ValueError('Scorecard length must be 30–1,000 yd.')
    if not isinstance(tee_label,str) or not 1<=len(tee_label.strip())<=80:raise ValueError('Enter a tee label.')
    if not isinstance(source_url,str) or len(source_url)>500 or source_url and urllib.parse.urlsplit(source_url).scheme not in ('http','https'):
        raise ValueError('Use an http(s) source link.')
    origin=selected['line'][0]; lat=math.radians(origin[1]);R=6371008.8/.9144
    def eastnorth(p):return [(math.radians(p[0]-origin[0]))*math.cos(lat)*R,math.radians(p[1]-origin[1])*R]
    east,north=eastnorth(selected['line'][-1]);length=math.hypot(east,north)
    projection_length=length
    if not 30<=length<=1000:raise ValueError('Tee-to-pin separation must be 30–1,000 yd.')
    def project(p):
        e,n=eastnorth(p)
        if math.hypot(e,n)>5000:raise ValueError('Source features extend over 5,000 yd from this hole; crop to one course.')
        return [round((e*north-n*east)/length,4),round((e*east+n*north)/length,4)]
    line=[project(p) for p in selected['line']]
    route=sum(math.dist(a,b) for a,b in zip(line,line[1:]));pin=line[-1]
    if route>1500:raise ValueError('The playing path exceeds 1,500 yd; choose a single hole.')
    bounds=[min(p[0] for p in line)-80,max(p[0] for p in line)+80,min(p[1] for p in line)-35,max(p[1] for p in line)+40]
    surfaces={k:[] for k in ('fairway','green','tee','sand','water','nature')}
    for f in parsed:
        if f['kind']=='hole':continue
        poly={k:[project(p) for p in v] if k=='outer' else [[project(p) for p in h] for h in v] for k,v in f['polygon'].items()}
        ps=poly['outer']
        if max(p[0] for p in ps)<bounds[0] or min(p[0] for p in ps)>bounds[1] or max(p[1] for p in ps)<bounds[2] or min(p[1] for p in ps)>bounds[3]:continue
        surfaces[f['kind']].append(poly)
    boundary=dict(outer=[[bounds[0],bounds[2]],[bounds[1],bounds[2]],[bounds[1],bounds[3]],[bounds[0],bounds[3]]],holes=[])
    tee=[0,0]
    if edits is not None:
        from course_workbench import validate_edits
        fixed=validate_edits(edits)
        surfaces,boundary,tee,pin=(fixed[k] for k in ('surfaces','boundary','tee','pin'))
        line=[tee,*line[1:-1],pin]
        route=sum(math.dist(a,b) for a,b in zip(line,line[1:]))
        length=math.dist(tee,pin)
        if not 30<=length<=1000 or route>1500:raise ValueError('Edited tee/pin must define a 30–1,000 yd hole with a playing line under 1,500 yd.')
        ps=boundary['outer'];bounds=[min(p[0] for p in ps),max(p[0] for p in ps),min(p[1] for p in ps),max(p[1] for p in ps)]
        warnings.append('User-edited geometry in original projected yards. Check the corrected tee, pin, surfaces and game boundary against your source.')
    blockers=[]
    if not any(in_polygon(pin,p) for p in surfaces['green']):blockers.append('The hole endpoint is not inside a mapped green. Add or correct the green before publishing.')
    if not in_polygon(tee,boundary) or not in_polygon(pin,boundary):blockers.append('Both tee and pin must be inside the game boundary.')
    if any(in_polygon(pin,p) or in_polygon(tee,p) for k in ('water','sand') for p in surfaces[k]):blockers.append('Tee and pin cannot lie in water or sand. Correct overlapping surfaces.')
    if blockers and not allow_incomplete:raise ValueError(' '.join(blockers))
    if not surfaces['fairway']:warnings.append('No mapped fairway intersects this hole. Unmapped ground plays as rough; add fairway polygons before relying on lies.')
    else:
        samples=[[a[0]+(b[0]-a[0])*t/20,a[1]+(b[1]-a[1])*t/20] for a,b in zip(line,line[1:]) for t in range(1,20)]
        coverage=sum(any(in_polygon(p,f) for f in surfaces['fairway']) for p in samples)/len(samples)
        if coverage<.5:warnings.append('Less than half of the mapped playing line crosses a mapped fairway. Fairway coverage appears incomplete; nearby polygons are not proof this hole is mapped.')
    if not any(in_polygon(tee,p) for p in surfaces['tee']):
        warnings.append('Path start is not inside a mapped tee. A small inferred tee marker is used; check the tee location.')
        surfaces['tee'].append(dict(outer=[[round(tee[0]+3*math.cos(i*math.pi/4),4),round(tee[1]+3*math.sin(i*math.pi/4),4)] for i in range(8)],holes=[]))
    warnings+=[('Tee and pin were manually reviewed in the original map frame; verify the selected tee set and current pin position.' if edits is not None else 'Mapped path endpoints stand in for tee and pin; tee set and current pin position are unverified.'),
        'The pink outline is an artificial game boundary, not official out of bounds. Water/OB use the app replay penalty.',
        'Nearby-hole surfaces may be included. Check all boundaries; unmapped ground is rough. Flat green, no elevation or obstacle collisions.']
    if scorecard_yards is not None and abs(scorecard_yards-route)>max(10,scorecard_yards*.05):warnings.append('Scorecard and mapped playing-line length differ by more than 5%/10 yd. Geometry has not been stretched.')
    osm=isinstance(data.get('elements'),list) or 'openstreetmap.org' in source_url
    provenance=dict(kind='osm_import' if osm else 'geojson_import',source_url=source_url,
        attribution='© OpenStreetMap contributors · ODbL' if osm else 'User-supplied geometry; retain upstream attribution',
        license_url='https://www.openstreetmap.org/copyright' if osm else None,
        osm_timestamp=(data.get('osm3s') or {}).get('timestamp_osm_base') if isinstance(data.get('osm3s'),dict) else None,hole_id=hole_id,
        transform=dict(type='local_equirectangular_rotated',origin_lon_lat=origin,earth_radius_m=6371008.8,
                       forward_east_north=[east/projection_length,north/projection_length],units='yards'),
        route_yards=round(route,1),straight_yards=round(length,1),scorecard_yards=scorecard_yards,tee_label=tee_label)
    course=dict(name=name.strip(),par=par,yards=scorecard_yards or round(route),tee=tee,pin=pin,playing_line=line,
        hole_number=str(selected['tags'].get('ref','?')),bounds=bounds,boundary=boundary,
        viewbox=[bounds[2],bounds[0],bounds[3]-bounds[2],bounds[1]-bounds[0]],surfaces=surfaces,
        provenance=provenance,warnings=warnings,blocking_issues=blockers)
    if edits is not None:provenance['geometry_review']='manual_edits_v1'
    identity=json.dumps(course,sort_keys=True,allow_nan=False)
    course['id']='import-'+hashlib.sha256(identity.encode()).hexdigest()[:24]
    return course


def save(store,params,reviewed=False):
    if not store:raise ValueError('SQLite storage is required.')
    if reviewed is not True:raise ValueError('Review the boundaries and assumptions before saving.')
    c=preview(**params);key=PREFIX+c['id']
    with store.transaction():
        store.connection.execute('INSERT OR IGNORE INTO metadata VALUES(?,?)',(key,json.dumps(dict(course=c,source=params['data'],params=params,reviewed_at=timestamp()),allow_nan=False)))
    return c


def catalog(store):
    from bundled_courses import bundled_catalog
    result=bundled_catalog()
    if store:
        with store.lock:
            for row in store.connection.execute('SELECT value FROM metadata WHERE key LIKE ?',(PREFIX+'%',)):
                c=json.loads(row[0])['course'];result.append(dict(id=c['id'],name=c['name'],par=c['par'],yards=c['yards'],imported=True))
    return result


def load(store,course_id):
    from bundled_courses import COURSE_IDS, load_bundled
    if course_id in ('meadow-one-v1','meadow-one-v2'):return None
    if course_id in COURSE_IDS:return load_bundled(course_id)
    if store:
        with store.lock:row=store.connection.execute('SELECT value FROM metadata WHERE key=?',(PREFIX+course_id,)).fetchone()
        if row:return copy.deepcopy(json.loads(row[0])['course'])
    raise ValueError('Choose an available course from the library.')


def fetch_osm(way_id):
    if type(way_id) is not int or not 1<=way_id<=10**12:raise ValueError('Enter a valid OpenStreetMap course way ID.')
    query=f'[out:json][timeout:25];way({way_id});out geom;map_to_area->.a;(way(area.a)[golf];way(area.a)[natural];relation(area.a)[natural];);out geom;'
    request=urllib.request.Request('https://overpass-api.de/api/interpreter',data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'TraceLoft-course-prototype/1.0'})
    try:
        with urllib.request.urlopen(request,timeout=35) as response:raw=response.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('Course response is too large; export one hole as GeoJSON.')
        data=json.loads(raw);inspect(data);return data
    except (OSError,json.JSONDecodeError) as exc:raise ValueError('OpenStreetMap download unavailable. Try later or import a saved GeoJSON/Overpass file.') from exc
