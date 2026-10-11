"""Schema 3 -> 4: reproducible bag-mapping and wedge-matrix cohorts.

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step.
"""

TO_VERSION = 4
SQL = '0004_collection_cohorts.sql'
STAGE = 'reproducible_collection_cohorts'


def prepare(store):
    from shot_schema import evidence_manifest

    return evidence_manifest(store.connection)


def reconcile(store, evidence):
    from shot_schema import evidence_manifest

    if (
        store.connection.execute('PRAGMA foreign_key_check').fetchall()
        or evidence_manifest(store.connection) != evidence
    ):
        raise ValueError('Analysis migration reconciliation failed.')
