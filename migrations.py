"""Numbered, immutable schema upgrades for the TraceLoft SQLite database.

Each step upgrades exactly one schema version. It takes a verified pre-upgrade backup
(existing databases only), applies its DDL inside one BEGIN IMMEDIATE transaction,
reconciles original evidence before COMMIT and records a report under
`schema_migration.v<N>` in metadata. A failure rolls the step back completely.

Never edit a released step. To change the schema, append the next step to STEPS and
bump storage.SCHEMA_VERSION.
"""

import json

from storage import encoded, now


def _apply(store, version, ddl, stage, backup, prepare, reconcile):
    connection = store.connection
    snapshot = store.backup() if backup else None
    before = prepare(store)
    try:
        connection.executescript('BEGIN IMMEDIATE;\n' + ddl)
        details = reconcile(store, before) or {}
        report = dict(
            from_schema=version - 1,
            to_schema=version,
            at=now(),
            backup=str(snapshot) if snapshot else None,
            stage=stage,
            **details,
        )
        connection.execute(
            'INSERT INTO metadata VALUES(?,?)', (f'schema_migration.v{version}', encoded(report))
        )
        connection.execute(f'PRAGMA user_version={version}')
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise


EVIDENCE_COUNTS = (
    'shots',
    'observations',
    'metric_values',
    'sessions',
    'session_attempts',
    'ingest_events',
)


def to_v2_wide_metrics(store, backup):
    from shot_schema import DDL, backfill, evidence_manifest

    def prepare(store):
        counts = {table: store.count(table) for table in EVIDENCE_COUNTS}
        return counts, evidence_manifest(store.connection)

    def reconcile(store, before):
        counts, evidence = before
        backfill(store.connection)
        after = {table: store.count(table) for table in counts}
        if counts != after:
            raise ValueError('Schema upgrade changed original evidence counts.')
        if evidence_manifest(store.connection) != evidence:
            raise ValueError('Schema upgrade changed original evidence or saved outcomes.')
        return dict(before=counts, after=after, evidence=evidence)

    _apply(store, 2, DDL, 'wide_source_and_derived_metrics', backup, prepare, reconcile)


def to_v3_relational_domain(store, backup):
    from domain_schema import DDL, backfill, read_session
    from shot_schema import hydrate_session, evidence_manifest

    def prepare(store):
        originals = {
            r['id']: hydrate_session(store.connection, json.loads(r['payload_json']))
            for r in store.connection.execute('SELECT id,payload_json FROM sessions')
        }
        return evidence_manifest(store.connection), originals

    def reconcile(store, before):
        evidence, originals = before
        backfill(store.connection)
        for sid, data in originals.items():
            if read_session(store.connection, sid) != data:
                raise ValueError(f'Relational migration changed session {sid}.')
        if evidence_manifest(store.connection) != evidence:
            raise ValueError('Relational migration changed original evidence.')
        return dict(evidence=evidence, sessions_reconciled=len(originals))

    _apply(store, 3, DDL, 'relational_golfers_equipment_sessions', backup, prepare, reconcile)


def _foreign_keys_and_evidence(message, work=None):
    from shot_schema import evidence_manifest

    def reconcile(store, evidence):
        if work:
            work(store.connection)
        if (
            store.connection.execute('PRAGMA foreign_key_check').fetchall()
            or evidence_manifest(store.connection) != evidence
        ):
            raise ValueError(message)

    return reconcile


def _evidence(store):
    from shot_schema import evidence_manifest

    return evidence_manifest(store.connection)


def to_v4_collection_cohorts(store, backup):
    from analysis_schema import DDL

    reconcile = _foreign_keys_and_evidence('Analysis migration reconciliation failed.')
    _apply(store, 4, DDL, 'reproducible_collection_cohorts', backup, _evidence, reconcile)


def to_v5_staged_calculations(store, backup):
    from analysis_schema import backfill
    from recalculation import DDL

    reconcile = _foreign_keys_and_evidence('Calculation migration reconciliation failed.', backfill)
    _apply(store, 5, DDL, 'staged_calculation_publication', backup, _evidence, reconcile)


# Current schema version -> the step that upgrades it by one.
STEPS = {
    1: to_v2_wide_metrics,
    2: to_v3_relational_domain,
    3: to_v4_collection_cohorts,
    4: to_v5_staged_calculations,
}


def upgrade(store, new_database, lease_held):
    """Apply every pending step in order. Existing databases need the service lease."""
    lease = None
    try:
        while (version := store.connection.execute('PRAGMA user_version').fetchone()[0]) in STEPS:
            if lease is None and not new_database and not lease_held:
                from database_tools import ServiceLease

                lease = ServiceLease(store.path)
            STEPS[version](store, backup=not new_database)
    finally:
        if lease:
            lease.close()
