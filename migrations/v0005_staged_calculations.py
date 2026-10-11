"""Schema 4 -> 5: staged recalculation batches, lineage and reviewed publication.

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step. The writers called below are shared application code; the
v1 upgrade test in tests/test_shot_schema.py fails if a later change makes them incompatible
with this step, in which case freeze a copy of the old writer here.
"""

TO_VERSION = 5
SQL = '0005_staged_calculations.sql'
STAGE = 'staged_calculation_publication'


def backfill(c):
    from analysis_schema import save_collection
    from domain_schema import read_session

    for sid in c.execute('SELECT session_id FROM session_plans').fetchall():
        save_collection(c, read_session(c, sid[0]))


def prepare(store):
    from shot_schema import evidence_manifest

    return evidence_manifest(store.connection)


def reconcile(store, evidence):
    from shot_schema import evidence_manifest

    backfill(store.connection)
    if (
        store.connection.execute('PRAGMA foreign_key_check').fetchall()
        or evidence_manifest(store.connection) != evidence
    ):
        raise ValueError('Calculation migration reconciliation failed.')
