
CREATE UNIQUE INDEX contexts_cohort_identity ON shot_contexts(context_id,session_id,ordinal,shot_id);
CREATE TABLE analysis_runs(analysis_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 session_id TEXT REFERENCES sessions(id), kind TEXT NOT NULL, distance_basis TEXT NOT NULL,
 simulated INTEGER NOT NULL, method_version TEXT NOT NULL, cohort_fingerprint TEXT NOT NULL,
 parameters_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,kind,cohort_fingerprint));
CREATE TABLE analysis_members(analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
 session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, shot_id TEXT NOT NULL REFERENCES shots(id),
 report_id TEXT NOT NULL REFERENCES shot_source_metrics(report_id), context_id TEXT REFERENCES shot_contexts(context_id),
 flight_result_id TEXT REFERENCES shot_derived_metrics(result_id), included INTEGER NOT NULL,
 removed INTEGER NOT NULL, inclusion_revision INTEGER NOT NULL, PRIMARY KEY(analysis_id,session_id,ordinal),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 FOREIGN KEY(report_id,shot_id) REFERENCES shot_source_metrics(report_id,shot_id),
 FOREIGN KEY(context_id,session_id,ordinal,shot_id) REFERENCES shot_contexts(context_id,session_id,ordinal,shot_id));
CREATE TABLE collection_results(result_id TEXT PRIMARY KEY, analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
 bag_id TEXT, club_id TEXT, configuration_id TEXT REFERENCES club_revisions(configuration_id),
 bag_name TEXT, club_label TEXT, swing_label TEXT NOT NULL, planned INTEGER NOT NULL,
 sample_goal INTEGER NOT NULL, included_count INTEGER NOT NULL);
CREATE TABLE group_metric_results(result_id TEXT NOT NULL REFERENCES collection_results(result_id),
 metric TEXT NOT NULL, available_count INTEGER NOT NULL, median REAL,q1 REAL,q3 REAL,iqr REAL,
 PRIMARY KEY(result_id,metric));
CREATE TABLE bag_gap_results(analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
 longer_result_id TEXT NOT NULL REFERENCES collection_results(result_id),
 shorter_result_id TEXT NOT NULL REFERENCES collection_results(result_id), median_gap_yd REAL NOT NULL,
 iqr_overlap INTEGER, PRIMARY KEY(analysis_id,longer_result_id,shorter_result_id));
CREATE TABLE collection_analysis_selection(session_id TEXT PRIMARY KEY REFERENCES sessions(id),
 analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id));
CREATE TABLE equipment_profile_selection(user_id TEXT NOT NULL REFERENCES users(user_id), bag_id TEXT NOT NULL REFERENCES bags(bag_id),
 kind TEXT NOT NULL, simulated INTEGER NOT NULL, analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id),
 selected_at TEXT NOT NULL, PRIMARY KEY(user_id,bag_id,kind,simulated));
CREATE VIEW v_bag_map_results AS SELECT r.*, a.user_id,a.distance_basis,a.created_at,m.available_count,m.median,m.q1,m.q3,m.iqr
 FROM collection_results r JOIN analysis_runs a USING(analysis_id)
 JOIN group_metric_results m ON m.result_id=r.result_id AND m.metric=a.distance_basis WHERE a.kind='bag';
CREATE VIEW v_wedge_matrix_results AS SELECT r.*, a.user_id,a.distance_basis,a.created_at,m.available_count,m.median,m.q1,m.q3,m.iqr,
 l.median launch_angle_deg,l.available_count launch_count,s.median total_spin_rpm,s.available_count spin_count
 FROM collection_results r JOIN analysis_runs a USING(analysis_id)
 JOIN group_metric_results m ON m.result_id=r.result_id AND m.metric=a.distance_basis
 JOIN group_metric_results l ON l.result_id=r.result_id AND l.metric='launch_ang'
 JOIN group_metric_results s ON s.result_id=r.result_id AND s.metric='total_spin' WHERE a.kind='wedge';
CREATE TRIGGER analysis_runs_immutable BEFORE UPDATE ON analysis_runs BEGIN SELECT RAISE(ABORT,'Analysis runs are immutable'); END;
CREATE TRIGGER analysis_members_immutable BEFORE UPDATE ON analysis_members BEGIN SELECT RAISE(ABORT,'Analysis membership is immutable'); END;
CREATE TRIGGER collection_results_immutable BEFORE UPDATE ON collection_results BEGIN SELECT RAISE(ABORT,'Collection results are immutable'); END;
CREATE TRIGGER group_metrics_immutable BEFORE UPDATE ON group_metric_results BEGIN SELECT RAISE(ABORT,'Group metrics are immutable'); END;
CREATE TRIGGER profile_ownership BEFORE INSERT ON equipment_profile_selection BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM analysis_runs a JOIN bags b USING(user_id)
 WHERE a.analysis_id=NEW.analysis_id AND b.bag_id=NEW.bag_id AND a.user_id=NEW.user_id
 AND a.kind=NEW.kind AND a.simulated=NEW.simulated) THEN RAISE(ABORT,'Profile ownership/scope mismatch') END; END;
CREATE TRIGGER profile_update_ownership BEFORE UPDATE ON equipment_profile_selection BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM analysis_runs a JOIN bags b USING(user_id)
 WHERE a.analysis_id=NEW.analysis_id AND b.bag_id=NEW.bag_id AND a.user_id=NEW.user_id
 AND a.kind=NEW.kind AND a.simulated=NEW.simulated) THEN RAISE(ABORT,'Profile ownership/scope mismatch') END; END;
CREATE TRIGGER collection_selection_scope BEFORE INSERT ON collection_analysis_selection BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM analysis_runs WHERE analysis_id=NEW.analysis_id AND session_id=NEW.session_id)
 THEN RAISE(ABORT,'Collection selection scope mismatch') END; END;
CREATE TRIGGER collection_selection_update_scope BEFORE UPDATE ON collection_analysis_selection BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM analysis_runs WHERE analysis_id=NEW.analysis_id AND session_id=NEW.session_id)
 THEN RAISE(ABORT,'Collection selection scope mismatch') END; END;
