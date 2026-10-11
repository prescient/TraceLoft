"""Schema-v2 shot metrics: readable reports and immutable calculation results.

Legacy evidence/session DTOs remain intact during this first migration stage.
All functions run inside the caller's SQLite transaction.
"""

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone


# field: (readable column, canonical metric key, divisor from canonical SI)
SOURCE_FIELDS = {
    'club_speed': ('club_head_speed_mph', 'club.speed', 0.44704),
    'smash_factor': ('smash_factor', 'ball.smash_factor', 1),
    'club_path': ('club_path_deg', 'club.path', 1),
    'attack_angle': ('angle_of_attack_deg', 'club.attack_angle', 1),
    'carry': ('carry_distance_yd', 'flight.carry_distance', 0.9144),
    'total': ('total_distance_yd', 'flight.total_distance', 0.9144),
    'ball_speed': ('ball_speed_mph', 'ball.speed', 0.44704),
    'total_spin': ('total_spin_rpm', 'ball.spin_rate', 1),
    'launch_ang': ('vertical_launch_angle_deg', 'ball.launch_angle', 1),
    'launch_dir': ('horizontal_launch_angle_deg', 'ball.launch_direction', 1),
    'spin_axis': ('spin_tilt_axis_deg', 'ball.spin_axis', 1),
    'back_spin': ('back_spin_rpm', 'ball.backspin', 1),
    'side_spin': ('side_spin_rpm', 'ball.sidespin', 1),
    'peak_height': ('ball_apex_ft', 'flight.apex_height', 0.3048),
    'descent_ang': ('ball_descent_angle_deg', 'flight.descent_angle', 1),
    'offline': ('ball_offline_yd', 'flight.total_side', 0.9144),
    'curve': ('ball_curve_yd', 'flight.curve', 0.9144),
    'hang_time': ('hang_time_s', 'flight.flight_time', 1),
}
DERIVED_COLUMNS = (
    'carry_distance_yd',
    'total_distance_yd',
    'carry_forward_yd',
    'carry_right_yd',
    'total_forward_yd',
    'total_right_yd',
    'offline_distance_yd',
    'absolute_offline_yd',
    'apex_ft',
    'descent_angle_deg',
    'hang_time_s',
    'calculated_smash_factor',
    'source_rollout_yd',
    'estimated_distance_ft',
    'target_distance_ft',
    'distance_error_ft',
    'stimp_ft',
)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def identity(value):
    return uuid.uuid5(uuid.NAMESPACE_URL, 'traceloft-schema2:' + value).hex


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


SOURCE_COLUMNS = ',\n'.join(f'{column} REAL' for column, _, _ in SOURCE_FIELDS.values())
DERIVED_SQL_COLUMNS = ',\n'.join(f'{column} REAL' for column in DERIVED_COLUMNS)
DDL = f"""
CREATE UNIQUE INDEX observations_identity_shot ON observations(id,shot_id);
CREATE UNIQUE INDEX attempts_identity_shot ON session_attempts(session_id,ordinal,shot_id);
CREATE TABLE shot_source_metrics(
 report_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL UNIQUE,
 shot_id TEXT, normalization_revision TEXT NOT NULL, created_at TEXT NOT NULL,
 {SOURCE_COLUMNS},
 UNIQUE(report_id,shot_id),
 FOREIGN KEY(observation_id,shot_id) REFERENCES observations(id,shot_id)
 DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX source_shot ON shot_source_metrics(shot_id);
CREATE TABLE source_metric_quality(
 report_id TEXT NOT NULL REFERENCES shot_source_metrics(report_id), column_name TEXT NOT NULL,
 availability TEXT NOT NULL CHECK(availability IN ('available','unavailable','invalid','not_supplied')),
 source_field TEXT NOT NULL, source_unit TEXT, method TEXT, semantic_variant TEXT,
 PRIMARY KEY(report_id,column_name),
 CHECK(column_name IN ({','.join(repr(c) for c, _, _ in SOURCE_FIELDS.values())})));
CREATE TABLE shot_primary_source(
 shot_id TEXT PRIMARY KEY REFERENCES shots(id), report_id TEXT NOT NULL,
 policy TEXT NOT NULL, selected_at TEXT NOT NULL,
 FOREIGN KEY(report_id,shot_id) REFERENCES shot_source_metrics(report_id,shot_id));
CREATE TABLE calculation_runs(
 run_id TEXT PRIMARY KEY, model_family TEXT NOT NULL, model_version TEXT NOT NULL,
 output_schema_revision TEXT NOT NULL, provenance TEXT NOT NULL,
 code_hash TEXT, parameters_json TEXT NOT NULL, created_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('complete','unavailable','error')));
CREATE TABLE shot_derived_metrics(
 result_id TEXT PRIMARY KEY, shot_id TEXT NOT NULL REFERENCES shots(id),
 run_id TEXT NOT NULL REFERENCES calculation_runs(run_id),
 model_family TEXT NOT NULL, context_id TEXT NOT NULL,
 input_fingerprint TEXT NOT NULL, status TEXT NOT NULL,
 reason TEXT, flight_shape TEXT, {DERIVED_SQL_COLUMNS},
 artifact_json TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(result_id,shot_id,model_family,context_id),
 UNIQUE(shot_id,run_id,model_family,context_id,input_fingerprint));
CREATE INDEX derived_shot ON shot_derived_metrics(shot_id,model_family,context_id);
CREATE TABLE calculation_inputs(
 result_id TEXT NOT NULL, shot_id TEXT NOT NULL, report_id TEXT NOT NULL,
 PRIMARY KEY(result_id,report_id),
 FOREIGN KEY(result_id,shot_id) REFERENCES shot_derived_metrics(result_id,shot_id),
 FOREIGN KEY(report_id,shot_id) REFERENCES shot_source_metrics(report_id,shot_id));
CREATE UNIQUE INDEX derived_identity_shot ON shot_derived_metrics(result_id,shot_id);
CREATE TABLE shot_trajectories(
 result_id TEXT PRIMARY KEY REFERENCES shot_derived_metrics(result_id),
 coordinates TEXT NOT NULL, sample_count INTEGER NOT NULL, points_json TEXT NOT NULL);
CREATE TABLE derived_metric_selection(
 shot_id TEXT NOT NULL, model_family TEXT NOT NULL, context_id TEXT NOT NULL,
 result_id TEXT NOT NULL, selected_at TEXT NOT NULL,
 PRIMARY KEY(shot_id,model_family,context_id),
 FOREIGN KEY(result_id,shot_id,model_family,context_id)
 REFERENCES shot_derived_metrics(result_id,shot_id,model_family,context_id));
CREATE TABLE attempt_derived_results(
 session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, shot_id TEXT NOT NULL,
 model_family TEXT NOT NULL, context_id TEXT NOT NULL, result_id TEXT NOT NULL,
 PRIMARY KEY(session_id,ordinal,model_family),
 FOREIGN KEY(session_id,ordinal,shot_id) REFERENCES session_attempts(session_id,ordinal,shot_id),
 FOREIGN KEY(result_id,shot_id,model_family,context_id)
 REFERENCES shot_derived_metrics(result_id,shot_id,model_family,context_id));
CREATE VIEW v_shots_source AS
 SELECT s.id shot_id,s.occurred_at,s.time_basis,s.reported_club,
 p.policy source_selection_policy,r.report_id,r.observation_id,r.normalization_revision,
 {','.join('r.' + c for c, _, _ in SOURCE_FIELDS.values())},
 o.event_id,o.mapping_id,o.provenance,c.source_id
 FROM shots s LEFT JOIN shot_primary_source p ON p.shot_id=s.id
 LEFT JOIN shot_source_metrics r ON r.report_id=p.report_id
 LEFT JOIN observations o ON o.id=r.observation_id
 LEFT JOIN ingest_events e ON e.id=o.event_id
 LEFT JOIN capture_streams c ON c.id=e.stream_id;
CREATE VIEW v_shots_analysis AS
 SELECT s.*,d.result_id,d.model_family,d.context_id,d.status calculation_status,
 d.absolute_offline_yd,d.calculated_smash_factor,d.source_rollout_yd,
 d.carry_distance_yd model_carry_distance_yd,d.total_distance_yd model_total_distance_yd,
 d.apex_ft model_apex_ft,d.descent_angle_deg model_descent_angle_deg,
 d.hang_time_s model_hang_time_s,d.flight_shape,
 r.run_id,r.model_version,r.provenance calculation_provenance
 FROM v_shots_source s
 LEFT JOIN derived_metric_selection p ON p.shot_id=s.shot_id
 LEFT JOIN shot_derived_metrics d ON d.result_id=p.result_id
 LEFT JOIN calculation_runs r ON r.run_id=d.run_id;
CREATE VIEW v_session_shots AS
 SELECT a.session_id,a.ordinal,a.legacy_key,a.shot_id,a.captured,a.target,a.success,a.excluded,
 s.deleted_at,r.report_id,{','.join('r.' + c for c, _, _ in SOURCE_FIELDS.values())},
 f.result_id flight_result_id,f.carry_distance_yd model_carry_distance_yd,
 f.total_distance_yd model_total_distance_yd,f.flight_shape,
 p.result_id putting_result_id,p.estimated_distance_ft,p.distance_error_ft,p.stimp_ft
 FROM session_attempts a JOIN sessions s ON s.id=a.session_id
 JOIN shot_source_metrics r ON r.observation_id=a.observation_id
 LEFT JOIN attempt_derived_results af ON af.session_id=a.session_id AND af.ordinal=a.ordinal AND af.model_family='flight'
 LEFT JOIN shot_derived_metrics f ON f.result_id=af.result_id
 LEFT JOIN attempt_derived_results ap ON ap.session_id=a.session_id AND ap.ordinal=a.ordinal AND ap.model_family='putting'
 LEFT JOIN shot_derived_metrics p ON p.result_id=ap.result_id;
"""
# Source identity is relinked once during receipt/practice reconciliation; numerical values cannot change.
DDL += f"""
CREATE TRIGGER source_values_immutable BEFORE UPDATE ON shot_source_metrics
 WHEN {' OR '.join('OLD.' + c + ' IS NOT NEW.' + c for c in ['report_id', 'observation_id', 'normalization_revision', 'created_at'] + [c for c, _, _ in SOURCE_FIELDS.values()])}
 BEGIN SELECT RAISE(ABORT,'Source report values are immutable'); END;
CREATE TRIGGER derived_values_immutable BEFORE UPDATE ON shot_derived_metrics
 BEGIN SELECT RAISE(ABORT,'Derived results are immutable; append a new version'); END;
CREATE TRIGGER run_values_immutable BEFORE UPDATE ON calculation_runs
 BEGIN SELECT RAISE(ABORT,'Calculation specifications are immutable'); END;
CREATE TRIGGER trajectory_values_immutable BEFORE UPDATE ON shot_trajectories
 BEGIN SELECT RAISE(ABORT,'Saved trajectories are immutable'); END;
CREATE TRIGGER quality_values_immutable BEFORE UPDATE ON source_metric_quality
 BEGIN SELECT RAISE(ABORT,'Source quality evidence is immutable'); END;
CREATE TRIGGER calculation_inputs_immutable BEFORE UPDATE ON calculation_inputs
 BEGIN SELECT RAISE(ABORT,'Calculation dependencies are immutable'); END;
"""


def select_source(connection, shot_id):
    """Prefer the shot's exact accepted receipt, then documented practice/legacy order.

    No field-level coalescing or averaging of competing reports. Ties with conflicting
    overlapping values remain unselected rather than depending on incidental row order.
    """
    policy = 'exact_receipt_then_practice_then_legacy_v1'
    existing = connection.execute(
        'SELECT policy FROM shot_primary_source WHERE shot_id=?', (shot_id,)
    ).fetchone()
    if existing and existing['policy'] != policy:
        return  # Future manual selections are not replaced by automatic reconciliation.
    rows = connection.execute(
        '''SELECT r.*,o.provenance,o.event_id,s.event_id original_event
        FROM shot_source_metrics r JOIN observations o ON o.id=r.observation_id
        JOIN shots s ON s.id=r.shot_id WHERE r.shot_id=?''',
        (shot_id,),
    ).fetchall()
    if not rows:
        return
    rank = {'live_capture': 1, 'practice_measurements': 2, 'legacy_practice': 3, 'legacy_csv': 4}

    def priority(row):
        return (
            0
            if row['event_id'] == row['original_event'] and row['provenance'] != 'legacy_csv'
            else rank.get(row['provenance'], 5)
        )

    best = min(priority(r) for r in rows)
    candidates = [r for r in rows if priority(r) == best]
    for column, _, _ in SOURCE_FIELDS.values():
        values = [r[column] for r in candidates if r[column] is not None]
        if values and any(
            not math.isclose(v, values[0], rel_tol=1e-9, abs_tol=1e-9) for v in values
        ):
            connection.execute(
                'DELETE FROM shot_primary_source WHERE shot_id=? AND policy=?', (shot_id, policy)
            )
            return
    chosen = min(candidates, key=lambda r: r['report_id'])
    connection.execute(
        'INSERT INTO shot_primary_source VALUES(?,?,?,?) ON CONFLICT(shot_id) DO UPDATE SET report_id=excluded.report_id,policy=excluded.policy,selected_at=excluded.selected_at',
        (shot_id, chosen['report_id'], policy, timestamp()),
    )


def write_source(connection, observation_id):
    observation = connection.execute(
        'SELECT * FROM observations WHERE id=?', (observation_id,)
    ).fetchone()
    report_id = identity('source:' + observation_id)
    existing = connection.execute(
        'SELECT shot_id FROM shot_source_metrics WHERE report_id=?', (report_id,)
    ).fetchone()
    if existing:
        if existing['shot_id'] != observation['shot_id']:
            connection.execute('DELETE FROM shot_primary_source WHERE report_id=?', (report_id,))
            connection.execute(
                'UPDATE shot_source_metrics SET shot_id=? WHERE report_id=?',
                (observation['shot_id'], report_id),
            )
        if observation['shot_id']:
            select_source(connection, observation['shot_id'])
        return report_id
    metrics = {}
    for metric in connection.execute(
        'SELECT * FROM metric_values WHERE observation_id=?', (observation_id,)
    ):
        if metric['metric_key'] in metrics:
            raise ValueError(
                'Multiple definition versions need explicit source normalization selection.'
            )
        metrics[metric['metric_key']] = metric
    raw = json.loads(
        connection.execute(
            'SELECT raw_json FROM ingest_events WHERE id=?', (observation['event_id'],)
        ).fetchone()[0]
    )
    values = {}
    quality = []
    for field, (column, key, factor) in SOURCE_FIELDS.items():
        metric = metrics.get(key)
        availability = metric['availability'] if metric else 'not_supplied'
        if field not in raw.get('vals', {}) and availability == 'unavailable':
            availability = 'not_supplied'
        values[column] = (
            metric['real_value'] / factor if metric and availability == 'available' else None
        )
        if metric and availability == 'available':
            original = json.loads(metric['source_json'])
            unit = (
                'mph'
                if factor == 0.44704
                else 'yd'
                if factor == 0.9144
                else 'ft'
                if factor == 0.3048
                else 'ratio'
                if field == 'smash_factor'
                else 's'
                if field == 'hang_time'
                else 'rpm'
                if 'spin' in field and field != 'spin_axis'
                else 'deg'
            )
            if (
                finite(original)
                and metric['source_unit'] == unit
                and math.isclose(
                    original * factor, metric['real_value'], rel_tol=1e-12, abs_tol=1e-12
                )
            ):
                values[column] = float(
                    original
                )  # Avoid introducing a binary round-trip difference.
        quality.append(
            (
                report_id,
                column,
                availability,
                field,
                metric['source_unit'] if metric else None,
                metric['method'] if metric else None,
                metric['variant'] if metric else None,
            )
        )
    columns = [
        'report_id',
        'observation_id',
        'shot_id',
        'normalization_revision',
        'created_at',
    ] + list(values)
    connection.execute(
        f"INSERT INTO shot_source_metrics({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        [
            report_id,
            observation_id,
            observation['shot_id'],
            'canonical_to_golf_units_v1',
            timestamp(),
        ]
        + list(values.values()),
    )
    connection.executemany('INSERT INTO source_metric_quality VALUES(?,?,?,?,?,?,?)', quality)
    if observation['shot_id']:
        select_source(connection, observation['shot_id'])
    return report_id


def write_result(
    connection,
    shot_id,
    report_id,
    family,
    context_id,
    model_version,
    parameters,
    artifact,
    values,
    *,
    provenance,
    code_hash=None,
    select=False,
):
    """Append/retry safely; publishing analytical selection is explicit.

    artifact is immutable evidence, scalar values are the analytical authority.
    Legacy lineage is labeled honestly rather than inventing historic code hashes.
    """
    if set(values) - set(DERIVED_COLUMNS):
        raise ValueError('Unknown derived metric column.')
    if any(v is not None and not finite(v) for v in values.values()):
        raise ValueError('Derived metrics must be finite numbers or unavailable.')
    spec = dict(
        family=family,
        version=model_version,
        parameters=parameters,
        provenance=provenance,
        code_hash=code_hash,
        output_schema_revision='wide_v1',
    )
    run_id = identity('run:' + encoded(spec))
    fingerprint = hashlib.sha256(
        encoded(
            dict(report_id=report_id, context=context_id, artifact=artifact, values=values)
        ).encode()
    ).hexdigest()
    result_id = identity('result:' + encoded([shot_id, run_id, context_id, fingerprint]))
    status = artifact.get('status', 'ready')
    if status not in ('ready', 'unavailable', 'error'):
        raise ValueError('Invalid calculation status.')
    connection.execute(
        'INSERT OR IGNORE INTO calculation_runs VALUES(?,?,?,?,?,?,?,?,?)',
        (
            run_id,
            family,
            model_version,
            'wide_v1',
            provenance,
            code_hash,
            encoded(parameters),
            timestamp(),
            'complete',
        ),
    )
    columns = (
        [
            'result_id',
            'shot_id',
            'run_id',
            'model_family',
            'context_id',
            'input_fingerprint',
            'status',
            'reason',
            'flight_shape',
        ]
        + list(DERIVED_COLUMNS)
        + ['artifact_json', 'created_at']
    )
    connection.execute(
        f"INSERT OR IGNORE INTO shot_derived_metrics({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        [
            result_id,
            shot_id,
            run_id,
            family,
            context_id,
            fingerprint,
            status,
            artifact.get('reason'),
            artifact.get('shape'),
        ]
        + [values.get(k) for k in DERIVED_COLUMNS]
        + [encoded(artifact), timestamp()],
    )
    connection.execute(
        'INSERT OR IGNORE INTO calculation_inputs VALUES(?,?,?)', (result_id, shot_id, report_id)
    )
    if artifact.get('trajectory') is not None:
        points = artifact['trajectory']
        connection.execute(
            'INSERT OR IGNORE INTO shot_trajectories VALUES(?,?,?,?)',
            (
                result_id,
                't seconds; x/y/z meters, +X forward/+Y right/+Z up',
                len(points),
                encoded(points),
            ),
        )
    if select:
        connection.execute(
            'INSERT INTO derived_metric_selection VALUES(?,?,?,?,?) ON CONFLICT(shot_id,model_family,context_id) DO UPDATE SET result_id=excluded.result_id,selected_at=excluded.selected_at',
            (shot_id, family, context_id, result_id, timestamp()),
        )
    return result_id


def save_attempt_results(connection, session, attempt, ordinal, *, legacy=False):
    link = connection.execute(
        'SELECT * FROM session_attempts WHERE session_id=? AND ordinal=?', (session['id'], ordinal)
    ).fetchone()
    report_id = identity('source:' + link['observation_id'])
    context_id = identity('attempt:' + session['id'] + ':' + str(ordinal))
    specifications = []
    flight = attempt.get('flight')
    if flight:
        m = flight.get('metrics', {})
        carry, total = flight.get('carry_point_yd', {}), flight.get('total_point_yd', {})
        values = dict(
            carry_distance_yd=m.get('carry_yd'),
            total_distance_yd=m.get('total_yd'),
            carry_forward_yd=carry.get('forward'),
            carry_right_yd=carry.get('right'),
            total_forward_yd=total.get('forward'),
            total_right_yd=total.get('right'),
            offline_distance_yd=m.get('offline_yd'),
            apex_ft=m.get('apex_ft'),
            descent_angle_deg=m.get('descent_deg'),
            hang_time_s=m.get('hang_time_s'),
        )
        specs = dict(
            assumptions=flight.get('assumptions'),
            inputs=flight.get('inputs'),
            handedness=flight.get('handedness'),
            endpoint_method=flight.get('endpoint_method'),
        )
        specifications.append(
            ('flight', flight.get('model', 'legacy_unknown'), specs, flight, values)
        )
    if 'estimated_distance_ft' in attempt:
        values = {
            k: attempt.get(k)
            for k in (
                'estimated_distance_ft',
                'target_distance_ft',
                'distance_error_ft',
                'stimp_ft',
            )
        }
        model = attempt.get('distance_model_id', 'legacy_unknown')
        specifications.append(
            (
                'putting',
                model,
                dict(model=session.get('distance_model'), stimp_ft=attempt.get('stimp_ft')),
                dict(status='ready', **values),
                values,
            )
        )
    for family, version, parameters, artifact, values in specifications:
        # Existing attempt pins remain immutable even after analytical publication changes.
        old = connection.execute(
            'SELECT result_id FROM attempt_derived_results WHERE session_id=? AND ordinal=? AND model_family=?',
            (session['id'], ordinal, family),
        ).fetchone()
        if old:
            continue
        result = write_result(
            connection,
            link['shot_id'],
            report_id,
            family,
            context_id,
            version,
            parameters,
            artifact,
            values,
            provenance='legacy_saved_outcome_incomplete_lineage'
            if legacy
            else 'saved_attempt_snapshot',
            select=True,
        )
        connection.execute(
            'INSERT INTO attempt_derived_results VALUES(?,?,?,?,?,?)',
            (session['id'], ordinal, link['shot_id'], family, context_id, result),
        )


def source_features(connection, shot_id):
    selected = connection.execute(
        "SELECT r.provenance FROM derived_metric_selection s JOIN shot_derived_metrics d USING(result_id) JOIN calculation_runs r USING(run_id) WHERE s.shot_id=? AND s.model_family='source_features' AND s.context_id='shot'",
        (shot_id,),
    ).fetchone()
    if selected and selected['provenance'] == 'recalculation_batch_v1':
        return
    row = connection.execute(
        'SELECT r.* FROM shot_primary_source p JOIN shot_source_metrics r ON r.report_id=p.report_id WHERE p.shot_id=?',
        (shot_id,),
    ).fetchone()
    if not row:
        return
    ball, club, offline, total, carry = (
        row[k]
        for k in (
            'ball_speed_mph',
            'club_head_speed_mph',
            'ball_offline_yd',
            'total_distance_yd',
            'carry_distance_yd',
        )
    )
    values = dict(
        absolute_offline_yd=abs(offline) if offline is not None else None,
        calculated_smash_factor=ball / club
        if ball is not None and club is not None and club > 0
        else None,
        source_rollout_yd=total - carry if total is not None and carry is not None else None,
    )
    write_result(
        connection,
        shot_id,
        row['report_id'],
        'source_features',
        'shot',
        'source_features_v1',
        dict(
            smash='ball speed / positive club speed',
            rollout='source total minus source carry; signed difference',
        ),
        dict(status='ready'),
        values,
        provenance='recomputed_from_selected_source',
        select=True,
    )


def backfill(connection):
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


def hydrate_session(connection, data):
    """Preserve the browser DTO, reading existing shot keys from named source columns.

    Live/review results stay pinned to attempt results, independent of the selected
    analytical methodology. Legacy snapshots supply non-scalar artifact fields.
    """
    rows = connection.execute(
        '''SELECT a.ordinal,r.* FROM session_attempts a
        JOIN shot_source_metrics r ON r.observation_id=a.observation_id
        WHERE a.session_id=? ORDER BY a.ordinal''',
        (data['id'],),
    ).fetchall()
    # One query for every attempt's pinned results (at most one per family per attempt).
    derived = {}
    for result in connection.execute(
        '''SELECT p.ordinal pinned_ordinal, t.points_json pinned_trajectory, d.*
        FROM attempt_derived_results p
        JOIN shot_derived_metrics d ON d.result_id=p.result_id
        LEFT JOIN shot_trajectories t ON t.result_id=d.result_id
        WHERE p.session_id=? ORDER BY p.ordinal, p.model_family''',
        (data['id'],),
    ):
        derived.setdefault(result['pinned_ordinal'], []).append(result)
    for row in rows:
        attempt = data['shots'][row['ordinal'] - 1]
        for field, (column, _, _) in SOURCE_FIELDS.items():
            if field in attempt['vals'] and row[column] is not None:
                attempt['vals'][field] = row[column]
        for result in derived.get(row['ordinal'], []):
            if result['model_family'] == 'putting':
                for column in (
                    'estimated_distance_ft',
                    'target_distance_ft',
                    'distance_error_ft',
                    'stimp_ft',
                ):
                    if column in attempt:
                        attempt[column] = result[column]
            elif result['model_family'] == 'flight':
                flight = json.loads(result['artifact_json'])
                if 'metrics' in flight:
                    for key, column in {
                        'carry_yd': 'carry_distance_yd',
                        'total_yd': 'total_distance_yd',
                        'offline_yd': 'offline_distance_yd',
                        'apex_ft': 'apex_ft',
                        'descent_deg': 'descent_angle_deg',
                        'hang_time_s': 'hang_time_s',
                    }.items():
                        if key in flight['metrics']:
                            flight['metrics'][key] = result[column]
                if 'shape' in flight:
                    flight['shape'] = result['flight_shape']
                for key, prefix in (('carry_point_yd', 'carry'), ('total_point_yd', 'total')):
                    if key in flight:
                        flight[key] = dict(
                            forward=result[prefix + '_forward_yd'],
                            right=result[prefix + '_right_yd'],
                        )
                if result['pinned_trajectory'] is not None:
                    flight['trajectory'] = json.loads(result['pinned_trajectory'])
                attempt['flight'] = flight
    return data


def evidence_manifest(connection):
    """Exact typed-row reconciliation of original evidence and saved game/drill state."""
    result = {}
    for table in (
        'shots',
        'observations',
        'metric_values',
        'sessions',
        'session_attempts',
        'ingest_events',
        'import_files',
        'inclusion_decisions',
        'delivery_events',
        'audit_events',
        'sources',
        'capture_streams',
    ):
        digest = hashlib.sha256()
        count = 0
        for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid'):
            values = [
                dict(blob_hex=value.hex()) if isinstance(value, bytes) else value for value in row
            ]
            digest.update((encoded(values) + '\n').encode())
            count += 1
        result[table] = dict(rows=count, sha256=digest.hexdigest())
    return result
