"""Schema 1 -> 2: wide source metrics and versioned derived results.

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step. The writers called below are shared application code; the
v1 upgrade test in tests/test_shot_schema.py fails if a later change makes them incompatible
with this step, in which case freeze a copy of the old writer here.
"""

import json

TO_VERSION = 2
SQL = '0002_wide_metrics.sql'
STAGE = 'wide_source_and_derived_metrics'
EVIDENCE_COUNTS = (
    'shots',
    'observations',
    'metric_values',
    'sessions',
    'session_attempts',
    'ingest_events',
)


def backfill(connection):
    from shot_schema import save_attempt_results, source_features, write_source

    for row in connection.execute('SELECT id FROM observations').fetchall():
        write_source(connection, row['id'])
    for row in connection.execute('SELECT id FROM shots').fetchall():
        source_features(connection, row['id'])
    for row in connection.execute('SELECT payload_json FROM sessions').fetchall():
        session = json.loads(row['payload_json'])
        for ordinal, attempt in enumerate(session['shots'], 1):
            save_attempt_results(connection, session, attempt, ordinal, legacy=True)
    errors = connection.execute('PRAGMA foreign_key_check').fetchall()
    if errors:
        raise ValueError('Schema-v2 foreign-key reconciliation failed.')
    if (
        connection.execute('SELECT count(*) FROM observations').fetchone()[0]
        != connection.execute('SELECT count(*) FROM shot_source_metrics').fetchone()[0]
    ):
        raise ValueError('Schema-v2 report reconciliation failed.')


def prepare(store):
    from shot_schema import evidence_manifest

    counts = {table: store.count(table) for table in EVIDENCE_COUNTS}
    return counts, evidence_manifest(store.connection)


def reconcile(store, before):
    from shot_schema import evidence_manifest

    counts, evidence = before
    backfill(store.connection)
    after = {table: store.count(table) for table in counts}
    if counts != after:
        raise ValueError('Schema upgrade changed original evidence counts.')
    if evidence_manifest(store.connection) != evidence:
        raise ValueError('Schema upgrade changed original evidence or saved outcomes.')
    return dict(before=counts, after=after, evidence=evidence)
