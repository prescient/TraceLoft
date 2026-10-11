"""Staged, restartable calculations. Publication never rewrites historical attempt pins."""

import csv
import hashlib
import io
import json
import uuid
from pathlib import Path
from importlib.metadata import distribution
from shot_schema import SOURCE_FIELDS, DERIVED_COLUMNS, identity, encoded, timestamp, write_result
from domain_schema import active_user, read_session
from analysis_schema import read_rows, report, save_collection, QUERY

DDL = '''
CREATE TABLE recalculation_batches(batch_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(user_id),
 model_family TEXT NOT NULL,model_version TEXT NOT NULL,code_hash TEXT NOT NULL,parameters_json TEXT NOT NULL,
 created_at TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('staging','complete','error','published','cancelled')));
CREATE TABLE recalculation_inputs(batch_id TEXT NOT NULL REFERENCES recalculation_batches(batch_id), ordinal INTEGER NOT NULL,
 shot_id TEXT NOT NULL REFERENCES shots(id),report_id TEXT NOT NULL,calculation_context_id TEXT NOT NULL,
 session_id TEXT NOT NULL,attempt_ordinal INTEGER NOT NULL,equipment_context_id TEXT REFERENCES shot_contexts(context_id),
 excluded INTEGER NOT NULL,removed INTEGER NOT NULL,handedness TEXT NOT NULL,stimp_ft REAL,target_distance_ft REAL,
 putting_model TEXT,PRIMARY KEY(batch_id,ordinal),
 FOREIGN KEY(report_id,shot_id) REFERENCES shot_source_metrics(report_id,shot_id),
 FOREIGN KEY(equipment_context_id,session_id,attempt_ordinal,shot_id) REFERENCES shot_contexts(context_id,session_id,ordinal,shot_id),
 FOREIGN KEY(session_id,attempt_ordinal,shot_id) REFERENCES session_attempts(session_id,ordinal,shot_id));
CREATE TABLE recalculation_outputs(batch_id TEXT NOT NULL,ordinal INTEGER NOT NULL,result_id TEXT NOT NULL REFERENCES shot_derived_metrics(result_id),
 PRIMARY KEY(batch_id,ordinal),FOREIGN KEY(batch_id,ordinal) REFERENCES recalculation_inputs(batch_id,ordinal));
CREATE TABLE calculation_lineage(result_id TEXT NOT NULL REFERENCES shot_derived_metrics(result_id),
 batch_id TEXT NOT NULL,ordinal INTEGER NOT NULL,PRIMARY KEY(result_id,batch_id,ordinal),
 FOREIGN KEY(batch_id,ordinal) REFERENCES recalculation_inputs(batch_id,ordinal));
CREATE TABLE calculation_attempt_contexts(session_id TEXT NOT NULL,ordinal INTEGER NOT NULL,model_family TEXT NOT NULL,
 context_id TEXT NOT NULL,PRIMARY KEY(session_id,ordinal,model_family),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal));
CREATE TABLE calculation_publications(publication_id TEXT PRIMARY KEY,batch_id TEXT NOT NULL REFERENCES recalculation_batches(batch_id),published_at TEXT NOT NULL);
CREATE TABLE calculation_publication_items(publication_id TEXT NOT NULL REFERENCES calculation_publications(publication_id),
 ordinal INTEGER NOT NULL,previous_result_id TEXT REFERENCES shot_derived_metrics(result_id),result_id TEXT NOT NULL REFERENCES shot_derived_metrics(result_id),
 PRIMARY KEY(publication_id,ordinal));
CREATE TRIGGER batch_spec_immutable BEFORE UPDATE ON recalculation_batches
 WHEN OLD.batch_id IS NOT NEW.batch_id OR OLD.user_id IS NOT NEW.user_id OR OLD.model_family IS NOT NEW.model_family
 OR OLD.model_version IS NOT NEW.model_version OR OLD.code_hash IS NOT NEW.code_hash OR OLD.parameters_json IS NOT NEW.parameters_json
 OR OLD.created_at IS NOT NEW.created_at BEGIN SELECT RAISE(ABORT,'Batch specification is immutable'); END;
CREATE TRIGGER batch_inputs_immutable BEFORE UPDATE ON recalculation_inputs BEGIN SELECT RAISE(ABORT,'Batch inputs are immutable'); END;
CREATE TRIGGER batch_outputs_immutable BEFORE UPDATE ON recalculation_outputs BEGIN SELECT RAISE(ABORT,'Batch outputs are immutable'); END;
CREATE TRIGGER lineage_immutable BEFORE UPDATE ON calculation_lineage BEGIN SELECT RAISE(ABORT,'Lineage is immutable'); END;
CREATE TRIGGER batch_output_scope BEFORE INSERT ON recalculation_outputs BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM recalculation_inputs i JOIN recalculation_batches b USING(batch_id)
 JOIN shot_derived_metrics d ON d.shot_id=i.shot_id AND d.model_family=b.model_family AND d.context_id=i.calculation_context_id
 JOIN calculation_inputs source ON source.result_id=d.result_id AND source.report_id=i.report_id
 WHERE i.batch_id=NEW.batch_id AND i.ordinal=NEW.ordinal AND d.result_id=NEW.result_id)
 THEN RAISE(ABORT,'Calculation output scope mismatch') END; END;
CREATE VIEW v_calculation_history AS SELECT d.*,r.model_version,r.code_hash,r.parameters_json,r.provenance,
 l.batch_id,i.session_id,i.attempt_ordinal,i.report_id,i.equipment_context_id,i.handedness,i.stimp_ft input_stimp_ft,
 i.target_distance_ft input_target_distance_ft,i.putting_model,
 CASE WHEN selected.result_id=d.result_id THEN 1 ELSE 0 END selected_for_analysis
 FROM shot_derived_metrics d JOIN calculation_runs r USING(run_id)
 LEFT JOIN calculation_lineage l USING(result_id) LEFT JOIN recalculation_inputs i USING(batch_id,ordinal)
 LEFT JOIN derived_metric_selection selected ON selected.result_id=d.result_id;
'''

# Everyday wide view: one row per session attempt, named source and selected-derived columns.
# Historical outcomes remain in v_session_shots, which uses the immutable attempt pins.
DDL += (
    '''CREATE VIEW v_session_current_metrics AS SELECT rows.session_id,rows.ordinal,rows.legacy_key,rows.shot_id,
 rows.user_id,users.display_name golfer,rows.captured,rows.drill,rows.deleted_at,rows.simulated,
 rows.bag_name,rows.club_label,rows.configuration_id,rows.context_id,rows.excluded,rows.removed,rows.swing_label,
 rows.report_id,'''
    + ','.join('rows.' + col for col, _, _ in SOURCE_FIELDS.values())
    + ''',
 rows.flight_result_id,rows.flight_model_version,rows.flight_status,
 rows.model_carry_distance_yd,rows.model_total_distance_yd,rows.model_ball_offline_yd,
 rows.model_ball_apex_ft,rows.model_ball_descent_angle_deg,rows.model_hang_time_s,
 rows.putting_result_id,rows.putting_model_version,rows.estimated_distance_ft,rows.distance_error_ft,
 rows.features_result_id,rows.calculated_smash_factor,rows.source_rollout_yd
 FROM ('''
    + QUERY.split(' WHERE o.user_id=? AND s.deleted_at IS NULL')[0]
    + ''') rows JOIN users USING(user_id);'''
)


def specification(family, putting_model):
    if family not in ('flight', 'putting', 'source_features'):
        raise ValueError('Choose flight, putting or source features.')
    file = Path(__file__).with_name(
        {
            'flight': 'flight_model.py',
            'putting': 'putting_distance.py',
            'source_features': 'shot_schema.py',
        }[family]
    )
    pieces = [Path(__file__).read_bytes(), file.read_bytes()]
    package = None
    if family == 'flight':
        from flight_model import MODEL, ASSUMPTIONS

        version = MODEL
        params = dict(assumptions=ASSUMPTIONS)
        try:
            dist = distribution('opengolfcoach')
            package = dist.version
            # Hash the installed implementation, including its native binary, not just its version label.
            for entry in sorted(dist.files or [], key=str):
                if str(entry).endswith(('.py', '.pyd', '.dll', '.so')) and 'opengolfcoach' in str(
                    entry
                ):
                    pieces.append(str(entry).encode() + dist.locate_file(entry).read_bytes())
        except Exception:
            package = 'unavailable'
        params['package_version'] = package
    elif family == 'putting':
        from putting_distance import BASELINE_ID, MODEL_ID

        if putting_model not in ('saved', BASELINE_ID, MODEL_ID):
            raise ValueError('Choose a supported putting method.')
        version = 'putting-adapter-v1/' + putting_model
        params = dict(
            putting_model=putting_model,
            stimp='frozen attempt/session value',
            target='frozen attempt target',
        )
    else:
        version = 'source_features_v1'
        params = dict(
            smash='ball speed / positive club speed',
            rollout='source total minus carry; signed',
            offline='absolute source offline',
        )
    return version, hashlib.sha256(b''.join(pieces)).hexdigest(), params


def stage(store, family, filters, putting_model='saved'):
    version, code_hash, params = specification(family, putting_model)
    bid = uuid.uuid4().hex
    # Plan from a committed snapshot without the writer lock, which the event loop needs for
    # shot intake. If anything committed meanwhile, re-plan inside the write transaction so
    # the frozen inputs always match the database at the moment the batch is recorded.
    before = store.committed_version()
    with store.reading() as snapshot_connection:
        uid, inputs = plan_inputs(snapshot_connection, family, filters, putting_model)
    with store.transaction():
        c = store.connection
        if store.committed_version() != before:
            uid, inputs = plan_inputs(c, family, filters, putting_model)
        params['filters'] = filters
        c.execute(
            'INSERT INTO recalculation_batches VALUES(?,?,?,?,?,?,?,?)',
            (bid, uid, family, version, code_hash, encoded(params), timestamp(), 'staging'),
        )
        for item in inputs:
            c.execute(
                'INSERT INTO recalculation_inputs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (bid, *item),
            )
        store.audit(bid, 'stage_recalculation', dict(family=family, count=len(inputs)))
    return resume(store, bid)


def plan_inputs(c, family, filters, putting_model):
    """Read-only selection of frozen calculation inputs; returns (user_id, input rows)."""
    uid = active_user(c)
    selected = report(c, filters, uid)['rows']
    keys = {(r['session_id'], r['key']) for r in selected}
    rows = [r for r in read_rows(c, uid) if (r['session_id'], r['legacy_key']) in keys]
    if family == 'putting':
        rows = [
            r
            for r in rows
            if r['practice_type'] == 'putting'
            or c.execute(
                "SELECT 1 FROM attempt_derived_results WHERE session_id=? AND ordinal=? AND model_family='putting'",
                (r['session_id'], r['ordinal']),
            ).fetchone()
        ]
    if not rows:
        raise ValueError('No matching shots for this calculation family.')
    seen = set()
    sessions = {}
    inputs = []
    for r in rows:
        pin = c.execute(
            'SELECT context_id FROM attempt_derived_results WHERE session_id=? AND ordinal=? AND model_family=?',
            (r['session_id'], r['ordinal'], family),
        ).fetchone()
        context = (
            'shot'
            if family == 'source_features'
            else pin[0]
            if pin
            else identity('attempt:' + r['session_id'] + ':' + str(r['ordinal']))
        )
        key = (r['shot_id'], context)
        if key in seen:
            continue
        seen.add(key)
        if r['session_id'] not in sessions:
            sessions[r['session_id']] = read_session(c, r['session_id'])
        data = sessions[r['session_id']]
        shot = data['shots'][r['ordinal'] - 1]
        stimp = shot.get('stimp_ft', data.get('stimp'))
        target = shot.get('target_distance_ft')
        model = (
            shot.get('distance_model_id', data.get('distance_model', {}).get('id'))
            if putting_model == 'saved'
            else putting_model
        )
        # Each result names its exact attempt report; source features use the selected physical-shot report.
        source = (
            c.execute(
                'SELECT report_id FROM shot_primary_source WHERE shot_id=?', (r['shot_id'],)
            ).fetchone()
            if family == 'source_features'
            else None
        )
        if family == 'source_features' and not source:
            raise ValueError('A physical shot has no unambiguous source report.')
        inputs.append(
            (
                len(seen),
                r['shot_id'],
                source[0] if source else r['report_id'],
                context,
                r['session_id'],
                r['ordinal'],
                r['context_id'],
                r['excluded'],
                r['removed'],
                data.get('handedness', 'right_handed'),
                stimp,
                target,
                model,
            )
        )
    return uid, inputs


def calculate(source, item, family):
    vals = {k: source[col] for k, (col, _, _) in SOURCE_FIELDS.items()}
    if family == 'flight':
        from flight_model import predict

        artifact = predict(vals, item['handedness'])
        m = artifact.get('metrics', {})
        carry = artifact.get('carry_point_yd', {})
        total = artifact.get('total_point_yd', {})
        return artifact, dict(
            carry_distance_yd=m.get('carry_yd'),
            total_distance_yd=m.get('total_yd'),
            offline_distance_yd=m.get('offline_yd'),
            apex_ft=m.get('apex_ft'),
            descent_angle_deg=m.get('descent_deg'),
            hang_time_s=m.get('hang_time_s'),
            carry_forward_yd=carry.get('forward'),
            carry_right_yd=carry.get('right'),
            total_forward_yd=total.get('forward'),
            total_right_yd=total.get('right'),
        )
    if family == 'putting':
        from putting_distance import distance_ft

        try:
            distance = distance_ft(vals['ball_speed'], item['stimp_ft'], item['putting_model'])
        except (ValueError, TypeError):
            return dict(
                status='unavailable',
                reason='Needs valid speed, frozen Stimp and a supported putting model.',
            ), {}
        target = item['target_distance_ft']
        values = dict(
            estimated_distance_ft=distance,
            stimp_ft=item['stimp_ft'],
            target_distance_ft=target,
            distance_error_ft=distance - target if target is not None else None,
        )
        return dict(status='ready', model=item['putting_model']), values
    ball, club, offline, total, carry = [
        vals[k] for k in ('ball_speed', 'club_speed', 'offline', 'total', 'carry')
    ]
    values = dict(
        absolute_offline_yd=abs(offline) if offline is not None else None,
        calculated_smash_factor=ball / club
        if ball is not None and club is not None and club > 0
        else None,
        source_rollout_yd=total - carry if total is not None and carry is not None else None,
    )
    return (
        dict(status='ready')
        if any(v is not None for v in values.values())
        else dict(status='unavailable', reason='No valid source inputs for comparisons.')
    ), values


def owned(c, bid):
    batch = c.execute('SELECT * FROM recalculation_batches WHERE batch_id=?', (bid,)).fetchone()
    if not batch or batch['user_id'] != active_user(c):
        raise ValueError('Calculation batch not found for this golfer.')
    return dict(batch)


def resume(store, bid):
    with store.lock:
        c = store.connection
        b = owned(c, bid)
        if b['status'] != 'staging':
            return snapshot(c, bid)
        version, code_hash, _ = specification(
            b['model_family'], json.loads(b['parameters_json']).get('putting_model', 'saved')
        )
        if version != b['model_version'] or code_hash != b['code_hash']:
            raise ValueError(
                'Calculation code changed. Stage a new batch rather than resuming this specification.'
            )
        items = [
            dict(r)
            for r in c.execute(
                'SELECT i.* FROM recalculation_inputs i LEFT JOIN recalculation_outputs o USING(batch_id,ordinal) WHERE i.batch_id=? AND o.result_id IS NULL ORDER BY ordinal',
                (bid,),
            )
        ]
    # No shared-state lock while the external flight model works. Each output commits independently.
    for item in items:
        with store.lock:
            source = dict(
                c.execute(
                    'SELECT * FROM shot_source_metrics WHERE report_id=?', (item['report_id'],)
                ).fetchone()
            )
        try:
            artifact, values = calculate(source, item, b['model_family'])
        except Exception as exc:
            artifact, values = (
                dict(status='error', reason='Calculation failed: ' + type(exc).__name__),
                {},
            )
        with store.transaction():
            if owned(c, bid)['status'] != 'staging':
                return snapshot(c, bid)
            params = json.loads(b['parameters_json'])
            params['input_context'] = {
                k: item[k]
                for k in ('handedness', 'stimp_ft', 'target_distance_ft', 'putting_model')
            }
            rid = write_result(
                c,
                item['shot_id'],
                item['report_id'],
                b['model_family'],
                item['calculation_context_id'],
                b['model_version'],
                params,
                artifact,
                values,
                provenance='recalculation_batch_v1',
                code_hash=b['code_hash'],
            )
            c.execute(
                'INSERT OR IGNORE INTO recalculation_outputs VALUES(?,?,?)',
                (bid, item['ordinal'], rid),
            )
            c.execute(
                'INSERT OR IGNORE INTO calculation_lineage VALUES(?,?,?)',
                (rid, bid, item['ordinal']),
            )
            if b['model_family'] != 'source_features':
                c.execute(
                    'INSERT OR IGNORE INTO calculation_attempt_contexts VALUES(?,?,?,?)',
                    (
                        item['session_id'],
                        item['attempt_ordinal'],
                        b['model_family'],
                        item['calculation_context_id'],
                    ),
                )
    with store.transaction():
        failures = c.execute(
            "SELECT count(*) FROM recalculation_outputs o JOIN shot_derived_metrics d USING(result_id) WHERE batch_id=? AND d.status='error'",
            (bid,),
        ).fetchone()[0]
        c.execute(
            "UPDATE recalculation_batches SET status=? WHERE batch_id=? AND status='staging'",
            ('error' if failures else 'complete', bid),
        )
        return snapshot(c, bid)


def current_state(c, b, item):
    r = c.execute(
        '''SELECT a.shot_id,a.observation_id,a.excluded,s.deleted_at,eq.context_id,
       outcomes.removed FROM session_attempts a JOIN sessions s ON s.id=a.session_id
       LEFT JOIN v_session_equipment eq ON eq.session_id=a.session_id AND eq.ordinal=a.ordinal
       JOIN v_attempt_outcomes outcomes ON outcomes.session_id=a.session_id AND outcomes.ordinal=a.ordinal
       WHERE a.session_id=? AND a.ordinal=?''',
        (item['session_id'], item['attempt_ordinal']),
    ).fetchone()
    selected = c.execute(
        'SELECT result_id FROM derived_metric_selection WHERE shot_id=? AND model_family=? AND context_id=?',
        (item['shot_id'], b['model_family'], item['calculation_context_id']),
    ).fetchone()
    source = (
        c.execute(
            'SELECT report_id FROM shot_primary_source WHERE shot_id=?', (item['shot_id'],)
        ).fetchone()
        if b['model_family'] == 'source_features'
        else None
    )
    valid = bool(
        r
        and r['shot_id'] == item['shot_id']
        and not r['deleted_at']
        and r['context_id'] == item['equipment_context_id']
        and r['excluded'] == item['excluded']
        and r['removed'] == item['removed']
    )
    if b['model_family'] == 'source_features':
        valid = valid and bool(source and source[0] == item['report_id'])
    else:
        valid = valid and bool(
            c.execute(
                'SELECT 1 FROM shot_source_metrics WHERE report_id=? AND observation_id=?',
                (item['report_id'], r['observation_id'] if r else None),
            ).fetchone()
        )
    return valid, selected[0] if selected else None


def snapshot(c, bid):
    b = owned(c, bid)
    items = [
        dict(r)
        for r in c.execute(
            'SELECT i.*,o.result_id,d.status,d.reason FROM recalculation_inputs i LEFT JOIN recalculation_outputs o USING(batch_id,ordinal) LEFT JOIN shot_derived_metrics d USING(result_id) WHERE i.batch_id=? ORDER BY ordinal',
            (bid,),
        )
    ]
    counts = {k: sum(i['status'] == k for i in items) for k in ('ready', 'unavailable', 'error')}
    stale = 0
    diffs = []
    token = []
    for i in items:
        valid, previous = current_state(c, b, i)
        stale += int(not valid)
        token.append([i['ordinal'], valid, previous])
        old = (
            c.execute(
                'SELECT * FROM shot_derived_metrics WHERE result_id=?', (previous,)
            ).fetchone()
            if previous
            else None
        )
        new = (
            c.execute(
                'SELECT * FROM shot_derived_metrics WHERE result_id=?', (i['result_id'],)
            ).fetchone()
            if i['result_id']
            else None
        )
        changed = {
            k: dict(before=old[k] if old else None, after=new[k] if new else None)
            for k in DERIVED_COLUMNS
            if (old[k] if old else None) != (new[k] if new else None)
        }
        diffs.append(
            dict(
                ordinal=i['ordinal'],
                shot_id=i['shot_id'],
                session_id=i['session_id'],
                report_id=i['report_id'],
                context_id=i['calculation_context_id'],
                previous_result_id=previous,
                result_id=i['result_id'],
                status=i['status'] or 'pending',
                reason=i['reason'],
                changes=changed,
            )
        )
    b.update(
        expected=len(items),
        processed=sum(counts.values()),
        coverage=counts,
        stale=stale,
        differences=diffs,
        selection_token=hashlib.sha256(encoded(token).encode()).hexdigest(),
        publishable=bool(
            items
            and counts['ready'] == len(items)
            and not stale
            and b['status'] in ('complete', 'published')
        ),
    )
    return b


def publish(store, bid, selection_token):
    with store.transaction():
        c = store.connection
        b = snapshot(c, bid)
        if not b['publishable']:
            raise ValueError(
                'Batch must have complete ready coverage and unchanged source/context/inclusion before publication.'
            )
        if selection_token != b['selection_token']:
            raise ValueError(
                'Selected versions changed. Refresh the calculation preview before publishing.'
            )
        if b['status'] == 'published' and all(
            i['previous_result_id'] == i['result_id'] for i in b['differences']
        ):
            return b
        pid = uuid.uuid4().hex
        c.execute('INSERT INTO calculation_publications VALUES(?,?,?)', (pid, bid, timestamp()))
        for i in b['differences']:
            c.execute(
                'INSERT INTO calculation_publication_items VALUES(?,?,?,?)',
                (pid, i['ordinal'], i['previous_result_id'], i['result_id']),
            )
            c.execute(
                'INSERT INTO derived_metric_selection VALUES(?,?,?,?,?) ON CONFLICT(shot_id,model_family,context_id) DO UPDATE SET result_id=excluded.result_id,selected_at=excluded.selected_at',
                (i['shot_id'], b['model_family'], i['context_id'], i['result_id'], timestamp()),
            )
        c.execute("UPDATE recalculation_batches SET status='published' WHERE batch_id=?", (bid,))
        for sid in {i['session_id'] for i in b['differences']}:
            save_collection(c, read_session(c, sid))
        store.audit(bid, 'publish_recalculation', dict(publication_id=pid, count=b['expected']))
        return snapshot(c, bid)


def history(c, shot_id):
    if not c.execute(
        'SELECT 1 FROM shot_owners WHERE shot_id=? AND user_id=?', (shot_id, active_user(c))
    ).fetchone():
        raise ValueError('Shot not found for this golfer.')
    return [
        dict(r)
        for r in c.execute(
            'SELECT * FROM v_calculation_history WHERE shot_id=? ORDER BY created_at,result_id',
            (shot_id,),
        )
    ]


def csv_history(c):
    cursor = c.execute(
        'SELECT h.* FROM v_calculation_history h JOIN shot_owners o USING(shot_id) WHERE o.user_id=? ORDER BY h.shot_id,h.created_at,h.result_id',
        (active_user(c),),
    )
    stream = io.StringIO(newline='')
    w = csv.writer(stream)
    w.writerow([d[0] for d in cursor.description])
    for r in cursor:
        w.writerow(
            [
                "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v
                for v in r
            ]
        )
    return '\ufeff' + stream.getvalue()


def cancel(store, bid):
    with store.transaction():
        b = owned(store.connection, bid)
        if b['status'] == 'published':
            raise ValueError(
                'A published batch cannot be cancelled. Review and select another version.'
            )
        store.connection.execute(
            "UPDATE recalculation_batches SET status='cancelled' WHERE batch_id=?", (bid,)
        )
        store.audit(bid, 'cancel_recalculation', {})
        return snapshot(store.connection, bid)
