"""SQL analytical reads and immutable collection cohorts (schema 4)."""

import hashlib
import json
from storage import encoded, identity, now
from analysis import METRICS, robust, build_report
from shot_schema import SOURCE_FIELDS
from domain_schema import active_user


QUERY = '''SELECT a.*,s.started,s.drill,s.revision,s.deleted_at,o.user_id,
 eq.bag_id,eq.bag_name,eq.club_id,eq.club_label,eq.context_id,eq.configuration_id,
 state.session_kind,state.practice_type,state.simulated, outcomes.removed,outcomes.swing_label,
 r.*,pin.context_id calculation_context,selected.result_id flight_result_id,d.artifact_json flight_json,d.status flight_status,
 d.carry_distance_yd model_carry_distance_yd,d.total_distance_yd model_total_distance_yd,d.offline_distance_yd model_ball_offline_yd,
 d.apex_ft model_ball_apex_ft,d.descent_angle_deg model_ball_descent_angle_deg,d.hang_time_s model_hang_time_s,
 d.carry_forward_yd,d.carry_right_yd,d.total_forward_yd,d.total_right_yd,
 features.calculated_smash_factor,features.source_rollout_yd,put.estimated_distance_ft,put.distance_error_ft,
 features.result_id features_result_id,put.result_id putting_result_id,
 flight_run.model_version flight_model_version,put_run.model_version putting_model_version,
 (SELECT text_value FROM session_fields f WHERE f.session_id=a.session_id AND f.path='/collection_kind') collection_kind,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/receipt_id') receipt_id
 FROM session_attempts a JOIN sessions s ON s.id=a.session_id JOIN session_owners o ON o.session_id=s.id
 JOIN v_session_state state ON state.session_id=s.id
 JOIN v_attempt_outcomes outcomes ON outcomes.session_id=a.session_id AND outcomes.ordinal=a.ordinal
 LEFT JOIN v_session_equipment eq ON eq.session_id=a.session_id AND eq.ordinal=a.ordinal
 JOIN shot_source_metrics r ON r.observation_id=a.observation_id
 LEFT JOIN attempt_derived_results pin ON pin.session_id=a.session_id AND pin.ordinal=a.ordinal AND pin.model_family='flight'
 LEFT JOIN calculation_attempt_contexts ac ON ac.session_id=a.session_id AND ac.ordinal=a.ordinal AND ac.model_family='flight'
 LEFT JOIN derived_metric_selection selected ON selected.shot_id=a.shot_id AND selected.model_family='flight' AND selected.context_id=COALESCE(pin.context_id,ac.context_id)
 LEFT JOIN shot_derived_metrics d ON d.result_id=selected.result_id
 LEFT JOIN calculation_runs flight_run ON flight_run.run_id=d.run_id
 LEFT JOIN derived_metric_selection sf ON sf.shot_id=a.shot_id AND sf.model_family='source_features' AND sf.context_id='shot'
 LEFT JOIN shot_derived_metrics features ON features.result_id=sf.result_id AND EXISTS(
 SELECT 1 FROM calculation_inputs dep JOIN shot_primary_source primary_report ON primary_report.shot_id=dep.shot_id AND primary_report.report_id=dep.report_id
 WHERE dep.result_id=sf.result_id)
 LEFT JOIN attempt_derived_results pp ON pp.session_id=a.session_id AND pp.ordinal=a.ordinal AND pp.model_family='putting'
 LEFT JOIN calculation_attempt_contexts pc ON pc.session_id=a.session_id AND pc.ordinal=a.ordinal AND pc.model_family='putting'
 LEFT JOIN derived_metric_selection ps ON ps.shot_id=a.shot_id AND ps.model_family='putting' AND ps.context_id=COALESCE(pp.context_id,pc.context_id)
 LEFT JOIN shot_derived_metrics put ON put.result_id=ps.result_id AND put.status='ready'
 LEFT JOIN calculation_runs put_run ON put_run.run_id=put.run_id
 WHERE o.user_id=? AND s.deleted_at IS NULL'''


def read_rows(c, user_id=None, session_id=None):
    query = QUERY
    args = [user_id or active_user(c)]
    if session_id:
        query += ' AND a.session_id=?'
        args.append(session_id)
    return [dict(r) for r in c.execute(query + ' ORDER BY s.started DESC,a.ordinal', args)]


def metric_values(row, basis='source'):
    row = dict(row)
    values = {k: row[SOURCE_FIELDS[k][0]] for k in METRICS if k in SOURCE_FIELDS}
    if basis == 'flight':
        for key in ('carry', 'total', 'offline', 'peak_height', 'descent_ang', 'hang_time'):
            values[key] = (
                row.get('model_' + SOURCE_FIELDS[key][0])
                if row.get('flight_status') == 'ready'
                else None
            )
        for key in (
            'calculated_smash_factor',
            'source_rollout_yd',
            'estimated_distance_ft',
            'distance_error_ft',
        ):
            values[key] = row[key]
    return values


def sessions_for_analysis(
    c, user_id=None, basis='source', tag_names=(), tag_match='any', configuration=''
):
    # Tag matches are EXISTS subqueries, never joins that multiply one attempt by tag count.
    sql = QUERY
    args = [user_id or active_user(c)]
    if configuration:
        sql += ' AND eq.configuration_id=?'
        args.append(configuration)
    if tag_names:
        matches = []
        for name in tag_names:
            matches.append(
                "EXISTS(SELECT 1 FROM v_shot_tags t JOIN tags names USING(tag_id) WHERE t.shot_id=a.shot_id AND t.user_id=o.user_id AND names.name_key=? AND (t.scope='shot' OR (t.session_id=a.session_id AND t.ordinal=a.ordinal)))"
            )
            args.append(name.casefold())
        sql += ' AND (' + (' AND ' if tag_match == 'all' else ' OR ').join(matches) + ')'
    rows = c.execute(sql + ' ORDER BY s.started DESC,a.ordinal', args).fetchall()
    sessions = {}
    # Include empty sessions so session-picker behavior remains compatible.
    for r in c.execute(
        'SELECT * FROM v_session_state WHERE user_id=? AND deleted_at IS NULL ORDER BY started DESC',
        (args[0],),
    ):
        sessions[r['session_id']] = dict(
            id=r['session_id'],
            started=r['started'],
            drill=r['drill'],
            session_kind=r['session_kind'],
            practice_type=r['practice_type'],
            demo=bool(r['simulated']),
            shots=[],
        )
    for row in rows:
        shot = dict(
            key=row['legacy_key'],
            captured=row['captured'],
            receipt_id=row['receipt_id'],
            vals=metric_values(row, basis),
            excluded=bool(row['excluded']),
            removed=bool(row['removed']),
            simulated=bool(row['simulated']),
            **{
                k: row[k]
                for k in ('bag_id', 'bag_name', 'club_id', 'club_label', 'swing_label')
                if row[k] is not None
            },
        )
        # Preserve source-only legacy demo descent spelling without decoding old snapshots.
        if shot['vals'].get('descent_ang') is None and row['simulated'] and basis == 'source':
            extra = c.execute(
                "SELECT real_value,integer_value FROM attempt_fields WHERE session_id=? AND ordinal=? AND path='/vals/descent'",
                (row['session_id'], row['ordinal']),
            ).fetchone()
            if extra:
                shot['vals']['descent'] = (
                    extra['real_value']
                    if extra['real_value'] is not None
                    else extra['integer_value']
                )
        sessions[row['session_id']]['shots'].append(shot)
    return list(sessions.values())


def report(c, params, user_id=None):
    basis = params.get('basis', 'source')
    tag_match = params.get('tag_match', 'any')
    names = tuple(dict.fromkeys(n.strip() for n in params.get('tags', '').split(',') if n.strip()))
    if basis not in ('source', 'flight') or tag_match not in ('any', 'all') or len(names) > 20:
        raise ValueError('Choose valid metric/tag filters.')
    r = build_report(
        sessions_for_analysis(c, user_id, basis, names, tag_match, params.get('configuration', '')),
        params,
    )
    r['filters'].update(
        basis=basis,
        tags=', '.join(names),
        tag_match=tag_match,
        configuration=params.get('configuration', ''),
    )
    r['options']['tags'] = [
        r[0]
        for r in c.execute(
            'SELECT name FROM tags WHERE user_id=? ORDER BY name', (user_id or active_user(c),)
        )
    ]
    picked = {(row['session_id'], row['key']) for row in r['rows'] + r.get('context_rows', [])}
    r['lineage'] = [
        {
            k: row[k]
            for k in (
                'session_id',
                'legacy_key',
                'shot_id',
                'report_id',
                'configuration_id',
                'context_id',
                'flight_result_id',
                'flight_model_version',
                'putting_result_id',
                'putting_model_version',
                'features_result_id',
            )
        }
        for row in read_rows(c, user_id)
        if (row['session_id'], row['legacy_key']) in picked
    ]
    r['options']['configurations'] = {
        r['configuration_id']: f"{r['club_label']} · config {r['configuration_id'][:6]}"
        for r in c.execute(
            'SELECT DISTINCT configuration_id,club_label FROM v_session_equipment WHERE user_id=? AND configuration_id IS NOT NULL',
            (user_id or active_user(c),),
        )
    }
    if basis == 'flight':
        r['method'] = (
            'Selected analytical flight/putting/source-feature results; launch/club fields are source inputs. Median/type-7 IQR. Missing model outputs stay unavailable; saved scores/reviews stay pinned.'
        )
    return r


def save_collection(c, data):
    if not data.get('collection_kind'):
        return None
    sid = data['id']
    owner = c.execute('SELECT user_id FROM session_owners WHERE session_id=?', (sid,)).fetchone()[0]
    rows = read_rows(c, owner, sid)
    signature = [
        {
            k: r[k]
            for k in (
                'session_id',
                'ordinal',
                'shot_id',
                'report_id',
                'context_id',
                'configuration_id',
                'flight_result_id',
                'excluded',
                'removed',
                'swing_label',
            )
        }
        for r in rows
    ]
    params = dict(
        plan=data['collection_plan'],
        labels=data.get('swing_labels', ['']),
        sample_goal=data['collection_samples'],
        metric=data['range_metric'],
        mode=data['demo'],
    )
    fingerprint = hashlib.sha256(encoded([sid, params, signature]).encode()).hexdigest()
    aid = identity('collection:' + sid + ':' + fingerprint)
    existing = c.execute('SELECT 1 FROM analysis_runs WHERE analysis_id=?', (aid,)).fetchone()
    if not existing:
        c.execute(
            'INSERT INTO analysis_runs VALUES(?,?,?,?,?,?,?,?,?,?)',
            (
                aid,
                owner,
                sid,
                data['collection_kind'],
                data['range_metric'],
                int(data['demo']),
                'median-type7-v1-distinct-physical-shot',
                fingerprint,
                encoded(params),
                now(),
            ),
        )
        for r in rows:
            c.execute(
                'INSERT INTO analysis_members VALUES(?,?,?,?,?,?,?,?,?,?)',
                (
                    aid,
                    sid,
                    r['ordinal'],
                    r['shot_id'],
                    r['report_id'],
                    r['context_id'],
                    r['flight_result_id'],
                    int(not r['excluded'] and not r['removed']),
                    r['removed'],
                    r['revision'],
                ),
            )
        for eq in data['collection_plan']:
            plan_config = c.execute(
                '''SELECT m.configuration_id FROM bag_memberships m JOIN bag_revisions b USING(bag_revision_id)
                WHERE b.bag_id=? AND b.catalog_revision=? AND m.club_id=?''',
                (eq['bag_id'], eq['catalog_revision'], eq['club_id']),
            ).fetchone()
            plan_config = plan_config[0] if plan_config else None
            for label in data.get('swing_labels', ['']):
                candidates = [
                    r
                    for r in rows
                    if r['bag_id'] == eq['bag_id']
                    and r['club_id'] == eq['club_id']
                    and (r['swing_label'] or '') == label
                    and r['configuration_id'] == plan_config
                    and not r['excluded']
                    and not r['removed']
                ]
                unique = {r['shot_id']: r for r in candidates}
                rs = list(unique.values())
                rid = identity('cell:' + aid + ':' + eq['club_id'] + ':' + label)
                c.execute(
                    'INSERT INTO collection_results VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    (
                        rid,
                        aid,
                        eq['bag_id'],
                        eq['club_id'],
                        plan_config,
                        eq['bag_name'],
                        eq['club_label'],
                        label,
                        1,
                        data['collection_samples'],
                        len(rs),
                    ),
                )
                for metric in METRICS:
                    summary = robust(
                        abs(r['ball_offline_yd'])
                        if metric == 'absolute_offline' and r['ball_offline_yd'] is not None
                        else metric_values(r).get(metric)
                        for r in rs
                    )
                    c.execute(
                        'INSERT INTO group_metric_results VALUES(?,?,?,?,?,?,?)',
                        (
                            rid,
                            metric,
                            summary['count'],
                            summary['median'],
                            summary['q1'],
                            summary['q3'],
                            summary['iqr'],
                        ),
                    )
        if data['collection_kind'] == 'bag':
            ordered = c.execute(
                'SELECT * FROM v_bag_map_results WHERE analysis_id=? AND median IS NOT NULL ORDER BY median DESC,result_id',
                (aid,),
            ).fetchall()
            for longer, shorter in zip(ordered, ordered[1:]):
                overlap = (
                    int(longer['q1'] <= shorter['q3'])
                    if longer['q1'] is not None and shorter['q3'] is not None
                    else None
                )
                c.execute(
                    'INSERT INTO bag_gap_results VALUES(?,?,?,?,?)',
                    (
                        aid,
                        longer['result_id'],
                        shorter['result_id'],
                        longer['median'] - shorter['median'],
                        overlap,
                    ),
                )
    c.execute(
        'INSERT INTO collection_analysis_selection VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET analysis_id=excluded.analysis_id',
        (sid, aid),
    )
    return aid


def collection_snapshot(c, sid):
    selected = c.execute(
        'SELECT a.* FROM collection_analysis_selection s JOIN analysis_runs a USING(analysis_id) WHERE s.session_id=?',
        (sid,),
    ).fetchone()
    if not selected:
        return None
    rows = []
    for cell in c.execute(
        'SELECT * FROM collection_results WHERE analysis_id=? ORDER BY rowid',
        (selected['analysis_id'],),
    ):
        metrics = {
            r['metric']: dict(
                count=r['available_count'], median=r['median'], q1=r['q1'], q3=r['q3'], iqr=r['iqr']
            )
            for r in c.execute(
                'SELECT * FROM group_metric_results WHERE result_id=?', (cell['result_id'],)
            )
        }
        rows.append(
            dict(
                cell,
                **metrics[selected['distance_basis']],
                launch=metrics['launch_ang'],
                spin=metrics['total_spin'],
                label=cell['swing_label'],
            )
        )
    published = c.execute(
        'SELECT 1 FROM equipment_profile_selection WHERE analysis_id=?', (selected['analysis_id'],)
    ).fetchone()
    return dict(
        analysis_id=selected['analysis_id'],
        kind=selected['kind'],
        rows=rows,
        selected_for_play=bool(published),
        counting='Distinct physical shots; planned configuration only.',
        created_at=selected['created_at'],
    )


def select_profile(c, session_id):
    row = c.execute(
        '''SELECT a.* FROM analysis_runs a JOIN collection_analysis_selection s USING(analysis_id) WHERE s.session_id=?''',
        (session_id,),
    ).fetchone()
    if not row or row['user_id'] != active_user(c):
        raise ValueError('Choose a collection owned by the current golfer.')
    for bag in c.execute(
        'SELECT DISTINCT bag_id FROM collection_results WHERE analysis_id=?', (row['analysis_id'],)
    ).fetchall():
        if not c.execute(
            'SELECT 1 FROM bags WHERE bag_id=? AND user_id=?', (bag[0], row['user_id'])
        ).fetchone():
            raise ValueError('Historical bag cannot be selected as a current profile.')
        c.execute(
            'INSERT INTO equipment_profile_selection VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,bag_id,kind,simulated) DO UPDATE SET analysis_id=excluded.analysis_id,selected_at=excluded.selected_at',
            (row['user_id'], bag[0], row['kind'], row['simulated'], row['analysis_id'], now()),
        )
    return row['analysis_id']


def preview_sessions(c, game, user_id=None):
    """Current analytical paths, owned configurations and explicit frozen profile cohorts."""
    user_id = user_id or active_user(c)
    eq = game.get('equipment_selection') or {}
    bag = eq.get('bag_id')
    club = eq.get('club_id')
    rows = read_rows(c, user_id)
    profiles = {
        r['kind']: dict(r)
        for r in c.execute(
            'SELECT * FROM equipment_profile_selection WHERE user_id=? AND bag_id=? AND simulated=?',
            (user_id, bag, int(game['demo'])),
        )
    }
    configs = c.execute(
        '''SELECT r.* FROM bag_memberships m JOIN bag_revisions b USING(bag_revision_id)
        JOIN equipment_catalogs e ON e.user_id=b.user_id AND e.revision=b.catalog_revision
        JOIN club_revisions r USING(configuration_id) WHERE b.bag_id=? AND m.club_id=?''',
        (bag, club),
    ).fetchone()
    sessions = {}
    seen = set()
    warnings = []
    for r in rows:
        kind = r['collection_kind']
        if (
            not kind
            or r['bag_id'] != bag
            or r['club_id'] != club
            or bool(r['simulated']) != bool(game['demo'])
        ):
            continue
        profile = profiles.get(kind)
        if profile:
            selected = c.execute(
                'SELECT analysis_id FROM collection_analysis_selection WHERE session_id=?',
                (r['session_id'],),
            ).fetchone()
            if (
                r['session_id']
                != c.execute(
                    'SELECT session_id FROM analysis_runs WHERE analysis_id=?',
                    (profile['analysis_id'],),
                ).fetchone()[0]
            ):
                continue
            if not selected or selected[0] != profile['analysis_id']:
                warnings.append(
                    'Selected ' + kind + ' profile changed. Review and publish it again.'
                )
                continue
            if not c.execute(
                'SELECT 1 FROM analysis_members WHERE analysis_id=? AND session_id=? AND ordinal=?',
                (profile['analysis_id'], r['session_id'], r['ordinal']),
            ).fetchone():
                continue
        if configs and (
            r['configuration_id']
            and r['configuration_id'] != configs['configuration_id']
            or not r['configuration_id']
            and any(
                configs[k] is not None for k in ('make', 'model', 'loft_deg', 'shaft', 'settings')
            )
        ):
            continue
        duplicate = (kind, r['swing_label'] or '', r['shot_id'])
        if not r['excluded'] and not r['removed']:
            if duplicate in seen:
                continue
            seen.add(duplicate)
        s = sessions.setdefault(
            r['session_id'],
            dict(
                id=r['session_id'],
                started=r['started'],
                drill=r['drill'],
                practice_type='full_swing',
                collection_kind=kind,
                demo=game['demo'],
                shots=[],
            ),
        )
        shot = dict(
            key=r['legacy_key'],
            captured=r['captured'],
            vals=metric_values(r),
            excluded=bool(r['excluded']),
            removed=bool(r['removed']),
            swing_label=r['swing_label'],
            **{k: r[k] for k in ('bag_id', 'bag_name', 'club_id', 'club_label')},
        )
        if r['flight_status'] == 'ready':
            shot['flight'] = dict(
                status='ready',
                model=json.loads(r['flight_json']).get('model'),
                analytical_version=True,
                carry_point_yd=dict(forward=r['carry_forward_yd'], right=r['carry_right_yd']),
                total_point_yd=dict(forward=r['total_forward_yd'], right=r['total_right_yd']),
            )
        s['shots'].append(shot)
    return list(sessions.values()), list(dict.fromkeys(warnings))
