"""Schema 5 -> 6: estimates a shot source makes itself, kept apart from its measurements (D70).

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step. The table starts empty: earlier receipts carried no estimates
block, so there is nothing to backfill and no existing evidence changes.
"""

TO_VERSION = 6
SQL = '0006_source_estimates.sql'
STAGE = 'source_estimates'


def prepare(store):
    from shot_schema import evidence_manifest

    return evidence_manifest(store.connection)


def reconcile(store, evidence):
    from shot_schema import evidence_manifest

    if (
        store.connection.execute('PRAGMA foreign_key_check').fetchall()
        or evidence_manifest(store.connection) != evidence
    ):
        raise ValueError('Source estimate migration reconciliation failed.')
