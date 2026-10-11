
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
CREATE VIEW v_session_current_metrics AS SELECT rows.session_id,rows.ordinal,rows.legacy_key,rows.shot_id,
 rows.user_id,users.display_name golfer,rows.captured,rows.drill,rows.deleted_at,rows.simulated,
 rows.bag_name,rows.club_label,rows.configuration_id,rows.context_id,rows.excluded,rows.removed,rows.swing_label,
 rows.report_id,rows.club_head_speed_mph,rows.smash_factor,rows.club_path_deg,rows.angle_of_attack_deg,rows.carry_distance_yd,rows.total_distance_yd,rows.ball_speed_mph,rows.total_spin_rpm,rows.vertical_launch_angle_deg,rows.horizontal_launch_angle_deg,rows.spin_tilt_axis_deg,rows.back_spin_rpm,rows.side_spin_rpm,rows.ball_apex_ft,rows.ball_descent_angle_deg,rows.ball_offline_yd,rows.ball_curve_yd,rows.hang_time_s,
 rows.flight_result_id,rows.flight_model_version,rows.flight_status,
 rows.model_carry_distance_yd,rows.model_total_distance_yd,rows.model_ball_offline_yd,
 rows.model_ball_apex_ft,rows.model_ball_descent_angle_deg,rows.model_hang_time_s,
 rows.putting_result_id,rows.putting_model_version,rows.estimated_distance_ft,rows.distance_error_ft,
 rows.features_result_id,rows.calculated_smash_factor,rows.source_rollout_yd
 FROM (SELECT a.*,s.started,s.drill,s.revision,s.deleted_at,o.user_id,
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
) rows JOIN users USING(user_id);