
CREATE TABLE users(user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
 handedness TEXT NOT NULL CHECK(handedness IN ('right_handed','left_handed')),
 created_at TEXT NOT NULL, archived_at TEXT);
CREATE TABLE golfer_selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
 user_id TEXT NOT NULL REFERENCES users(user_id));
CREATE TABLE session_owners(session_id TEXT PRIMARY KEY REFERENCES sessions(id),
 user_id TEXT NOT NULL REFERENCES users(user_id), attribution TEXT NOT NULL,
 UNIQUE(session_id,user_id));
CREATE TABLE shot_owners(shot_id TEXT PRIMARY KEY REFERENCES shots(id),
 user_id TEXT NOT NULL REFERENCES users(user_id), attribution TEXT NOT NULL, UNIQUE(shot_id,user_id));
CREATE TABLE equipment_catalogs(user_id TEXT PRIMARY KEY REFERENCES users(user_id),
 version INTEGER NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE bags(bag_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 created_at TEXT NOT NULL, UNIQUE(bag_id,user_id));
CREATE TABLE clubs(club_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 created_at TEXT NOT NULL, UNIQUE(club_id,user_id));
CREATE TABLE club_revisions(configuration_id TEXT PRIMARY KEY, club_id TEXT NOT NULL,
 user_id TEXT NOT NULL, revision INTEGER NOT NULL, make TEXT, model TEXT, loft_deg REAL,
 shaft TEXT, settings TEXT, created_at TEXT NOT NULL,
 FOREIGN KEY(club_id,user_id) REFERENCES clubs(club_id,user_id),
 UNIQUE(configuration_id,club_id,user_id), UNIQUE(club_id,revision));
CREATE TABLE bag_revisions(bag_revision_id TEXT PRIMARY KEY, bag_id TEXT NOT NULL,
 user_id TEXT NOT NULL, catalog_revision INTEGER NOT NULL, position INTEGER NOT NULL,
 name TEXT NOT NULL, active INTEGER NOT NULL CHECK(active IN (0,1)), created_at TEXT NOT NULL,
 FOREIGN KEY(bag_id,user_id) REFERENCES bags(bag_id,user_id),
 UNIQUE(bag_id,catalog_revision), UNIQUE(bag_revision_id,user_id));
CREATE TABLE bag_memberships(membership_id TEXT PRIMARY KEY, bag_revision_id TEXT NOT NULL,
 user_id TEXT NOT NULL, club_id TEXT NOT NULL, configuration_id TEXT NOT NULL,
 position INTEGER NOT NULL, label TEXT NOT NULL,
 FOREIGN KEY(bag_revision_id,user_id) REFERENCES bag_revisions(bag_revision_id,user_id),
 FOREIGN KEY(configuration_id,club_id,user_id) REFERENCES club_revisions(configuration_id,club_id,user_id),
 UNIQUE(bag_revision_id,club_id), UNIQUE(membership_id,user_id));
CREATE TABLE session_fields(session_id TEXT NOT NULL REFERENCES sessions(id), path TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('object','array','null','text','real','integer','boolean','artifact')),
 text_value TEXT, real_value REAL, integer_value INTEGER, PRIMARY KEY(session_id,path));
CREATE TABLE attempt_fields(session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, path TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('object','array','null','text','real','integer','boolean','artifact')),
 text_value TEXT, real_value REAL, integer_value INTEGER, PRIMARY KEY(session_id,ordinal,path),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal));
CREATE TABLE shot_contexts(context_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
 shot_id TEXT NOT NULL REFERENCES shots(id), user_id TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('original','correction')),
 membership_id TEXT, bag_revision_id TEXT, bag_id TEXT, bag_name TEXT, club_id TEXT, club_label TEXT,
 catalog_revision INTEGER, selection_mode TEXT, present_mask INTEGER NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 FOREIGN KEY(session_id,user_id) REFERENCES session_owners(session_id,user_id),
 FOREIGN KEY(shot_id,user_id) REFERENCES shot_owners(shot_id,user_id),
 FOREIGN KEY(membership_id,user_id) REFERENCES bag_memberships(membership_id,user_id),
 FOREIGN KEY(bag_revision_id,user_id) REFERENCES bag_revisions(bag_revision_id,user_id),
 UNIQUE(context_id,session_id,ordinal,scope));
CREATE INDEX contexts_attempt ON shot_contexts(session_id,ordinal,scope,recorded_at);
CREATE TRIGGER contexts_immutable BEFORE UPDATE ON shot_contexts BEGIN
 SELECT RAISE(ABORT,'Shot contexts are immutable; append a scoped correction'); END;
CREATE TABLE context_selection(session_id TEXT NOT NULL, ordinal INTEGER NOT NULL, scope TEXT NOT NULL,
 context_id TEXT NOT NULL REFERENCES shot_contexts(context_id), PRIMARY KEY(session_id,ordinal,scope),
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 FOREIGN KEY(context_id,session_id,ordinal,scope) REFERENCES shot_contexts(context_id,session_id,ordinal,scope));
CREATE TABLE session_plans(plan_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
 revision INTEGER NOT NULL, collection_kind TEXT NOT NULL, distance_basis TEXT NOT NULL,
 sample_goal INTEGER NOT NULL, created_at TEXT NOT NULL, UNIQUE(session_id,revision));
CREATE TABLE session_plan_items(plan_id TEXT NOT NULL REFERENCES session_plans(plan_id),
 position INTEGER NOT NULL, field TEXT NOT NULL, kind TEXT NOT NULL, text_value TEXT, real_value REAL,
 integer_value INTEGER, PRIMARY KEY(plan_id,position,field));
CREATE TABLE session_plan_selection(session_id TEXT PRIMARY KEY REFERENCES sessions(id),
 plan_id TEXT NOT NULL REFERENCES session_plans(plan_id));
CREATE TABLE tags(tag_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(user_id),
 name TEXT NOT NULL, name_key TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id,name_key));
CREATE TABLE shot_tag_events(event_id TEXT PRIMARY KEY, tag_id TEXT NOT NULL REFERENCES tags(tag_id),
 shot_id TEXT NOT NULL REFERENCES shots(id), session_id TEXT, ordinal INTEGER,
 scope TEXT NOT NULL CHECK(scope IN ('shot','attempt')), added INTEGER NOT NULL CHECK(added IN (0,1)),
 batch_id TEXT NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL,
 FOREIGN KEY(session_id,ordinal) REFERENCES session_attempts(session_id,ordinal),
 CHECK((scope='shot' AND session_id IS NULL AND ordinal IS NULL) OR
       (scope='attempt' AND session_id IS NOT NULL AND ordinal IS NOT NULL)));
CREATE INDEX tag_latest ON shot_tag_events(tag_id,shot_id,session_id,ordinal);
CREATE TRIGGER tag_ownership BEFORE INSERT ON shot_tag_events BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM shot_owners o JOIN tags t USING(user_id)
 WHERE o.shot_id=NEW.shot_id AND t.tag_id=NEW.tag_id) THEN RAISE(ABORT,'Tag and shot golfers differ') END;
 SELECT CASE WHEN NEW.scope='attempt' AND NOT EXISTS(SELECT 1 FROM session_attempts a
 WHERE a.session_id=NEW.session_id AND a.ordinal=NEW.ordinal AND a.shot_id=NEW.shot_id)
 THEN RAISE(ABORT,'Tag attempt belongs to another shot') END; END;
CREATE TRIGGER tag_events_immutable BEFORE UPDATE ON shot_tag_events BEGIN
 SELECT RAISE(ABORT,'Tag events are immutable; append a reversal'); END;
CREATE TRIGGER session_evidence_immutable BEFORE UPDATE OF payload_json ON sessions
 WHEN OLD.payload_json!=NEW.payload_json BEGIN SELECT RAISE(ABORT,'Legacy session evidence is immutable'); END;
CREATE TRIGGER attempt_evidence_immutable BEFORE UPDATE OF payload_json ON session_attempts
 WHEN OLD.payload_json!=NEW.payload_json BEGIN SELECT RAISE(ABORT,'Legacy attempt evidence is immutable'); END;
CREATE VIEW v_shot_tags AS SELECT e.* , t.user_id, t.name FROM shot_tag_events e JOIN tags t USING(tag_id)
 WHERE e.added=1 AND NOT EXISTS(SELECT 1 FROM shot_tag_events newer
 WHERE newer.tag_id=e.tag_id AND newer.shot_id=e.shot_id
 AND newer.scope=e.scope AND newer.session_id IS e.session_id AND newer.ordinal IS e.ordinal
 AND newer.rowid>e.rowid);
CREATE VIEW v_session_equipment AS SELECT a.session_id,a.ordinal,a.shot_id, o.user_id,u.display_name,
 c.context_id,c.bag_id,c.bag_name,c.club_id,c.club_label,c.catalog_revision,c.selection_mode,
 c.bag_revision_id,c.membership_id,m.configuration_id
 FROM session_attempts a JOIN session_owners o USING(session_id) JOIN users u USING(user_id)
 LEFT JOIN context_selection p ON p.session_id=a.session_id AND p.ordinal=a.ordinal
 AND p.scope=CASE WHEN EXISTS(SELECT 1 FROM context_selection x WHERE x.session_id=a.session_id
 AND x.ordinal=a.ordinal AND x.scope='correction') THEN 'correction' ELSE 'original' END
 LEFT JOIN shot_contexts c ON c.context_id=p.context_id LEFT JOIN bag_memberships m USING(membership_id);
CREATE VIEW v_session_state AS SELECT s.id session_id,o.user_id,u.display_name,s.started,s.ended,s.drill,s.deleted_at,s.revision,
 (SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/session_kind') session_kind,
 COALESCE((SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/practice_type'),'putting') practice_type,
 COALESCE((SELECT integer_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/demo'),0) simulated,
 (SELECT integer_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/game/hole_index') hole_index,
 (SELECT text_value FROM session_fields f WHERE f.session_id=s.id AND f.path='/game/lie') current_lie
 FROM sessions s JOIN session_owners o ON o.session_id=s.id JOIN users u USING(user_id);
CREATE VIEW v_attempt_outcomes AS SELECT a.session_id,a.ordinal,a.shot_id,a.legacy_key,a.target,a.success,a.excluded,
 COALESCE((SELECT integer_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/removed'),0) removed,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/swing_label') swing_label,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/game_correction/kind') shot_correction,
 (SELECT text_value FROM attempt_fields f WHERE f.session_id=a.session_id AND f.ordinal=a.ordinal AND f.path='/cleanup_reason') cleanup_reason
 FROM session_attempts a;
