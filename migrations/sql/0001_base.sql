
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE metric_definitions(
 key TEXT NOT NULL, version INTEGER NOT NULL, value_type TEXT NOT NULL,
 canonical_unit TEXT, definition_json TEXT NOT NULL, PRIMARY KEY(key, version));
CREATE TABLE mapping_versions(id TEXT PRIMARY KEY, hash TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY, configuration_json TEXT NOT NULL);
CREATE TABLE capture_streams(id TEXT PRIMARY KEY, source_id TEXT REFERENCES sources(id), legacy_id TEXT);
CREATE TABLE import_files(
 id TEXT PRIMARY KEY, path TEXT NOT NULL, hash TEXT NOT NULL, content BLOB NOT NULL,
 imported_at TEXT NOT NULL, UNIQUE(path, hash));
CREATE TABLE ingest_events(
 id TEXT PRIMARY KEY, stream_id TEXT REFERENCES capture_streams(id), legacy_key TEXT,
 source_time TEXT, received_at TEXT, time_basis TEXT NOT NULL,
 acceptance TEXT NOT NULL CHECK(acceptance IN ('accepted','logged','failed','unknown')),
 raw_json TEXT NOT NULL, import_file_id TEXT REFERENCES import_files(id), row_number INTEGER);
CREATE INDEX events_legacy ON ingest_events(legacy_key);
CREATE TABLE shots(id TEXT PRIMARY KEY, event_id TEXT UNIQUE REFERENCES ingest_events(id),
 occurred_at TEXT, time_basis TEXT NOT NULL, reported_club TEXT);
CREATE TABLE observations(id TEXT PRIMARY KEY, event_id TEXT UNIQUE NOT NULL REFERENCES ingest_events(id),
 shot_id TEXT REFERENCES shots(id), mapping_id TEXT NOT NULL REFERENCES mapping_versions(id),
 provenance TEXT NOT NULL);
CREATE TABLE metric_values(
 observation_id TEXT NOT NULL REFERENCES observations(id), metric_key TEXT NOT NULL,
 definition_version INTEGER NOT NULL, real_value REAL, text_value TEXT, bool_value INTEGER, integer_value INTEGER,
 source_field TEXT NOT NULL, source_unit TEXT, source_json TEXT NOT NULL,
 availability TEXT NOT NULL CHECK(availability IN ('available','unavailable','invalid')),
 method TEXT NOT NULL, variant TEXT NOT NULL,
 PRIMARY KEY(observation_id, metric_key, definition_version),
 FOREIGN KEY(metric_key,definition_version) REFERENCES metric_definitions(key,version),
 CHECK(bool_value IS NULL OR bool_value IN (0,1)),
 CHECK((real_value IS NOT NULL)+(text_value IS NOT NULL)+(bool_value IS NOT NULL)+(integer_value IS NOT NULL) =
       CASE WHEN availability='available' THEN 1 ELSE 0 END));
CREATE TRIGGER metric_type_insert BEFORE INSERT ON metric_values BEGIN
 SELECT CASE WHEN
 (NEW.real_value IS NOT NULL AND (SELECT value_type FROM metric_definitions WHERE key=NEW.metric_key AND version=NEW.definition_version)!='real') OR
 (NEW.text_value IS NOT NULL AND (SELECT value_type FROM metric_definitions WHERE key=NEW.metric_key AND version=NEW.definition_version)!='text') OR
 (NEW.bool_value IS NOT NULL AND (SELECT value_type FROM metric_definitions WHERE key=NEW.metric_key AND version=NEW.definition_version)!='boolean') OR
 (NEW.integer_value IS NOT NULL AND (SELECT value_type FROM metric_definitions WHERE key=NEW.metric_key AND version=NEW.definition_version)!='integer')
 THEN RAISE(ABORT,'Metric type conflicts with its definition') END;
END;
CREATE TRIGGER metric_values_immutable BEFORE UPDATE ON metric_values BEGIN
 SELECT RAISE(ABORT,'Original metric values are immutable; add a new observation or derivation');
END;
CREATE INDEX values_metric ON metric_values(metric_key, definition_version, real_value);
CREATE INDEX shots_date ON shots(occurred_at);
CREATE TABLE sessions(id TEXT PRIMARY KEY, started TEXT NOT NULL, ended TEXT,
 drill TEXT NOT NULL, deleted_at TEXT, revision INTEGER NOT NULL DEFAULT 1, payload_json TEXT NOT NULL);
CREATE TABLE session_attempts(
 session_id TEXT NOT NULL REFERENCES sessions(id), ordinal INTEGER NOT NULL, legacy_key TEXT NOT NULL,
 shot_id TEXT NOT NULL REFERENCES shots(id), observation_id TEXT NOT NULL REFERENCES observations(id),
 captured TEXT, target REAL NOT NULL, success INTEGER NOT NULL, excluded INTEGER NOT NULL,
 payload_json TEXT NOT NULL, PRIMARY KEY(session_id,ordinal), UNIQUE(session_id,legacy_key));
CREATE INDEX attempts_shot ON session_attempts(shot_id);
CREATE TABLE inclusion_decisions(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 legacy_key TEXT NOT NULL, excluded INTEGER NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL);
CREATE TABLE delivery_events(id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES ingest_events(id),
 status TEXT NOT NULL, evidence_json TEXT NOT NULL);
CREATE TABLE audit_events(id TEXT PRIMARY KEY, entity_id TEXT NOT NULL, action TEXT NOT NULL,
 recorded_at TEXT NOT NULL, payload_json TEXT NOT NULL);
CREATE VIEW shot_metrics AS
 SELECT s.id shot_id, s.occurred_at, s.time_basis, s.reported_club,
 o.id observation_id, o.provenance, o.mapping_id, o.event_id, c.source_id,
 e.source_time, e.received_at, e.time_basis observation_time_basis,
 v.metric_key, v.definition_version, v.real_value, v.text_value, v.bool_value, v.integer_value,
 d.canonical_unit, v.source_unit, v.source_json, v.availability, v.method, v.variant
 FROM shots s JOIN observations o ON o.shot_id=s.id
 JOIN ingest_events e ON e.id=o.event_id JOIN capture_streams c ON c.id=e.stream_id
 JOIN metric_values v ON v.observation_id=o.id
 JOIN metric_definitions d ON d.key=v.metric_key AND d.version=v.definition_version;
