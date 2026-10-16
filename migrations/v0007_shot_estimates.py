"""Schema 6 -> 7: per-shot flight and club delivery estimates for every non-putt shot (D71).

RELEASED STEP: do not edit. tests/test_migrations.py pins this file and its SQL; change the
schema by adding the next step. The writer called below (shot_schema.shot_estimates) is shared
application code; the v1 upgrade test in tests/test_shot_schema.py fails if a later change makes it
incompatible with this step, in which case freeze a copy of the old writer here.

The backfill appends new selected results with context 'shot'. It changes no evidence, measurement,
session or attempt pin, which the evidence manifest proves.
"""

TO_VERSION = 7
SQL = '0007_shot_estimates.sql'
STAGE = 'per_shot_estimates'


def backfill(c):
    from shot_schema import shot_estimates

    shots = [row[0] for row in c.execute('SELECT id FROM shots ORDER BY rowid').fetchall()]
    for shot_id in shots:
        shot_estimates(c, shot_id)
    estimated = c.execute(
        "SELECT count(DISTINCT shot_id) FROM derived_metric_selection WHERE context_id='shot' "
        "AND model_family='club_delivery'"
    ).fetchone()[0]
    return dict(shots=len(shots), estimated=estimated)


def prepare(store):
    from shot_schema import evidence_manifest

    return evidence_manifest(store.connection)


def reconcile(store, evidence):
    from shot_schema import evidence_manifest

    report = backfill(store.connection)
    if (
        store.connection.execute('PRAGMA foreign_key_check').fetchall()
        or evidence_manifest(store.connection) != evidence
    ):
        raise ValueError('Per-shot estimate migration reconciliation failed.')
    return report
