
CREATE TABLE source_estimates(observation_id TEXT NOT NULL REFERENCES observations(id),
 shot_id TEXT NOT NULL REFERENCES shots(id),estimator TEXT NOT NULL,metric_key TEXT NOT NULL,
 real_value REAL NOT NULL,canonical_unit TEXT NOT NULL,source_field TEXT NOT NULL,source_value REAL NOT NULL,
 source_unit TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(observation_id,metric_key));
CREATE INDEX source_estimates_shot ON source_estimates(shot_id,metric_key);
CREATE TRIGGER source_estimates_immutable BEFORE UPDATE ON source_estimates BEGIN
 SELECT RAISE(ABORT,'Source estimates are immutable; they are evidence of what the source reported');
END;
