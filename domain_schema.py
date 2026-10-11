"""Relational equipment, local golfers and typed session documents (schema 3).

JSON is retained only as legacy evidence and whole-artifact geometry/model data.
Typed document leaves preserve drill-specific settings and ordered state exactly;
entities used in joins have explicit identity and foreign-key tables.
"""

import json
import uuid
from storage import encoded, identity, now

LOCAL_USER = 'local-golfer'
EQUIPMENT_FIELDS = (
    'bag_id',
    'bag_name',
    'club_id',
    'club_label',
    'catalog_revision',
    'selection_mode',
)
SPEC_FIELDS = ('make', 'model', 'loft_deg', 'shaft', 'settings')
DDL = """
CREATE TABLE users(user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
 handedness TEXT NOT NULL CHECK(handedness IN ('right_handed','left_handed')),
 created_at TEXT NOT NULL, archived_at TEXT);
CREATE TABLE golfer_selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 user_id TEXT NOT NULL REFERENCES users(user_id));
CREATE TABLE session_owners(session_id TEXT PRIMARY KEY REFERENCES sessions(id),
 user_id TEXT NOT NULL REFERENCES users(user_id), attribution TEXT NOT NULL,
 UNIQUE(session_id,user_id));
CREATE TABLE shot_owners(shot_id TEXT PRIMARY KEY REFERENCES shots(id),
 user_id TEXT NOT NULL REFERENCES users(user_id), attribution TEXT NOT NULL, UNIQUE(shot_id,user_id));
CREATE TABLE equipment_catalogs(user_id TEXT PRIMARY KEY REFERENCES users(user_id),
 version INTEGER NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE bags(bag_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 created_at TEXT NOT NULL, UNIQUE(bag_id,user_id));
CREATE TABLE clubs(club_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 created_at TEXT NOT NULL, UNIQUE(club_id,user_id));
CREATE TABLE club_revisions(configuration_id TEXT PRIMARY KEY, club_id TEXT NOT NULL,
 user_id TEXT NOT NULL, revision INTEGER NOT NULL, make TEXT, model TEXT, loft_deg REAL,
 shaft TEXT, settings TEXT, created_at TEXT NOT NULL,
 FOREIGN KEY(club_id,user_id) REFERENCES clubs(club_id,user_id),
 UNIQUE(configuration_id,club_id,user_id), UNIQUE(club_id,revision));
CREATE TABLE bag_revisions(bag_revision_id TEXT PRIMARY KEY, bag_id TEXT NOT NULL,
 user_id TEXT NOT NULL, catalog_revision INTEGER NOT NULL, position INTEGER NOT NULL,
 name TEXT NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)), created_at TEXT NOT NULL,
 FOREIGN KEY(bag_id,user_id) REFERENCES bags(bag_id,user_id),
 UNIQUE(bag_id,catalog_revision), UNIQUE(bag_revision_id,user_id));
CREATE TABLE bag_memberships(membership_id TEXT PRIMARY KEY, bag_revision_id TEXT NOT NULL,
 user_id TEXT NOT NULL, club_id TEXT NOT NULL, configuration_id TEXT NOT NULL,
 position INTEGER NOT NULL, label TEXT NOT NULL,
 FOREIGN KEY(bag_revision_id,user_id) REFERENCES bag_revisions(bag_revision_id,user_id),
 FOREIGN KEY(configuration_id,club_id,user_id) REFERENCES club_revisions(configuration_id,club_id,user_id),
 UNIQUE(bag_revision_id,club_id), UNIQUE(membership_id,user_id));
CREATE TABLE session_fields(session_id TEXT NOT NULL REFERENCES sessions(id), path TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('object','array','null','text','real','integer','boolean','artifact')),
 text_value TEXT, real_value REAL, integer_value INTEGER, PRIMARY KEY(session_id,path));
CREATE TABLE attempt_fields(session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, path TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('object','array','null','text','real','integer','boolean','artifact')),
 text_value TEXT, real_value REAL, integer_value INTEGER, PRIMARY KEY(session_id,ordinal,path),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal));
CREATE TABLE shot_contexts(context_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
 shot_id TEXT NOT NULL REFERENCES shots(id), user_id TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('original','correction')),
 membership_id TEXT, bag_revision_id TEXT, bag_id TEXT, bag_name TEXT, club_id TEXT, club_label TEXT,
 catalog_revision INTEGER, selection_mode TEXT, present_mask INTEGER NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 FOREIGN KEY(session_id,user_id) REFERENCES session_owners(session_id,user_id),
 FOREIGN KEY(shot_id,user_id) REFERENCES shot_owners(shot_id,user_id),
 FOREIGN KEY(membership_id,user_id) REFERENCES bag_memberships(membership_id,user_id),
 FOREIGN KEY(bag_revision_id,user_id) REFERENCES bag_revisions(bag_revision_id,user_id),
 UNIQUE(context_id,session_id,ordinal,scope));
CREATE INDEX contexts_attempt ON shot_contexts(session_id,ordinal,scope,recorded_at);
CREATE TRIGGER contexts_immutable BEFORE UPDATE ON shot_contexts BEGIN
 SELECT RAISE(ABORT,'Shot contexts are immutable; append a scoped correction'); END;
CREATE TABLE context_selection(session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, scope TEXT NOT NULL,
 context_id TEXT NOT NULL REFERENCES shot_contexts(context_id), PRIMARY KEY(session_id,ordinal,scope),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 FOREIGN KEY(context_id,session_id,ordinal,scope) REFERENCES shot_contexts(context_id,session_id,ordinal,scope));
CREATE TABLE session_plans(plan_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 revision INTEGER NOT NULL, collection_kind TEXT NOT NULL, distance_basis TEXT NOT NULL,
 sample_goal INTEGER NOT NULL, created_at TEXT NOT NULL, UNIQUE(session_id,revision));
CREATE TABLE session_plan_items(plan_id TEXT NOT NULL REFERENCES session_plans(plan_id),
 position INTEGER NOT NULL, field TEXT NOT NULL, kind TEXT NOT NULL, text_value TEXT, real_value REAL,
 integer_value INTEGER, PRIMARY KEY(plan_id,position,field));
CREATE TABLE session_plan_selection(session_id TEXT PRIMARY KEY REFERENCES sessions(id),
 plan_id TEXT NOT NULL REFERENCES session_plans(plan_id));
CREATE TABLE tags(tag_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 name TEXT NOT NULL, name_key TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,name_key));
CREATE TABLE shot_tag_events(event_id TEXT PRIMARY KEY, tag_id TEXT NOT NULL REFERENCES tags(tag_id),
 shot_id TEXT NOT NULL REFERENCES shots(id), session_id TEXT, ordinal INTEGER,
 scope TEXT NOT NULL CHECK(scope IN ('shot','attempt')), added INTEGER NOT NULL CHECK(added IN (0,1)),
 batch_id TEXT NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 CHECK((scope='shot' AND session_id IS NULL AND ordinal IS NULL) OR
       (scope='attempt' AND session_id IS NOT NULL AND ordinal IS NOT NULL)));
CREATE INDEX tag_latest ON shot_tag_events(tag_id,shot_id,session_id,ordinal);
CREATE TRIGGER tag_ownership BEFORE INSERT ON shot_tag_events BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM shot_owners o JOIN tags t USING(user_id)
 WHERE o.shot_id=NEW.shot_id AND t.tag_id=NEW.tag_id) THEN RAISE(ABORT,'Tag and shot golfers differ') END;
 SELECT CASE WHEN NEW.scope='attempt' AND NOT EXISTS(SELECT 1 FROM session_attempts a
 WHERE a.session_id=NEW.session_id AND a.ordinal=NEW.ordinal AND a.shot_id=NEW.shot_id)
 THEN RAISE(ABORT,'Tag attempt belongs to another shot') END; END;
CREATE TRIGGER tag_events_immutable BEFORE UPDATE ON shot_tag_events BEGIN
 SELECT RAISE(ABORT,'Tag events are immutable; append a reversal'); END;
CREATE TRIGGER session_evidence_immutable BEFORE UPDATE OF payload_json ON sessions
 WHEN OLD.payload_json!=NEW.payload_json BEGIN SELECT RAISE(ABORT,'Legacy session evidence is immutable'); END;
CREATE TRIGGER attempt_evidence_immutable BEFORE UPDATE OF payload_json ON session_attempts
 WHEN OLD.payload_json!=NEW.payload_json BEGIN SELECT RAISE(ABORT,'Legacy attempt evidence is immutable'); END;
CREATE VIEW v_shot_tags AS SELECT e.* , t.user_id, t.name FROM shot_tag_events e JOIN tags t USING(tag_id)
 WHERE e.added=1 AND NOT EXISTS(SELECT 1 FROM shot_tag_events newer
 WHERE newer.tag_id=e.tag_id AND newer.shot_id=e.shot_id
 AND newer.scope=e.scope AND newer.session_id IS e.session_id AND newer.ordinal IS e.ordinal
 AND newer.rowid>e.rowid);
CREATE VIEW v_session_equipment AS SELECT a.session_id,a.ordinal,a.shot_id, o.user_id,u.display_name,
 c.context_id,c.bag_id,c.bag_name,c.club_id,c.club_label,c.catalog_revision,c.selection_mode,
 c.bag_revision_id,c.membership_id,m.configuration_id
 FROM session_attempts a JOIN session_owners o USING(session_id) JOIN users u USING(user_id)
 LEFT JOIN context_selection p ON p.session_id=a.session_id AND p.ordinal=a.ordinal
 AND p.scope=CASE WHEN EXISTS(SELECT 1 FROM context_selection x WHERE x.session_id=a.session_id
 AND x.ordinal=a.ordinal AND x.scope='correction') THEN 'correction' ELSE 'original' END
 LEFT JOIN shot_contexts c ON c.context_id=p.context_id LEFT JOIN bag_memberships m USING(membership_id);
CREATE VIEW v_session_state AS SELECT s.id session_id,o.user_id,u.display_name,s.started,s.ended,s.drill,s.deleted_at,s.revision,
 (SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/session_kind') session_kind,
 COALESCE((SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/practice_type'),'putting') practice_type,
 COALESCE((SELECT integer_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/demo'),0) simulated,
 (SELECT integer_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/game/hole_index') hole_index,
 (SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/game/lie') current_lie
 FROM sessions s JOIN session_owners o ON o.session_id=s.id JOIN users u USING(user_id);
CREATE VIEW v_attempt_outcomes AS SELECT a.session_id,a.ordinal,a.shot_id,a.legacy_key,a.target,a.success,a.excluded,
 COALESCE((SELECT integer_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/removed'),0) removed,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/swing_label') swing_label,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/game_correction/kind') shot_correction,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/cleanup_reason') cleanup_reason
 FROM session_attempts a;
"""


def scalar(value):
    if value is None:
        return ('null', None, None, None)
    if isinstance(value, bool):
        return ('boolean', None, None, int(value))
    if isinstance(value, int):
        return ('integer', None, None, value)
    if isinstance(value, float):
        return ('real', None, value, None)
    if isinstance(value, str):
        return ('text', value, None, None)
    raise ValueError('Expected a typed scalar.')


def decode(row):
    return {
        'null': lambda: None,
        'boolean': lambda: bool(row['integer_value']),
        'integer': lambda: row['integer_value'],
        'real': lambda: row['real_value'],
        'text': lambda: row['text_value'],
        'artifact': lambda: json.loads(row['text_value']),
        'object': dict,
        'array': list,
    }[row['kind']]()


def pointer(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def flatten(value, path='', artifacts=()):
    # Only declared whole artifacts use JSON; all state/settings/corrections are typed leaves.
    if path in artifacts:
        yield (path, 'artifact', encoded(value), None, None)
    elif isinstance(value, (dict, list)):
        yield (path, 'object' if isinstance(value, dict) else 'array', None, None, None)
        for k, v in value.items() if isinstance(value, dict) else enumerate(value):
            yield from flatten(v, path + '/' + pointer(k), artifacts)
    else:
        yield (path, *scalar(value))


def unflatten(rows):
    nodes = {r['path']: decode(r) for r in rows}
    for path in sorted(nodes, key=lambda p: (p.count('/'), p)):
        if not path:
            continue
        parent, key = path.rsplit('/', 1)
        key = key.replace('~1', '/').replace('~0', '~')
        container = nodes[parent]
        if isinstance(container, list):
            index = int(key)
            while len(container) <= index:
                container.append(None)
            container[index] = nodes[path]
        else:
            container[key] = nodes[path]
    return nodes.get('', {})


def active_user(c):
    return c.execute('SELECT user_id FROM golfer_selection WHERE singleton=1').fetchone()[0]


def save_catalog(c, catalog, user_id):
    current = c.execute(
        'SELECT revision FROM equipment_catalogs WHERE user_id=?', (user_id,)
    ).fetchone()
    if current and catalog['revision'] <= current[0]:
        if read_catalog(c, user_id) != catalog:
            raise ValueError('Equipment revision is stale or conflicts.')
        return
    for pos, bag in enumerate(catalog['bags']):
        c.execute('INSERT OR IGNORE INTO bags VALUES(?,?,?)', (bag['id'], user_id, now()))
        if (
            c.execute('SELECT user_id FROM bags WHERE bag_id=?', (bag['id'],)).fetchone()[0]
            != user_id
        ):
            raise ValueError('Bag belongs to another golfer.')
        revision = identity('bag:' + bag['id'] + ':' + str(catalog['revision']))
        c.execute(
            'INSERT INTO bag_revisions VALUES(?,?,?,?,?,?,?,?)',
            (revision, bag['id'], user_id, catalog['revision'], pos, bag['name'], 1, now()),
        )
        for cp, club in enumerate(bag['clubs']):
            c.execute('INSERT OR IGNORE INTO clubs VALUES(?,?,?)', (club['id'], user_id, now()))
            if (
                c.execute('SELECT user_id FROM clubs WHERE club_id=?', (club['id'],)).fetchone()[0]
                != user_id
            ):
                raise ValueError('Club belongs to another golfer.')
            latest = c.execute(
                'SELECT * FROM club_revisions WHERE club_id=? ORDER BY revision DESC LIMIT 1',
                (club['id'],),
            ).fetchone()
            specs = [club.get(k) for k in SPEC_FIELDS]
            if latest and specs == [latest[k] for k in SPEC_FIELDS]:
                config = latest['configuration_id']
            else:
                config = uuid.uuid4().hex
                c.execute(
                    'INSERT INTO club_revisions VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (
                        config,
                        club['id'],
                        user_id,
                        latest['revision'] + 1 if latest else 1,
                        *specs,
                        now(),
                    ),
                )
            c.execute(
                'INSERT INTO bag_memberships VALUES(?,?,?,?,?,?,?)',
                (
                    identity('membership:' + revision + ':' + club['id']),
                    revision,
                    user_id,
                    club['id'],
                    config,
                    cp,
                    club['label'],
                ),
            )
    c.execute(
        'INSERT INTO equipment_catalogs VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET version=excluded.version,revision=excluded.revision',
        (user_id, catalog['version'], catalog['revision']),
    )


def read_catalog(c, user_id=None):
    user_id = user_id or active_user(c)
    row = c.execute('SELECT * FROM equipment_catalogs WHERE user_id=?', (user_id,)).fetchone()
    if not row:
        return None
    catalog = dict(version=row['version'], revision=row['revision'], bags=[])
    for b in c.execute(
        'SELECT * FROM bag_revisions WHERE user_id=? AND catalog_revision=? AND active=1 ORDER BY position',
        (user_id, row['revision']),
    ):
        clubs = []
        for m in c.execute(
            'SELECT m.*,r.make,r.model,r.loft_deg,r.shaft,r.settings FROM bag_memberships m JOIN club_revisions r USING(configuration_id) WHERE bag_revision_id=? ORDER BY position',
            (b['bag_revision_id'],),
        ):
            club = dict(id=m['club_id'], label=m['label'])
            club.update({k: m[k] for k in SPEC_FIELDS if m[k] is not None})
            clubs.append(club)
        catalog['bags'].append(dict(id=b['bag_id'], name=b['name'], clubs=clubs))
    return catalog


def context(c, sid, ordinal, shot, user_id, scope, eq):
    for table, column, key in (('bags', 'bag_id', 'bag_id'), ('clubs', 'club_id', 'club_id')):
        owner = c.execute(
            f'SELECT user_id FROM {table} WHERE {column}=?', (eq.get(key),)
        ).fetchone()
        if owner and owner[0] != user_id:
            raise ValueError('Equipment belongs to another golfer.')
    mask = sum(1 << i for i, k in enumerate(EQUIPMENT_FIELDS) if k in eq)
    vals = [eq.get(k) for k in EQUIPMENT_FIELDS]
    cid = identity(
        'context:' + sid + ':' + str(ordinal) + ':' + scope + ':' + encoded([mask, vals])
    )
    revision = c.execute(
        'SELECT bag_revision_id FROM bag_revisions WHERE bag_id=? AND user_id=? AND catalog_revision=?',
        (eq.get('bag_id'), user_id, eq.get('catalog_revision')),
    ).fetchone()
    revision = revision[0] if revision else None
    membership = c.execute(
        'SELECT membership_id FROM bag_memberships WHERE bag_revision_id=? AND club_id=?',
        (revision, eq.get('club_id')),
    ).fetchone()
    # Historical unresolved IDs/labels are preserved; unavailable config lineage stays NULL.
    c.execute(
        'INSERT OR IGNORE INTO shot_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (
            cid,
            sid,
            ordinal,
            shot,
            user_id,
            scope,
            membership[0] if membership else None,
            revision,
            *vals,
            mask,
            now(),
        ),
    )
    old = c.execute(
        'SELECT context_id FROM context_selection WHERE session_id=? AND ordinal=? AND scope=?',
        (sid, ordinal, scope),
    ).fetchone()
    if scope == 'original' and old and old[0] != cid:
        raise ValueError('Original equipment context cannot be rewritten; use a correction.')
    c.execute(
        'INSERT INTO context_selection VALUES(?,?,?,?) ON CONFLICT(session_id,ordinal,scope) DO UPDATE SET context_id=excluded.context_id',
        (sid, ordinal, scope, cid),
    )


def sync_fields(c, table, scope, rows):
    """Write only changed typed leaves, preserving artifact and container shapes."""
    columns = ('session_id',) if table == 'session_fields' else ('session_id', 'ordinal')
    where = ' AND '.join(column + '=?' for column in columns)
    existing = {
        row['path']: tuple(
            row[key] for key in ('path', 'kind', 'text_value', 'real_value', 'integer_value')
        )
        for row in c.execute(f'SELECT * FROM {table} WHERE {where}', scope)
    }
    incoming = {row[0]: tuple(row) for row in rows}
    c.executemany(
        f'DELETE FROM {table} WHERE {where} AND path=?',
        [(*scope, path) for path in existing.keys() - incoming.keys()],
    )
    placeholders = ','.join('?' for _ in range(len(columns) + 5))
    keys = ','.join((*columns, 'path'))
    c.executemany(
        f'INSERT INTO {table} VALUES({placeholders}) ON CONFLICT({keys}) '
        'DO UPDATE SET kind=excluded.kind,text_value=excluded.text_value,'
        'real_value=excluded.real_value,integer_value=excluded.integer_value',
        [(*scope, *row) for path, row in incoming.items() if existing.get(path) != row],
    )


def write_session(c, data, user_id=None, backfill=False, changed_attempts=None):
    sid = data['id']
    old = c.execute('SELECT user_id FROM session_owners WHERE session_id=?', (sid,)).fetchone()
    owner = old[0] if old else user_id or active_user(c)
    if data.get('user_id', owner) != owner:
        raise ValueError('A session cannot change golfer.')
    c.execute(
        'INSERT OR IGNORE INTO session_owners VALUES(?,?,?)',
        (sid, owner, 'single_player_history' if backfill else 'selected_at_start'),
    )
    config = {k: v for k, v in data.items() if k not in ('shots', 'collection_plan', 'user_id')}
    sync_fields(
        c,
        'session_fields',
        (sid,),
        flatten(config, artifacts=('/course', '/round/holes', '/distance_model')),
    )
    if 'collection_plan' in data:
        oldplan = c.execute(
            'SELECT plan_id FROM session_plan_selection WHERE session_id=?', (sid,)
        ).fetchone()
        fingerprint = identity('plan:' + sid + ':' + encoded(data['collection_plan']))
        if oldplan and oldplan[0] != fingerprint:
            raise ValueError('Collection plans are frozen; start a new plan.')
        c.execute(
            'INSERT OR IGNORE INTO session_plans VALUES(?,?,?,?,?,?,?)',
            (
                fingerprint,
                sid,
                1,
                data['collection_kind'],
                data['range_metric'],
                data['collection_samples'],
                now(),
            ),
        )
        for pos, eq in enumerate(data['collection_plan']):
            c.executemany(
                'INSERT OR IGNORE INTO session_plan_items VALUES(?,?,?,?,?,?,?)',
                [(fingerprint, pos, k, *scalar(v)) for k, v in eq.items()],
            )
        c.execute('INSERT OR IGNORE INTO session_plan_selection VALUES(?,?)', (sid, fingerprint))
    for ordinal, shot in enumerate(data['shots'], 1):
        if changed_attempts is not None and ordinal not in changed_attempts:
            continue
        link = c.execute(
            'SELECT shot_id FROM session_attempts WHERE session_id=? AND ordinal=?', (sid, ordinal)
        ).fetchone()[0]
        prior = c.execute('SELECT user_id FROM shot_owners WHERE shot_id=?', (link,)).fetchone()
        if prior and prior[0] != owner:
            raise ValueError('Shot and session belong to different golfers.')
        c.execute(
            'INSERT OR IGNORE INTO shot_owners VALUES(?,?,?)', (link, owner, 'session_context')
        )
        context(
            c,
            sid,
            ordinal,
            link,
            owner,
            'original',
            {k: shot[k] for k in EQUIPMENT_FIELDS if k in shot},
        )
        corrected = shot.get('corrected_equipment')
        if corrected:
            context(c, sid, ordinal, link, owner, 'correction', corrected)
        else:
            c.execute(
                "DELETE FROM context_selection WHERE session_id=? AND ordinal=? AND scope='correction'",
                (sid, ordinal),
            )
        fields = {k: v for k, v in shot.items() if k not in EQUIPMENT_FIELDS and k != 'flight'}
        # Numeric reads hydrate from source columns; these typed leaves retain missing/invalid
        # original representations and the precise provider key set, never a model fallback.
        sync_fields(c, 'attempt_fields', (sid, ordinal), flatten(fields))


def read_session(c, sid):
    data = unflatten(
        c.execute('SELECT * FROM session_fields WHERE session_id=?', (sid,)).fetchall()
    )
    if not data:
        raise FileNotFoundError('Session not found.')
    plan = c.execute(
        'SELECT plan_id FROM session_plan_selection WHERE session_id=?', (sid,)
    ).fetchone()
    if plan:
        cells = {}
        for row in c.execute(
            'SELECT * FROM session_plan_items WHERE plan_id=? ORDER BY position', (plan[0],)
        ):
            cells.setdefault(row['position'], {})[row['field']] = decode(row)
        data['collection_plan'] = list(cells.values())
    # Three queries per session regardless of attempt count (previously two per attempt).
    # unflatten() assembles by sorted path, so grouping rows by ordinal preserves the DTO.
    fields, contexts = {}, {}
    for row in c.execute('SELECT * FROM attempt_fields WHERE session_id=?', (sid,)):
        fields.setdefault(row['ordinal'], []).append(row)
    for row in c.execute(
        'SELECT p.ordinal selected_ordinal, c.* FROM context_selection p JOIN shot_contexts c '
        'USING(context_id) WHERE p.session_id=? ORDER BY p.ordinal, p.scope',
        (sid,),
    ):
        contexts.setdefault(row['selected_ordinal'], []).append(row)
    data['shots'] = []
    for link in c.execute(
        'SELECT ordinal FROM session_attempts WHERE session_id=? ORDER BY ordinal', (sid,)
    ).fetchall():
        ordinal = link[0]
        shot = unflatten(fields.get(ordinal, []))
        for row in contexts.get(ordinal, []):
            eq = {
                k: row[k] for i, k in enumerate(EQUIPMENT_FIELDS) if row['present_mask'] & (1 << i)
            }
            if row['scope'] == 'original':
                shot.update(eq)
            else:
                shot['corrected_equipment'] = eq
        data['shots'].append(shot)
    # Preserve legacy DTO shapes; profile identity is exposed separately in service/review DTOs.
    from shot_schema import hydrate_session

    return hydrate_session(c, data)


def backfill(c):
    c.execute(
        'INSERT INTO users VALUES(?,?,?,?,?)',
        (LOCAL_USER, 'My golfer', 'right_handed', now(), None),
    )
    c.execute('INSERT INTO golfer_selection VALUES(1,?)', (LOCAL_USER,))
    row = c.execute("SELECT value FROM metadata WHERE key='equipment_catalog.v1'").fetchone()
    if row:
        save_catalog(c, json.loads(row[0]), LOCAL_USER)
    else:
        from equipment import default_catalog

        save_catalog(c, default_catalog(), LOCAL_USER)
    for row in c.execute('SELECT payload_json FROM sessions').fetchall():
        write_session(c, json.loads(row[0]), backfill=True)
    if c.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Relational migration foreign-key check failed.')
