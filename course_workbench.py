"""Validated local-yard edits and durable, revision-checked course drafts."""
import copy
import json
import math
import re
import uuid
from course_import import polygon, preview
from putting import timestamp

DRAFT_PREFIX='course_draft.v1.'
KINDS=('fairway','green','tee','sand','water','nature')


def yard_point(p):
    if not isinstance(p,list) or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>5000 for v in p):
        raise ValueError('Map coordinates must be two finite yard values within ±5,000 yd.')
    return [round(v,4) for v in p]


def validate_edits(edits):
    if not isinstance(edits,dict) or set(edits)!= {'surfaces','boundary','tee','pin'}:
        raise ValueError('Use surfaces, boundary, tee and pin for map corrections.')
    surfaces=edits['surfaces']
    if not isinstance(surfaces,dict) or set(surfaces)!=set(KINDS):raise ValueError('Unknown or missing surface type.')
    if any(not isinstance(v,list) for v in surfaces.values()) or sum(map(len,surfaces.values()))>250:
        raise ValueError('Use at most 250 surface polygons per edited hole.')
    count=0
    def poly(p):
        nonlocal count
        if not isinstance(p,dict) or set(p)-{'outer','holes'}:raise ValueError('Invalid polygon object.')
        if not isinstance(p.get('holes',[]),list):raise ValueError('Polygon cutouts must be an array.')
        rings=[p.get('outer'),*p.get('holes',[])]
        result=polygon(rings,yard_point)
        count+=sum(len(r) for r in [result['outer'],*result['holes']])
        if count>12000:raise ValueError('Simplify edited geometry to at most 12,000 vertices.')
        return result
    return dict(surfaces={k:[poly(p) for p in surfaces[k]] for k in KINDS},boundary=poly(edits['boundary']),
                tee=yard_point(edits['tee']),pin=yard_point(edits['pin']))


def draft_key(identity):
    if not isinstance(identity,str) or not re.fullmatch('[a-f0-9]{32}',identity):raise ValueError('Invalid draft ID.')
    return DRAFT_PREFIX+identity


def list_drafts(store):
    with store.lock:
        rows=store.connection.execute('SELECT value FROM metadata WHERE key LIKE ?',(DRAFT_PREFIX+'%',)).fetchall()
    drafts=[json.loads(r[0]) for r in rows]
    return sorted([dict(id=d['id'],revision=d['revision'],updated=d['updated'],name=d['params']['name']) for d in drafts],key=lambda d:d['updated'],reverse=True)


def load_draft(store,identity):
    with store.lock:row=store.connection.execute('SELECT value FROM metadata WHERE key=?',(draft_key(identity),)).fetchone()
    if not row:raise ValueError('Draft not found.')
    return json.loads(row[0])


def save_draft(store,params,identity=None,revision=0):
    if not store:raise ValueError('SQLite storage is required.')
    if len(json.dumps(params,allow_nan=False).encode('utf-8'))>4000000:
        raise ValueError('Course drafts must be under 4 MB.')
    preview(**params,allow_incomplete=True)
    if type(revision) is not int or revision<0:raise ValueError('Invalid draft revision.')
    identity=identity or uuid.uuid4().hex; key=draft_key(identity)
    with store.transaction():
        row=store.connection.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone()
        previous=json.loads(row[0]) if row else None
        if revision!=(previous['revision'] if previous else 0):
            raise ValueError('This draft changed in another window. Reopen it before saving; your local edits have not been overwritten.')
        draft=dict(format='traceloft-course-draft-v1',id=identity,revision=revision+1,updated=timestamp(),params=copy.deepcopy(params))
        store.connection.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(key,json.dumps(draft,allow_nan=False)))
    return draft
