"""Complete CSV/ZIP export of the TraceLoft database from one committed snapshot."""

import csv
import io
import json
import zipfile

from storage import FIELDS, SCHEMA_VERSION, encoded, now


def export_archive(store):
    """One committed snapshot, separate observation rows, blank unavailable cells."""
    with store.reading() as connection:
        metric_cursor = connection.execute('''SELECT o.shot_id, s.occurred_at, s.time_basis, s.reported_club,
            o.id observation_id,o.provenance,o.mapping_id,o.event_id,c.source_id,e.acceptance,
            e.source_time,e.received_at,e.time_basis observation_time_basis,
            v.metric_key,v.definition_version,v.real_value,v.text_value,v.bool_value,v.integer_value,
            d.canonical_unit,v.source_unit,v.source_json,v.availability,v.method,v.variant
            FROM observations o LEFT JOIN shots s ON s.id=o.shot_id
            JOIN ingest_events e ON e.id=o.event_id JOIN capture_streams c ON c.id=e.stream_id
            JOIN metric_values v ON v.observation_id=o.id
            JOIN metric_definitions d ON d.key=v.metric_key AND d.version=v.definition_version
            ORDER BY o.shot_id,o.id,v.metric_key''')
        metric_fields = [d[0] for d in metric_cursor.description]
        metrics = [dict(r) for r in metric_cursor]
        attempt_cursor = connection.execute(
            'SELECT a.*,s.deleted_at FROM session_attempts a JOIN sessions s ON s.id=a.session_id ORDER BY a.session_id,a.ordinal'
        )
        attempt_fields = [d[0] for d in attempt_cursor.description]
        attempts = [dict(r) for r in attempt_cursor]
        # Derived putting outcomes belong to attempts, never to measured ball metrics.
        distance_fields = [
            'estimated_distance_ft',
            'target_distance_ft',
            'distance_error_ft',
            'distance_model_id',
            'stimp_ft',
            'ladder_rung',
            'ladder_round',
            'target_mode',
            'distance_tolerance_ft',
            'distance_source_revision',
            'target_distance_yd',
            'distance_yd',
            'distance_error_yd',
            'distance_metric',
            'scored',
            'unscored_reason',
            'club_label',
            'distance_tolerance_yd',
            'swing_label',
            'bag_id',
            'bag_name',
            'club_id',
            'catalog_revision',
            'selection_mode',
            'simulated',
            'removed',
            'cleanup_reason',
            'corrected_equipment',
            'flight',
        ]
        attempt_fields += distance_fields
        from domain_schema import read_session

        contexts = {
            r[0]: read_session(connection, r[0])
            for r in connection.execute('SELECT id FROM sessions').fetchall()
        }
        for attempt in attempts:
            outcome = contexts[attempt['session_id']]['shots'][attempt['ordinal'] - 1]
            context = contexts[attempt['session_id']]
            for field in distance_fields:
                attempt[field] = outcome.get(field)
            attempt['target_mode'] = context.get('target_mode')
            attempt['distance_tolerance_ft'] = context.get('distance_tolerance')
            attempt['distance_tolerance_yd'] = context.get('range_tolerance')
            attempt['distance_source_revision'] = context.get('distance_model', {}).get(
                'source_revision'
            )
        shot_cursor = connection.execute('SELECT * FROM shots ORDER BY occurred_at,id')
        shot_fields = (
            [d[0] for d in shot_cursor.description]
            + ['simulated']
            + [
                field + '_' + ('degrees' if unit == 'deg' else unit)
                for field, (_, unit, _) in FIELDS.items()
            ]
        )
        shots = [dict(r) for r in shot_cursor]
        simulated_events = {
            r['id']
            for r in connection.execute('SELECT id,raw_json FROM ingest_events')
            if json.loads(r['raw_json']).get('simulated')
        }
        for shot in shots:
            shot['simulated'] = shot['event_id'] in simulated_events
        from shot_schema import SOURCE_FIELDS

        reports = {r['shot_id']: r for r in connection.execute('SELECT * FROM v_shots_source')}
        for shot in shots:
            # One explicit report supplies the row; never blend values from competing reports.
            report = reports.get(shot['id'])
            for field, (_metric, unit, _factor) in FIELDS.items():
                shot[field + '_' + ('degrees' if unit == 'deg' else unit)] = (
                    report[SOURCE_FIELDS[field][0]] if report else None
                )
        files = {
            'shots.csv': shots,
            'metric_values.csv': metrics,
            'session_attempts.csv': attempts,
        }
        field_sets = {
            'shots.csv': shot_fields,
            'metric_values.csv': metric_fields,
            'session_attempts.csv': attempt_fields,
        }
        for table in (
            'shot_source_metrics',
            'source_metric_quality',
            'shot_primary_source',
            'shot_derived_metrics',
            'calculation_runs',
            'calculation_inputs',
            'derived_metric_selection',
            'attempt_derived_results',
            'shot_trajectories',
            'users',
            'session_owners',
            'shot_owners',
            'bags',
            'clubs',
            'bag_revisions',
            'club_revisions',
            'bag_memberships',
            'shot_contexts',
            'context_selection',
            'session_plans',
            'session_plan_items',
            'session_fields',
            'attempt_fields',
            'tags',
            'shot_tag_events',
            'analysis_runs',
            'analysis_members',
            'collection_results',
            'group_metric_results',
            'bag_gap_results',
            'equipment_profile_selection',
            'recalculation_batches',
            'recalculation_inputs',
            'recalculation_outputs',
            'calculation_lineage',
            'calculation_attempt_contexts',
            'calculation_publications',
            'calculation_publication_items',
            'source_estimates',
        ):
            cursor = connection.execute(f'SELECT * FROM {table} ORDER BY rowid')
            files[table + '.csv'] = [dict(r) for r in cursor]
            field_sets[table + '.csv'] = [d[0] for d in cursor.description]
        for view, name in (
            ('v_shots_source', 'shots_source.csv'),
            ('v_session_shots', 'session_shots_wide.csv'),
            ('v_session_equipment', 'session_equipment.csv'),
            ('v_calculation_history', 'calculation_history.csv'),
            ('v_session_current_metrics', 'session_current_metrics.csv'),
            ('v_bag_map_results', 'bag_map_results.csv'),
            ('v_wedge_matrix_results', 'wedge_matrix_results.csv'),
        ):
            cursor = connection.execute(f'SELECT * FROM {view}')
            files[name] = [dict(r) for r in cursor]
            field_sets[name] = [d[0] for d in cursor.description]
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, rows in files.items():
                text = io.StringIO(newline='')
                fields = field_sets[name]
                writer = csv.DictWriter(text, fields)
                writer.writeheader()
                # Protect spreadsheet text while preserving genuine numeric values.
                writer.writerows(
                    {
                        k: "'" + v
                        if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@'))
                        else v
                        for k, v in row.items()
                    }
                    for row in rows
                )
                archive.writestr(name, text.getvalue().encode('utf-8-sig'))
            archive.writestr(
                'manifest.json',
                encoded(
                    dict(
                        schema=SCHEMA_VERSION,
                        created=now(),
                        scope='all_captured_including_session_exclusions_and_deleted_sessions',
                        counts={name: len(rows) for name, rows in files.items()},
                        missing='blank; see availability in long export',
                        row_shapes={
                            'shots_source.csv': 'one selected report per physical shot; no model fallback',
                            'shot_source_metrics.csv': 'all observations including competing reports',
                            'session_shots_wide.csv': 'one row per session attempt, including excluded/deleted history',
                            'shot_derived_metrics.csv': 'all result versions; filter model family/context before aggregating',
                            'source_estimates.csv': "a source's own estimates (e.g. rēlā face/loft), never measurements",
                        },
                        timestamps='time_basis declares UTC receipts versus timezone-unknown legacy local times',
                        text_safety='formula-leading text prefixed with apostrophe',
                    )
                ),
            )
            archive.writestr(
                'metric_catalog.json',
                encoded(
                    [
                        json.loads(r[0])
                        for r in connection.execute(
                            'SELECT definition_json FROM metric_definitions ORDER BY key,version'
                        )
                    ]
                ),
            )
            archive.writestr(
                'metric_mappings.json',
                encoded(
                    [
                        json.loads(r[0])
                        for r in connection.execute(
                            'SELECT payload FROM mapping_versions ORDER BY id'
                        )
                    ]
                ),
            )
            archive.writestr(
                'putting_models.json',
                encoded(
                    {
                        sid: context['distance_model']
                        for sid, context in contexts.items()
                        if context.get('distance_model')
                    }
                ),
            )
        return output.getvalue()
