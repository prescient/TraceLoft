
CREATE UNIQUE INDEX observations_identity_shot ON observations(id,shot_id);
CREATE UNIQUE INDEX attempts_identity_shot ON session_attempts(session_id,ordinal,shot_id);
CREATE TABLE shot_source_metrics(
 report_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL UNIQUE,
 shot_id TEXT, normalization_revision TEXT NOT NULL, created_at TEXT NOT NULL,
 club_head_speed_mph REAL,
smash_factor REAL,
club_path_deg REAL,
angle_of_attack_deg REAL,
carry_distance_yd REAL,
total_distance_yd REAL,
ball_speed_mph REAL,
total_spin_rpm REAL,
vertical_launch_angle_deg REAL,
horizontal_launch_angle_deg REAL,
spin_tilt_axis_deg REAL,
back_spin_rpm REAL,
side_spin_rpm REAL,
ball_apex_ft REAL,
ball_descent_angle_deg REAL,
ball_offline_yd REAL,
ball_curve_yd REAL,
hang_time_s REAL,
 UNIQUE(report_id,shot_id),
 FOREIGN KEY(observation_id,shot_id) REFERENCES observations(id,shot_id)
 DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX source_shot ON shot_source_metrics(shot_id);
CREATE TABLE source_metric_quality(
 report_id TEXT NOT NULL REFERENCES shot_source_metrics(report_id), column_name TEXT NOT NULL,
 availability TEXT NOT NULL CHECK(availability IN ('available','unavailable','invalid','not_supplied')),
 source_field TEXT NOT NULL, source_unit TEXT, method TEXT, semantic_variant TEXT,
 PRIMARY KEY(report_id,column_name),
 CHECK(column_name IN ('club_head_speed_mph','smash_factor','club_path_deg','angle_of_attack_deg','carry_distance_yd','total_distance_yd','ball_speed_mph','total_spin_rpm','vertical_launch_angle_deg','horizontal_launch_angle_deg','spin_tilt_axis_deg','back_spin_rpm','side_spin_rpm','ball_apex_ft','ball_descent_angle_deg','ball_offline_yd','ball_curve_yd','hang_time_s')));
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
 reason TEXT, flight_shape TEXT, carry_distance_yd REAL,
total_distance_yd REAL,
carry_forward_yd REAL,
carry_right_yd REAL,
total_forward_yd REAL,
total_right_yd REAL,
offline_distance_yd REAL,
absolute_offline_yd REAL,
apex_ft REAL,
descent_angle_deg REAL,
hang_time_s REAL,
calculated_smash_factor REAL,
source_rollout_yd REAL,
estimated_distance_ft REAL,
target_distance_ft REAL,
distance_error_ft REAL,
stimp_ft REAL,
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
 r.club_head_speed_mph,r.smash_factor,r.club_path_deg,r.angle_of_attack_deg,r.carry_distance_yd,r.total_distance_yd,r.ball_speed_mph,r.total_spin_rpm,r.vertical_launch_angle_deg,r.horizontal_launch_angle_deg,r.spin_tilt_axis_deg,r.back_spin_rpm,r.side_spin_rpm,r.ball_apex_ft,r.ball_descent_angle_deg,r.ball_offline_yd,r.ball_curve_yd,r.hang_time_s,
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
 s.deleted_at,r.report_id,r.club_head_speed_mph,r.smash_factor,r.club_path_deg,r.angle_of_attack_deg,r.carry_distance_yd,r.total_distance_yd,r.ball_speed_mph,r.total_spin_rpm,r.vertical_launch_angle_deg,r.horizontal_launch_angle_deg,r.spin_tilt_axis_deg,r.back_spin_rpm,r.side_spin_rpm,r.ball_apex_ft,r.ball_descent_angle_deg,r.ball_offline_yd,r.ball_curve_yd,r.hang_time_s,
 f.result_id flight_result_id,f.carry_distance_yd model_carry_distance_yd,
 f.total_distance_yd model_total_distance_yd,f.flight_shape,
 p.result_id putting_result_id,p.estimated_distance_ft,p.distance_error_ft,p.stimp_ft
 FROM session_attempts a JOIN sessions s ON s.id=a.session_id
 JOIN shot_source_metrics r ON r.observation_id=a.observation_id
 LEFT JOIN attempt_derived_results af ON af.session_id=a.session_id AND af.ordinal=a.ordinal AND af.model_family='flight'
 LEFT JOIN shot_derived_metrics f ON f.result_id=af.result_id
 LEFT JOIN attempt_derived_results ap ON ap.session_id=a.session_id AND ap.ordinal=a.ordinal AND ap.model_family='putting'
 LEFT JOIN shot_derived_metrics p ON p.result_id=ap.result_id;

CREATE TRIGGER source_values_immutable BEFORE UPDATE ON shot_source_metrics
 WHEN OLD.report_id IS NOT NEW.report_id OR OLD.observation_id IS NOT NEW.observation_id OR OLD.normalization_revision IS NOT NEW.normalization_revision OR OLD.created_at IS NOT NEW.created_at OR OLD.club_head_speed_mph IS NOT NEW.club_head_speed_mph OR OLD.smash_factor IS NOT NEW.smash_factor OR OLD.club_path_deg IS NOT NEW.club_path_deg OR OLD.angle_of_attack_deg IS NOT NEW.angle_of_attack_deg OR OLD.carry_distance_yd IS NOT NEW.carry_distance_yd OR OLD.total_distance_yd IS NOT NEW.total_distance_yd OR OLD.ball_speed_mph IS NOT NEW.ball_speed_mph OR OLD.total_spin_rpm IS NOT NEW.total_spin_rpm OR OLD.vertical_launch_angle_deg IS NOT NEW.vertical_launch_angle_deg OR OLD.horizontal_launch_angle_deg IS NOT NEW.horizontal_launch_angle_deg OR OLD.spin_tilt_axis_deg IS NOT NEW.spin_tilt_axis_deg OR OLD.back_spin_rpm IS NOT NEW.back_spin_rpm OR OLD.side_spin_rpm IS NOT NEW.side_spin_rpm OR OLD.ball_apex_ft IS NOT NEW.ball_apex_ft OR OLD.ball_descent_angle_deg IS NOT NEW.ball_descent_angle_deg OR OLD.ball_offline_yd IS NOT NEW.ball_offline_yd OR OLD.ball_curve_yd IS NOT NEW.ball_curve_yd OR OLD.hang_time_s IS NOT NEW.hang_time_s
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
