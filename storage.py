"""SQLite authority for capture records and practice, with preserved source evidence."""
import contextlib
import copy
import csv
import hashlib
import io
import json
import math
import os
import re
import sqlite3
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 1
FIELDS = {
    'ball_speed': ('ball.speed', 'mph', .44704),
    'launch_ang': ('ball.launch_angle', 'deg', 1),
    'launch_dir': ('ball.launch_direction', 'deg', 1),
    'total_spin': ('ball.spin_rate', 'rpm', 1),
    'spin_axis': ('ball.spin_axis', 'deg', 1),
    'back_spin': ('ball.backspin', 'rpm', 1),
    'side_spin': ('ball.sidespin', 'rpm', 1),
    'total': ('flight.total_distance', 'yd', .9144),
    'carry': ('flight.carry_distance', 'yd', .9144),
    'offline': ('flight.total_side', 'yd', .9144),
    'descent_ang': ('flight.descent_angle', 'deg', 1),
    'peak_height': ('flight.apex_height', 'ft', .3048),
    'curve': ('flight.curve', 'yd', .9144),
    'hang_time': ('flight.flight_time', 's', 1),
}
EXTENDED_FIELDS = {'total', 'carry', 'offline', 'descent_ang', 'peak_height', 'curve', 'hang_time'}


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(value):
    return uuid.uuid5(uuid.NAMESPACE_URL, 'golfdata:' + value).hex


def database_path():
    override = os.environ.get('GOLFDATA_DATABASE')
    if override:
        return Path(override).expanduser().resolve()
    # Packaged Windows hosts virtualize AppData into their own disposable cache.
    # A user-owned folder is stable when launched from Explorer or a packaged host.
    return Path.home() / 'GolfData' / 'data' / 'golfdata.sqlite3'


def atomic_json(path, value):
    """Durable receipt/context publication; readers only see a complete JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as handle:
            handle.write(encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


SCHEMA = """
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
"""


class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.depth = 0
        self.connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False,
                                          isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA busy_timeout=5000')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            self.connection.close()
            raise OSError('Database is newer than this application; use the matching version.')
        if version == 0:
            # Schema and catalog initialization must succeed together.
            try:
                if self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise OSError('Unrecognized database; refusing to initialize over existing tables.')
                self.connection.executescript('BEGIN IMMEDIATE;\n' + SCHEMA)
                self._catalog()
                self.connection.execute('PRAGMA application_id=1196379206')
                self.connection.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                self.connection.execute('COMMIT')
            except BaseException:
                if self.connection.in_transaction:
                    self.connection.execute('ROLLBACK')
                self.connection.close()
                raise
        elif self.connection.execute('PRAGMA application_id').fetchone()[0] != 1196379206:
            self.connection.close()
            raise OSError('Unrecognized database application identity.')
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA synchronous=FULL')
        self.profile = json.loads(self.connection.execute(
            "SELECT payload FROM mapping_versions WHERE id='golfdata.foresight_screen.parsed.v1'").fetchone()[0])
        self.extended_profile = json.loads((ROOT / 'data/metric_mapping.v2.json').read_text('utf-8'))['profiles'][0]
        self.generic_profile = json.loads((ROOT / 'data/metric_mapping.normalized.v1.json').read_text('utf-8'))['profiles'][0]
        with self.transaction():
            payload = encoded(self.generic_profile)
            old = self.connection.execute('SELECT payload FROM mapping_versions WHERE id=?',(self.generic_profile['id'],)).fetchone()
            if old and old[0] != payload:raise ValueError('Normalized mapping conflicts with its archived definition.')
            self.connection.execute('INSERT OR IGNORE INTO mapping_versions VALUES(?,?,?)', (self.generic_profile['id'], digest(payload.encode()), payload))
        with self.transaction():
            payload = encoded(self.extended_profile)
            mapping_id = self.extended_profile['id']
            old = self.connection.execute('SELECT payload FROM mapping_versions WHERE id=?', (mapping_id,)).fetchone()
            if old and old[0] != payload:
                raise ValueError('Metric mapping version conflicts with its archived definition.')
            self.connection.execute('INSERT OR IGNORE INTO mapping_versions VALUES(?,?,?)',
                                    (mapping_id, digest(payload.encode()), payload))

    def equipment_catalog(self):
        from equipment import CATALOG_KEY, default_catalog
        with self.transaction():
            row = self.connection.execute('SELECT value FROM metadata WHERE key=?', (CATALOG_KEY,)).fetchone()
            if row:
                return json.loads(row[0])
            catalog = default_catalog()
            self.connection.execute('INSERT INTO metadata VALUES(?,?)', (CATALOG_KEY, encoded(catalog)))
            return catalog

    def save_equipment_catalog(self, catalog):
        from equipment import CATALOG_KEY
        with self.transaction():
            self.connection.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)', (CATALOG_KEY, encoded(catalog)))
            self._audit(CATALOG_KEY, 'edit_bags', {'revision':catalog['revision']})

    def _catalog(self):
        catalog = json.loads((ROOT / 'data/metric_catalog.v1.json').read_text('utf-8'))
        for metric in catalog['metrics']:
            self.connection.execute('INSERT INTO metric_definitions VALUES(?,?,?,?,?)',
                (metric['key'], metric['definition_version'], metric['value_type'],
                 metric.get('canonical_unit'), encoded(metric)))
        profile = json.loads((ROOT / 'data/metric_mapping.v1.json').read_text('utf-8'))['profiles'][0]
        # Keep v1 immutable; expanded flight columns use a separately registered v2 mapping.
        profile = copy.deepcopy(profile)
        profile['fields'] = [f for f in profile['fields'] if f['source_field'] in FIELDS]
        profile['status'] = 'active_for_current_golfdata_parsed_fields'
        payload = encoded(profile)
        self.mapping_id = profile['id']
        self.connection.execute('INSERT INTO mapping_versions VALUES(?,?,?)',
                                (self.mapping_id, digest(payload.encode()), payload))

    @contextlib.contextmanager
    def transaction(self):
        with self.lock:
            outer = self.depth == 0
            try:
                if outer:
                    self.connection.execute('BEGIN IMMEDIATE')
                self.depth += 1
                try:
                    yield self.connection
                finally:
                    self.depth -= 1
                if outer:
                    self.connection.execute('COMMIT')
            except BaseException as exc:
                if outer and self.connection.in_transaction:
                    self.connection.execute('ROLLBACK')
                if isinstance(exc, sqlite3.Error):
                    raise OSError(f'SQLite save failed: {exc}') from exc
                raise

    def close(self):
        with self.lock:
            self.connection.close()

    def count(self, table):
        if table not in ('shots','ingest_events','sessions','session_attempts','observations','metric_values','import_files'):
            raise ValueError('Unknown table.')
        with self.lock:
            return self.connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]

    def migrated(self):
        with self.lock:
            return bool(self.connection.execute("SELECT 1 FROM metadata WHERE key='legacy_import_complete'").fetchone())

    def _audit(self, entity, action, payload):
        self.connection.execute('INSERT INTO audit_events VALUES(?,?,?,?,?)',
            (uuid.uuid4().hex, entity, action, now(), encoded(payload)))

    def ingest(self, event, event_id=None, provenance='live_capture', file_id=None, row=None):
        """Receipt is immutable; successful delivery is never replayed from storage."""
        event_id = event_id or event.get('receipt_id') or identity('unspooled:' + encoded(event))
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}',event_id):
            raise ValueError('Invalid receipt identifier.')
        with self.transaction():
            existing = self.connection.execute('SELECT raw_json FROM ingest_events WHERE id=?', (event_id,)).fetchone()
            if existing:
                if existing['raw_json'] != encoded(event):
                    raise ValueError('Receipt identifier conflicts with different data.')
                return event_id, False
            source = event.get('source_configuration', {'acquisition': 'screen_ocr', 'profile': 'legacy_unknown'})
            source_id = identity('source:' + encoded(source))
            self.connection.execute('INSERT OR IGNORE INTO sources VALUES(?,?)', (source_id, encoded(source)))
            legacy_key = f"{event.get('session_id','unknown')}:{event.get('seq','unknown')}"
            stream_id = identity('stream:' + provenance + ':' + str(event.get('producer_id') or file_id) + ':' + str(event.get('session_id')))
            self.connection.execute('INSERT OR IGNORE INTO capture_streams VALUES(?,?,?)',
                                    (stream_id, source_id, str(event.get('session_id',''))))
            result = event.get('result', 'unknown')
            accepted = result in ('sent','validated')
            acceptance = 'accepted' if accepted else result if result in ('failed','logged') else 'unknown'
            when = event.get('captured_at') or event.get('source_time')
            basis = 'utc_receipt' if event.get('captured_at') else 'local_timezone_unknown'
            self.connection.execute('INSERT INTO ingest_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                (event_id, stream_id, legacy_key, event.get('source_time') or event.get('time'),
                 event.get('captured_at'), basis, acceptance, encoded(event), file_id, row))
            return self._observation(event_id, event, accepted, when, basis, provenance), True

    def _observation(self, event_id, event, accepted, when, basis, provenance):
        shot_id = identity('shot:' + event_id) if accepted else None
        if accepted:
            self.connection.execute('INSERT INTO shots VALUES(?,?,?,?,?)',
                (shot_id, event_id, when, basis, event.get('club')))
        observation_id = identity('observation:' + event_id)
        profile = self.generic_profile if event.get('mapping_id') == 'traceloft.normalized.v1' else self.extended_profile if EXTENDED_FIELDS.intersection(event.get('vals', {})) else self.profile
        mapping_id = profile['id']
        self.connection.execute('INSERT INTO observations VALUES(?,?,?,?,?)',
            (observation_id, event_id, shot_id, mapping_id, provenance))
        for mapping in profile['fields']:
            field, metric, unit = mapping['source_field'], mapping['metric'], mapping['source_unit']
            operation = mapping['transform']['operation']
            if operation not in ('identity','scale'):
                raise ValueError('Unsupported archived metric transform.')
            factor = mapping['transform'].get('factor',1)
            value = event.get('vals', {}).get(field)
            valid = isinstance(value, (int,float)) and not isinstance(value, bool) and math.isfinite(value)
            availability = 'available' if valid else 'unavailable' if value is None else 'invalid'
            self.connection.execute('INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (observation_id, metric, 1, float(value)*factor if valid else None, None, None, None,
                 field, unit, encoded(value), availability, 'synthetic_demo' if event.get('simulated') else mapping.get('method', 'provider_unknown'),
                 mapping['semantic_variant']))
        self.connection.execute('INSERT INTO delivery_events VALUES(?,?,?,?)',
            (identity('delivery:' + event_id), event_id,
             'socket_write_reported_unacknowledged' if event.get('result') == 'sent' else 'not_established',
             encoded({'result': event.get('result'), 'note':event.get('note'), 'sent_fields':event.get('sent_fields')})))
        return event_id

    def load_session(self, session_id, deleted=False):
        if not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('Invalid session identifier.')
        with self.lock:
            row = self.connection.execute('SELECT payload_json FROM sessions WHERE id=? AND (deleted_at IS NOT NULL)=?',
                                          (session_id, int(deleted))).fetchone()
            if not row:
                raise FileNotFoundError('Session not found.')
            return json.loads(row[0])

    def list_sessions(self, deleted=False):
        with self.lock:
            return [json.loads(r[0]) for r in self.connection.execute(
                'SELECT payload_json FROM sessions WHERE (deleted_at IS NOT NULL)=? ORDER BY started DESC', (int(deleted),))]

    def save_session(self, data, imported=False, deleted=False):
        with self.transaction():
            sid = data['id']
            old = self.connection.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
            if old and old['deleted_at'] and not imported:
                raise ValueError('This session has been deleted; restore it before editing.')
            if old and imported:
                if old['payload_json'] != encoded(data) or bool(old['deleted_at']) != deleted:
                    raise ValueError(f'Conflicting legacy copies of session {sid}.')
                return
            self.connection.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                'started=excluded.started, ended=excluded.ended, drill=excluded.drill, revision=sessions.revision+1, payload_json=excluded.payload_json',
                (sid, data['started'], data.get('ended'), data['drill'], now() if deleted else None, 1, encoded(data)))
            for ordinal, shot in enumerate(data['shots'], 1):
                previous = self.connection.execute('SELECT * FROM session_attempts WHERE session_id=? AND legacy_key=?',
                                                   (sid,shot['key'])).fetchone()
                if previous:
                    shot_id, obs_id = previous['shot_id'], previous['observation_id']
                    if previous['excluded'] != int(shot['excluded']):
                        self.connection.execute('INSERT INTO inclusion_decisions VALUES(?,?,?,?,?,?)',
                            (uuid.uuid4().hex,sid,shot['key'],int(shot['excluded']),'manual_session_only',now()))
                else:
                    receipt_id = shot.get('receipt_id')
                    candidates = self.connection.execute('SELECT id FROM ingest_events WHERE legacy_key=? AND import_file_id IS NOT NULL', (shot['key'],)).fetchall() if imported else []
                    linked = receipt_id or (candidates[0]['id'] if len(candidates)==1 else None)
                    shared = self.connection.execute('SELECT o.shot_id FROM observations o WHERE event_id=?', (linked,)).fetchone() if linked else None
                    if shared and not shared['shot_id']:
                        linked_shot = identity('shot:' + linked)
                        self.connection.execute('INSERT INTO shots VALUES(?,?,?,?,?)', (linked_shot, linked, shot.get('captured'),'utc_practice_receipt',None))
                        self.connection.execute("UPDATE ingest_events SET acceptance='accepted' WHERE id=?", (linked,))
                        self.connection.execute('UPDATE observations SET shot_id=? WHERE event_id=?',(linked_shot,linked))
                    else:
                        linked_shot = shared['shot_id'] if shared else None
                    event_id = identity('practice:' + sid + ':' + shot['key'])
                    event = dict(session_id=shot['key'].rsplit(':',1)[0], seq=shot['key'].rsplit(':',1)[-1],
                                 captured_at=shot.get('captured'), result='validated', vals=shot['vals'],
                                 practice_session_id=sid, linking='unique_legacy_key' if linked_shot else 'unresolved_or_practice_only')
                    if shot.get('simulated'):
                        event.update(simulated=True,source_configuration={'acquisition':'synthetic_demo','generator':'golfdata-demo-v1'})
                    self.ingest(event, event_id, 'legacy_practice' if imported else 'practice_measurements')
                    obs_id = identity('observation:' + event_id)
                    own_shot = identity('shot:' + event_id)
                    shot_id = linked_shot or own_shot
                    if linked_shot:
                        self.connection.execute('UPDATE observations SET shot_id=? WHERE id=?',(linked_shot,obs_id))
                        self.connection.execute('DELETE FROM shots WHERE id=?',(own_shot,))
                self.connection.execute('INSERT INTO session_attempts VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(session_id,ordinal) DO UPDATE SET '
                    'excluded=excluded.excluded,payload_json=excluded.payload_json',
                    (sid,ordinal,shot['key'],shot_id,obs_id,shot.get('captured'),shot.get('target',data['target']),
                     int(shot['success']),int(shot['excluded']),encoded(shot)))
            self._audit(sid, 'import_session' if imported else 'save_session', {'shots':len(data['shots'])})

    def set_deleted(self, session_id, deleted):
        with self.transaction():
            self.load_session(session_id, deleted=not deleted)
            self.connection.execute('UPDATE sessions SET deleted_at=?, revision=revision+1 WHERE id=?',
                                    (now() if deleted else None, session_id))
            self._audit(session_id, 'delete' if deleted else 'restore', {})

    def backup(self, directory=None):
        directory = Path(directory or self.path.parent / 'backups')
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / ('golfdata-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8] + '.sqlite3')
        with self.lock:
            with contextlib.closing(sqlite3.connect(target)) as destination:
                self.connection.backup(destination)
                destination.execute('PRAGMA journal_mode=DELETE')
                if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or destination.execute('PRAGMA foreign_key_check').fetchall():
                    raise OSError('Backup integrity verification failed.')
                counts = {t:destination.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('shots','ingest_events','sessions','session_attempts')}
        atomic_json(target.with_suffix('.manifest.json'), dict(schema=SCHEMA_VERSION,created=now(),sha256=digest(target.read_bytes()),counts=counts,
                     protection='local_only', includes='database and embedded imported evidence; crop/training archives remain separate'))
        return target

    def export(self):
        """One committed snapshot, separate observation rows, blank unavailable cells."""
        with self.transaction():
            metric_cursor = self.connection.execute('''SELECT o.shot_id, s.occurred_at, s.time_basis, s.reported_club,
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
            attempt_cursor = self.connection.execute('SELECT a.*,s.deleted_at FROM session_attempts a JOIN sessions s ON s.id=a.session_id ORDER BY a.session_id,a.ordinal')
            attempt_fields = [d[0] for d in attempt_cursor.description]
            attempts = [dict(r) for r in attempt_cursor]
            # Derived putting outcomes belong to attempts, never to measured ball metrics.
            distance_fields = ['estimated_distance_ft','target_distance_ft','distance_error_ft',
                               'distance_model_id','stimp_ft','ladder_rung','ladder_round',
                               'target_mode','distance_tolerance_ft','distance_source_revision',
                               'target_distance_yd','distance_yd','distance_error_yd','distance_metric',
                               'scored','unscored_reason','club_label','distance_tolerance_yd','swing_label',
                               'bag_id','bag_name','club_id','catalog_revision','selection_mode',
                               'simulated','removed','cleanup_reason','corrected_equipment','flight']
            attempt_fields += distance_fields
            contexts = {r['id']:json.loads(r['payload_json']) for r in self.connection.execute('SELECT id,payload_json FROM sessions')}
            for attempt in attempts:
                outcome = json.loads(attempt['payload_json'])
                context = contexts[attempt['session_id']]
                for field in distance_fields:
                    attempt[field] = outcome.get(field)
                attempt['target_mode'] = context.get('target_mode')
                attempt['distance_tolerance_ft'] = context.get('distance_tolerance')
                attempt['distance_tolerance_yd'] = context.get('range_tolerance')
                attempt['distance_source_revision'] = context.get('distance_model',{}).get('source_revision')
            shot_cursor = self.connection.execute('SELECT * FROM shots ORDER BY occurred_at,id')
            shot_fields = [d[0] for d in shot_cursor.description] + ['simulated'] + [field+'_'+('degrees' if unit=='deg' else unit) for field,(_,unit,_) in FIELDS.items()]
            shots = [dict(r) for r in shot_cursor]
            simulated_events={r['id'] for r in self.connection.execute('SELECT id,raw_json FROM ingest_events') if json.loads(r['raw_json']).get('simulated')}
            for shot in shots:
                shot['simulated']=shot['event_id'] in simulated_events
            by_shot = {}
            for value in metrics:
                by_shot.setdefault(value['shot_id'],[]).append(value)
            for shot in shots:
                # Prefer exact practice/live observation to rounded legacy CSV; retain all in long export.
                values = by_shot.get(shot['id'],[])
                values.sort(key=lambda v: v['provenance']=='legacy_csv')
                for field,(metric,unit,factor) in FIELDS.items():
                    found = next((v for v in values if v['metric_key']==metric and v['availability']=='available'),None)
                    shot[field + '_' + ('degrees' if unit=='deg' else unit)] = found['real_value']/factor if found else None
            files = {'shots.csv': shots, 'metric_values.csv':metrics, 'session_attempts.csv':attempts}
            output = io.BytesIO()
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
                for name,rows in files.items():
                    text = io.StringIO(newline='')
                    fields = {'shots.csv':shot_fields,'metric_values.csv':metric_fields,'session_attempts.csv':attempt_fields}[name]
                    writer = csv.DictWriter(text, fields)
                    writer.writeheader()
                    # Protect spreadsheet text while preserving genuine numeric values.
                    writer.writerows({k: "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()} for row in rows)
                    archive.writestr(name,text.getvalue().encode('utf-8-sig'))
                archive.writestr('manifest.json',encoded(dict(schema=SCHEMA_VERSION,created=now(),scope='all_captured_including_session_exclusions_and_deleted_sessions',
                    counts={name:len(rows) for name,rows in files.items()}, missing='blank; see availability in long export',
                    timestamps='time_basis declares UTC receipts versus timezone-unknown legacy local times',text_safety='formula-leading text prefixed with apostrophe')))
                archive.writestr('metric_catalog.json',encoded([json.loads(r[0]) for r in self.connection.execute('SELECT definition_json FROM metric_definitions ORDER BY key,version')]))
                archive.writestr('metric_mappings.json',encoded([json.loads(r[0]) for r in self.connection.execute('SELECT payload FROM mapping_versions ORDER BY id')]))
                archive.writestr('putting_models.json',encoded({sid:context['distance_model'] for sid,context in contexts.items() if context.get('distance_model')}))
            return output.getvalue()


def legacy_files(root):
    root = Path(root)
    return sorted(root.glob('shots*.csv')) + sorted((root/'practice_sessions').glob('*.json')) + sorted((root/'practice_sessions'/'.trash').glob('*.json'))


def inspect_legacy(root):
    files = []
    for path in legacy_files(root):
        content = path.read_bytes()
        if path.suffix == '.csv':
            count = len(list(csv.DictReader(io.StringIO(content.decode('utf-8-sig')))))
        else:
            data = json.loads(content.decode('utf-8-sig'))
            count = len(data['shots'])
            if data['id'] != path.stem or not re.fullmatch('[0-9a-f]{32}',path.stem):
                raise ValueError(f'Invalid session identity in {path.name}.')
        files.append(dict(path=str(path.resolve()),sha256=digest(content),rows=count,bytes=len(content)))
    return files


def import_legacy(store, root):
    """All-or-nothing, exact-file evidence, repeat-safe import. Originals never rewritten."""
    inventory = inspect_legacy(root)
    before = {t:store.count(t) for t in ('ingest_events','shots','sessions','session_attempts')}
    with store.transaction():
        seen_csv = {r[0] for r in store.connection.execute("SELECT hash FROM import_files WHERE path LIKE '%.csv'")}
        for item in inventory:
            path = Path(item['path'])
            content = path.read_bytes()
            if digest(content) != item['sha256']:
                raise OSError('Legacy data changed during import; retry after stopping capture.')
            file_id = identity('file:' + str(path) + ':' + item['sha256'])
            existing = store.connection.execute('SELECT 1 FROM import_files WHERE id=?',(file_id,)).fetchone()
            if existing:
                continue
            # Changed originals are not silently imported a second time.
            if store.connection.execute('SELECT 1 FROM import_files WHERE path=?',(str(path),)).fetchone():
                raise ValueError(f'{path.name} changed after import; reconcile before importing again.')
            store.connection.execute('INSERT INTO import_files VALUES(?,?,?,?,?)',
                                     (file_id,str(path),item['sha256'],content,now()))
            if path.suffix == '.csv':
                if item['sha256'] in seen_csv:
                    continue
                seen_csv.add(item['sha256'])
                for ordinal,row in enumerate(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))),1):
                    vals = {}
                    for key in FIELDS:
                        raw = row.get(key)
                        try:
                            value = float(raw) if raw not in ('',None) else None
                            vals[key] = value if value is None or math.isfinite(value) else raw
                        except (ValueError,TypeError):
                            vals[key] = raw
                    note = row.get('note','')
                    accepted = bool(re.match(r'^ok(?: \(no GSPro\))?(?:;|$)',note))
                    result = ('sent' if row.get('sent','').lower()=='true' else 'validated') if accepted else 'unknown'
                    event = dict(session_id=row.get('session_id'),seq=row.get('seq'),source_time=row.get('time'),
                        club=row.get('club'),vals=vals,note=note,result=result,legacy_row=row,
                        sent_fields={k:v for k,v in row.items() if k.startswith('sent_')})
                    store.ingest(event,identity('csv:' + file_id + ':' + str(ordinal)), 'legacy_csv',file_id,ordinal)
            else:
                data = json.loads(content.decode('utf-8-sig'))
                store.save_session(data, imported=True, deleted=path.parent.name=='.trash')
        after = {t:store.count(t) for t in before}
        report = dict(created=now(),files=inventory,before=before,after=after,added={t:after[t]-before[t] for t in before},
                      caveats=['CSV acceptance requires explicit ok note or unique confirmed practice evidence.',
                               'Unresolved colliding legacy keys remain separate shots/observations.',
                               'Legacy CSV local timestamps have unknown timezone; original evidence is embedded.'])
        store.connection.execute("INSERT OR REPLACE INTO metadata VALUES('legacy_import_complete',?)",(encoded(report),))
        store._audit('database','legacy_import',report)
    return report
