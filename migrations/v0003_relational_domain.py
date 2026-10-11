"""Schema 2 -> 3: relational golfers, equipment, contexts, tags, plans and session state.

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step. The writers called below are shared application code; the
v1 upgrade test in tests/test_shot_schema.py fails if a later change makes them incompatible
with this step, in which case freeze a copy of the old writer here.
"""

import json

TO_VERSION = 3
SQL = '0003_relational_domain.sql'
STAGE = 'relational_golfers_equipment_sessions'


def backfill(c):
    from domain_schema import LOCAL_USER, now, save_catalog, write_session

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


def prepare(store):
    from shot_schema import evidence_manifest, hydrate_session

    originals = {
        r['id']: hydrate_session(store.connection, json.loads(r['payload_json']))
        for r in store.connection.execute('SELECT id,payload_json FROM sessions')
    }
    return evidence_manifest(store.connection), originals


def reconcile(store, before):
    from domain_schema import read_session
    from shot_schema import evidence_manifest

    evidence, originals = before
    backfill(store.connection)
    for sid, data in originals.items():
        if read_session(store.connection, sid) != data:
            raise ValueError(f'Relational migration changed session {sid}.')
    if evidence_manifest(store.connection) != evidence:
        raise ValueError('Relational migration changed original evidence.')
    return dict(evidence=evidence, sessions_reconciled=len(originals))
