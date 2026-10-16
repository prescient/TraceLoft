"""Numbered, frozen schema upgrades for the TraceLoft SQLite database.

Layout:
  sql/0001_base.sql           schema 1, created by Store for a new database
  sql/000N_<stage>.sql        DDL of the step that upgrades schema N-1 to N
  v000N_<stage>.py            that step's prepare/backfill/reconcile code

Each step takes a verified pre-upgrade backup (existing databases only), runs its SQL inside
one BEGIN IMMEDIATE transaction, reconciles original evidence before COMMIT and records a
report under `schema_migration.v<N>` in metadata. A failure rolls the step back completely.

Released steps are immutable: tests/test_migrations.py pins the SHA-256 of every step file.
To change the schema, add v000<N+1> plus its SQL, append it to STEPS, bump
storage.SCHEMA_VERSION and add the new files' hashes to the test.
"""

from pathlib import Path

from storage import encoded, now

from . import (
    v0002_wide_metrics,
    v0003_relational_domain,
    v0004_collection_cohorts,
    v0005_staged_calculations,
    v0006_source_estimates,
    v0007_shot_estimates,
)

SQL_DIR = Path(__file__).resolve().parent / 'sql'

# Current schema version -> the released step that upgrades it by one.
STEPS = {
    1: v0002_wide_metrics,
    2: v0003_relational_domain,
    3: v0004_collection_cohorts,
    4: v0005_staged_calculations,
    5: v0006_source_estimates,
    6: v0007_shot_estimates,
}


def sql(name):
    return (SQL_DIR / name).read_text(encoding='utf-8')


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


def run_step(store, step, backup):
    _apply(store, step.TO_VERSION, sql(step.SQL), step.STAGE, backup, step.prepare, step.reconcile)


def upgrade(store, new_database, lease_held):
    """Apply every pending step in order. Existing databases need the service lease."""
    lease = None
    try:
        while (version := store.connection.execute('PRAGMA user_version').fetchone()[0]) in STEPS:
            if lease is None and not new_database and not lease_held:
                from database_tools import ServiceLease

                lease = ServiceLease(store.path)
            run_step(store, STEPS[version], backup=not new_database)
    finally:
        if lease:
            lease.close()
