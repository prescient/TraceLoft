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
