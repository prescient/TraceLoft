"""SQLite authority for capture records and practice, with preserved source evidence."""

import contextlib
import copy
import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 5
FIELDS = {
    'ball_speed': ('ball.speed', 'mph', 0.44704),
    'launch_ang': ('ball.launch_angle', 'deg', 1),
    'launch_dir': ('ball.launch_direction', 'deg', 1),
    'total_spin': ('ball.spin_rate', 'rpm', 1),
    'spin_axis': ('ball.spin_axis', 'deg', 1),
    'back_spin': ('ball.backspin', 'rpm', 1),
    'side_spin': ('ball.sidespin', 'rpm', 1),
    'total': ('flight.total_distance', 'yd', 0.9144),
    'carry': ('flight.carry_distance', 'yd', 0.9144),
    'offline': ('flight.total_side', 'yd', 0.9144),
    'descent_ang': ('flight.descent_angle', 'deg', 1),
    'peak_height': ('flight.apex_height', 'ft', 0.3048),
    'curve': ('flight.curve', 'yd', 0.9144),
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
    def __init__(self, path, migration_lease_held=False):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.depth = 0
        self._attempt_cache = {}
        self._attempt_updates = {}
        self._monitor = None
        self._monitor_lock = threading.Lock()
        self._writer_thread = None
        self._background = []
        self.connection = sqlite3.connect(
            self.path, timeout=5, check_same_thread=False, isolation_level=None
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA busy_timeout=5000')
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > SCHEMA_VERSION:
            self.connection.close()
            raise OSError('Database is newer than this application; use the matching version.')
        new_database = version == 0
        if version == 0:
            # Schema and catalog initialization must succeed together.
            try:
                if self.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchone():
                    raise OSError(
                        'Unrecognized database; refusing to initialize over existing tables.'
                    )
                self.connection.executescript('BEGIN IMMEDIATE;\n' + SCHEMA)
                self._catalog()
                self.connection.execute('PRAGMA application_id=1196379206')
                self.connection.execute('PRAGMA user_version=1')
                self.connection.execute('COMMIT')
            except BaseException:
                if self.connection.in_transaction:
                    self.connection.execute('ROLLBACK')
                self.connection.close()
                raise
        elif self.connection.execute('PRAGMA application_id').fetchone()[0] != 1196379206:
            self.connection.close()
            raise OSError('Unrecognized database application identity.')
        try:
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('PRAGMA synchronous=FULL')
            from migrations import upgrade

            upgrade(self, new_database, migration_lease_held)
        except BaseException:
            self.connection.close()
            raise
        self.profile = json.loads(
            self.connection.execute(
                "SELECT payload FROM mapping_versions WHERE id='golfdata.foresight_screen.parsed.v1'"
            ).fetchone()[0]
        )
        self.extended_profile = json.loads(
            (ROOT / 'data/metric_mapping.v2.json').read_text('utf-8')
        )['profiles'][0]
        self.generic_profile = json.loads(
            (ROOT / 'data/metric_mapping.normalized.v2.json').read_text('utf-8')
        )['profiles'][0]
        with self.transaction():
            payload = encoded(self.generic_profile)
            old = self.connection.execute(
                'SELECT payload FROM mapping_versions WHERE id=?', (self.generic_profile['id'],)
            ).fetchone()
            if old and old[0] != payload:
                raise ValueError('Normalized mapping conflicts with its archived definition.')
            self.connection.execute(
                'INSERT OR IGNORE INTO mapping_versions VALUES(?,?,?)',
                (self.generic_profile['id'], digest(payload.encode()), payload),
            )
        with self.transaction():
            payload = encoded(self.extended_profile)
            mapping_id = self.extended_profile['id']
            old = self.connection.execute(
                'SELECT payload FROM mapping_versions WHERE id=?', (mapping_id,)
            ).fetchone()
            if old and old[0] != payload:
                raise ValueError('Metric mapping version conflicts with its archived definition.')
            self.connection.execute(
                'INSERT OR IGNORE INTO mapping_versions VALUES(?,?,?)',
                (mapping_id, digest(payload.encode()), payload),
            )

    def write_derived_result(self, *args, **kwargs):
        """Append an analytical version; select=True explicitly publishes for analysis only."""
        from shot_schema import write_result

        with self.transaction():
            return write_result(self.connection, *args, **kwargs)

    def analysis(self, params):
        from analysis_schema import report

        with self.reading() as connection:
            return report(connection, params)

    def stage_calculations(self, family, filters, putting_model='saved'):
        from recalculation import stage

        return stage(self, family, filters, putting_model)

    def resume_calculations(self, batch_id):
        from recalculation import resume

        return resume(self, batch_id)

    def publish_calculations(self, batch_id, token):
        from recalculation import publish

        return publish(self, batch_id, token)

    def calculation_snapshot(self, batch_id):
        from recalculation import snapshot

        with self.reading() as connection:
            return snapshot(connection, batch_id)

    def calculation_history(self, shot_id):
        from recalculation import history

        with self.reading() as connection:
            return history(connection, shot_id)

    def calculation_batches(self):
        from domain_schema import active_user

        with self.reading() as connection:
            return [
                dict(r)
                for r in connection.execute(
                    'SELECT * FROM recalculation_batches WHERE user_id=? ORDER BY created_at DESC LIMIT 100',
                    (active_user(connection),),
                )
            ]

    def calculation_history_csv(self):
        from recalculation import csv_history

        with self.reading() as connection:
            return csv_history(connection)

    def collection_analysis(self, session_id):
        from analysis_schema import collection_snapshot
        from domain_schema import active_user

        with self.reading() as connection:
            owner = connection.execute(
                'SELECT user_id FROM session_owners WHERE session_id=?', (session_id,)
            ).fetchone()
            if (owner[0] if owner else None) != active_user(connection):
                raise ValueError('Switch golfer to view this collection.')
            return collection_snapshot(connection, session_id)

    def select_equipment_profile(self, session_id):
        from analysis_schema import select_profile

        with self.transaction():
            aid = select_profile(self.connection, session_id)
            self.audit(session_id, 'publish_equipment_profile', dict(analysis_id=aid))
            return aid

    def active_user(self):
        from domain_schema import active_user

        with self.lock:
            return active_user(self.connection)

    def users(self):
        with self.lock:
            return [
                dict(r)
                for r in self.connection.execute(
                    'SELECT * FROM users WHERE archived_at IS NULL ORDER BY created_at,user_id'
                )
            ]

    def golfers(self):
        """Committed golfer list and selection, read without waiting for the writer lock."""
        from domain_schema import active_user

        with self._monitor_lock:
            monitor = self._monitor_connection()
            users = [
                dict(r)
                for r in monitor.execute(
                    'SELECT * FROM users WHERE archived_at IS NULL ORDER BY created_at,user_id'
                )
            ]
            return users, active_user(monitor)

    def create_user(self, name, handedness='right_handed'):
        from equipment import text, default_catalog
        from domain_schema import save_catalog

        name = text(name, 'Golfer name')
        if handedness not in ('right_handed', 'left_handed'):
            raise ValueError('Choose a valid handedness.')
        uid = uuid.uuid4().hex
        with self.transaction():
            self.connection.execute(
                'INSERT INTO users VALUES(?,?,?,?,?)', (uid, name, handedness, now(), None)
            )
            save_catalog(self.connection, default_catalog(), uid)
            self.audit(uid, 'create_golfer', dict(name=name, handedness=handedness))
        return uid

    def select_user(self, user_id):
        with self.transaction():
            if not self.connection.execute(
                'SELECT 1 FROM users WHERE user_id=? AND archived_at IS NULL', (user_id,)
            ).fetchone():
                raise ValueError('Golfer not found.')
            self.connection.execute(
                'UPDATE golfer_selection SET user_id=? WHERE singleton=1', (user_id,)
            )
            self.audit(user_id, 'select_golfer', {})

    def session_owner(self, session_id):
        with self.lock:
            row = self.connection.execute(
                'SELECT user_id FROM session_owners WHERE session_id=?', (session_id,)
            ).fetchone()
            return row[0] if row else None

    def edit_tags(
        self,
        session_id,
        keys,
        name,
        action='add',
        scope='attempt',
        reason='Manual tag',
        batch_id=None,
    ):
        """Append associations atomically; an attempt tag never leaks to other sessions."""
        from equipment import text

        if action not in ('add', 'remove', 'undo') or scope not in ('shot', 'attempt'):
            raise ValueError('Choose a valid tag action and scope.')
        with self.transaction():
            user = self.active_user()
            if self.session_owner(session_id) != user:
                raise ValueError('Switch golfer before tagging this session.')
            if action == 'undo':
                row = self.connection.execute(
                    "SELECT payload_json FROM audit_events WHERE entity_id=? AND action='tag_batch' AND id=?",
                    (session_id, batch_id),
                ).fetchone()
                if not row:
                    raise ValueError('Tag batch not found.')
                items = json.loads(row[0])['items']
                for item in items:
                    last = self.connection.execute(
                        'SELECT batch_id FROM shot_tag_events WHERE tag_id=? AND shot_id=? AND session_id IS ? AND ordinal IS ? ORDER BY rowid DESC LIMIT 1',
                        (item['tag_id'], item['shot_id'], item['session_id'], item['ordinal']),
                    ).fetchone()
                    if not last or last[0] != batch_id:
                        raise ValueError('Tags changed since this batch; refresh before undoing.')
            else:
                name = text(name, 'Tag')
                reason = text(reason, 'Reason')
                if not keys or len(keys) > 1000 or len(set(keys)) != len(keys):
                    raise ValueError('Select 1–1000 distinct shots.')
                tag = self.connection.execute(
                    'SELECT tag_id FROM tags WHERE user_id=? AND name_key=?',
                    (user, name.casefold()),
                ).fetchone()
                tid = tag[0] if tag else uuid.uuid4().hex
                if not tag:
                    self.connection.execute(
                        'INSERT INTO tags VALUES(?,?,?,?,?)',
                        (tid, user, name, name.casefold(), now()),
                    )
                links = {
                    r['legacy_key']: r
                    for r in self.connection.execute(
                        'SELECT * FROM session_attempts WHERE session_id=?', (session_id,)
                    )
                }
                if any(k not in links for k in keys):
                    raise ValueError('Selection includes a shot outside this session.')
                items = []
                seen = set()
                for key in keys:
                    link = links[key]
                    sid = session_id if scope == 'attempt' else None
                    ordinal = link['ordinal'] if scope == 'attempt' else None
                    if (link['shot_id'], sid, ordinal) in seen:
                        continue
                    seen.add((link['shot_id'], sid, ordinal))
                    old = self.connection.execute(
                        'SELECT added FROM shot_tag_events WHERE tag_id=? AND shot_id=? AND session_id IS ? AND ordinal IS ? ORDER BY rowid DESC LIMIT 1',
                        (tid, link['shot_id'], sid, ordinal),
                    ).fetchone()
                    items.append(
                        dict(
                            tag_id=tid,
                            shot_id=link['shot_id'],
                            session_id=sid,
                            ordinal=ordinal,
                            scope=scope,
                            before=bool(old and old[0]),
                            after=action == 'add',
                        )
                    )
            batch = uuid.uuid4().hex
            for item in items:
                self.connection.execute(
                    'INSERT INTO shot_tag_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (
                        uuid.uuid4().hex,
                        item['tag_id'],
                        item['shot_id'],
                        item['session_id'],
                        item['ordinal'],
                        item['scope'],
                        int(item['before'] if action == 'undo' else item['after']),
                        batch,
                        reason,
                        now(),
                    ),
                )
            self.connection.execute(
                'INSERT INTO audit_events VALUES(?,?,?,?,?)',
                (
                    batch,
                    session_id,
                    'tag_batch',
                    now(),
                    encoded(dict(action=action, items=items, undo_of=batch_id)),
                ),
            )
            return batch

    def session_tags(self, session_id):
        with self.lock:
            if self.session_owner(session_id) != self.active_user():
                raise ValueError('Switch golfer to view tags.')
            rows = self.connection.execute(
                '''SELECT a.legacy_key,t.tag_id,t.name,t.scope FROM session_attempts a
                JOIN v_shot_tags t ON t.shot_id=a.shot_id AND (t.scope='shot' OR (t.session_id=a.session_id AND t.ordinal=a.ordinal))
                WHERE a.session_id=? ORDER BY t.name,t.scope''',
                (session_id,),
            )
            result = {}
            for r in rows:
                result.setdefault(r['legacy_key'], []).append(
                    dict(tag_id=r['tag_id'], name=r['name'], scope=r['scope'])
                )
            return result

    def equipment_catalog(self):
        from domain_schema import read_catalog

        with self.lock:
            return read_catalog(self.connection)

    def save_equipment_catalog(self, catalog):
        from domain_schema import save_catalog

        with self.transaction():
            save_catalog(self.connection, catalog, self.active_user())
            self.audit(self.active_user(), 'edit_bags', {'revision': catalog['revision']})

    def _catalog(self):
        catalog = json.loads((ROOT / 'data/metric_catalog.v1.json').read_text('utf-8'))
        for metric in catalog['metrics']:
            self.connection.execute(
                'INSERT INTO metric_definitions VALUES(?,?,?,?,?)',
                (
                    metric['key'],
                    metric['definition_version'],
                    metric['value_type'],
                    metric.get('canonical_unit'),
                    encoded(metric),
                ),
            )
        profile = json.loads((ROOT / 'data/metric_mapping.v1.json').read_text('utf-8'))['profiles'][
            0
        ]
        # Keep v1 immutable; expanded flight columns use a separately registered v2 mapping.
        profile = copy.deepcopy(profile)
        profile['fields'] = [f for f in profile['fields'] if f['source_field'] in FIELDS]
        profile['status'] = 'active_for_current_golfdata_parsed_fields'
        payload = encoded(profile)
        self.mapping_id = profile['id']
        self.connection.execute(
            'INSERT INTO mapping_versions VALUES(?,?,?)',
            (self.mapping_id, digest(payload.encode()), payload),
        )

    @contextlib.contextmanager
    def transaction(self):
        with self.lock:
            outer = self.depth == 0
            try:
                if outer:
                    self.connection.execute('BEGIN IMMEDIATE')
                    self._attempt_updates = {}
                    self._writer_thread = threading.get_ident()
                self.depth += 1
                try:
                    yield self.connection
                finally:
                    self.depth -= 1
                    if outer:
                        self._writer_thread = None
                if outer:
                    self.connection.execute('COMMIT')
                    self._attempt_cache.update(self._attempt_updates)
                    while len(self._attempt_cache) > 8:
                        del self._attempt_cache[next(iter(self._attempt_cache))]
                    self._attempt_updates = {}
            except BaseException as exc:
                if outer and self.connection.in_transaction:
                    self.connection.execute('ROLLBACK')
                    self._attempt_updates = {}
                if isinstance(exc, sqlite3.Error):
                    raise OSError(f'SQLite save failed: {exc}') from exc
                raise

    def backup_in_background(self, on_error):
        """Copy and verify on a worker thread; close() waits for outstanding copies."""

        def run():
            try:
                self.backup()
            except (OSError, sqlite3.Error) as exc:
                on_error(exc)

        thread = threading.Thread(target=run, name='traceloft-backup')
        with self._monitor_lock:
            self._background = [t for t in self._background if t.is_alive()] + [thread]
        thread.start()
        return thread

    def wait_for_background(self):
        with self._monitor_lock:
            threads = list(self._background)
        for thread in threads:
            thread.join()

    def close(self):
        self.wait_for_background()
        with self.lock:
            with self._monitor_lock:
                if self._monitor:
                    self._monitor.close()
                    self._monitor = None
            self.connection.close()

    def _read_connection(self):
        connection = sqlite3.connect(
            self.path.as_uri() + '?mode=ro',
            uri=True,
            timeout=5,
            check_same_thread=False,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA busy_timeout=5000')
        return connection

    def _monitor_connection(self):
        if self._monitor is None:
            self._monitor = self._read_connection()
        return self._monitor

    @contextlib.contextmanager
    def reading(self):
        """A private read-only connection pinned to one committed snapshot.

        WAL readers never wait for the writer, so long reports, exports and backups
        do not hold `self.lock`, which the event loop needs for shot intake. Inside the
        caller's own write transaction it yields the writer connection instead, so the
        caller still sees its uncommitted changes.
        """
        if self.writing_here():
            yield self.connection
            return
        connection = self._read_connection()
        try:
            connection.execute('BEGIN')
            # A deferred transaction fixes its snapshot at the first read.
            connection.execute('SELECT count(*) FROM metadata').fetchone()
            yield connection
        finally:
            if connection.in_transaction:
                connection.execute('ROLLBACK')
            connection.close()

    def writing_here(self):
        """True inside a write transaction opened by the calling thread.

        A snapshot reader cannot see that transaction's uncommitted rows, so callers
        that need them must read through `self.connection` instead.
        """
        return self.depth > 0 and self._writer_thread == threading.get_ident()

    def committed_version(self):
        """A value that changes after every commit, read without the writer lock.

        `PRAGMA data_version` on a separate connection changes whenever another
        connection commits, so uncommitted work in progress is never announced.
        """
        with self._monitor_lock:
            return self._monitor_connection().execute('PRAGMA data_version').fetchone()[0]

    def count(self, table):
        if table not in (
            'shots',
            'ingest_events',
            'sessions',
            'session_attempts',
            'observations',
            'metric_values',
            'import_files',
        ):
            raise ValueError('Unknown table.')
        with self.lock:
            return self.connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]

    def migrated(self):
        with self.lock:
            return bool(
                self.connection.execute(
                    "SELECT 1 FROM metadata WHERE key='legacy_import_complete'"
                ).fetchone()
            )

    def audit(self, entity, action, payload):
        self.connection.execute(
            'INSERT INTO audit_events VALUES(?,?,?,?,?)',
            (uuid.uuid4().hex, entity, action, now(), encoded(payload)),
        )

    def ingest(self, event, event_id=None, provenance='live_capture', file_id=None, row=None):
        """Receipt is immutable; successful delivery is never replayed from storage."""
        event_id = event_id or event.get('receipt_id') or identity('unspooled:' + encoded(event))
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}', event_id):
            raise ValueError('Invalid receipt identifier.')
        with self.transaction():
            existing = self.connection.execute(
                'SELECT raw_json FROM ingest_events WHERE id=?', (event_id,)
            ).fetchone()
            if existing:
                if existing['raw_json'] != encoded(event):
                    raise ValueError('Receipt identifier conflicts with different data.')
                return event_id, False
            source = event.get(
                'source_configuration', {'acquisition': 'screen_ocr', 'profile': 'legacy_unknown'}
            )
            source_id = identity('source:' + encoded(source))
            self.connection.execute(
                'INSERT OR IGNORE INTO sources VALUES(?,?)', (source_id, encoded(source))
            )
            legacy_key = f"{event.get('session_id', 'unknown')}:{event.get('seq', 'unknown')}"
            stream_id = identity(
                'stream:'
                + provenance
                + ':'
                + str(event.get('producer_id') or file_id)
                + ':'
                + str(event.get('session_id'))
            )
            self.connection.execute(
                'INSERT OR IGNORE INTO capture_streams VALUES(?,?,?)',
                (stream_id, source_id, str(event.get('session_id', ''))),
            )
            result = event.get('result', 'unknown')
            accepted = result in ('sent', 'validated')
            acceptance = (
                'accepted' if accepted else result if result in ('failed', 'logged') else 'unknown'
            )
            when = event.get('captured_at') or event.get('source_time')
            basis = 'utc_receipt' if event.get('captured_at') else 'local_timezone_unknown'
            self.connection.execute(
                'INSERT INTO ingest_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                (
                    event_id,
                    stream_id,
                    legacy_key,
                    event.get('source_time') or event.get('time'),
                    event.get('captured_at'),
                    basis,
                    acceptance,
                    encoded(event),
                    file_id,
                    row,
                ),
            )
            return self._observation(event_id, event, accepted, when, basis, provenance), True

    def _observation(self, event_id, event, accepted, when, basis, provenance):
        shot_id = identity('shot:' + event_id) if accepted else None
        if accepted:
            self.connection.execute(
                'INSERT INTO shots VALUES(?,?,?,?,?)',
                (shot_id, event_id, when, basis, event.get('club')),
            )
            owner = event.get('user_id')
            sid = event.get('practice_session_id')
            session_owner = self.session_owner(sid) if sid else None
            if owner and session_owner and owner != session_owner:
                raise ValueError('Shot golfer conflicts with its frozen session.')
            owner = session_owner or owner
            if owner:
                self.connection.execute(
                    'INSERT INTO shot_owners VALUES(?,?,?)',
                    (shot_id, owner, 'accepted_input_context'),
                )
        observation_id = identity('observation:' + event_id)
        profile = (
            self.generic_profile
            if event.get('mapping_id') in ('traceloft.normalized.v1', 'traceloft.normalized.v2')
            or {'club_speed', 'smash_factor', 'attack_angle', 'club_path'}.intersection(
                event.get('vals', {})
            )
            else self.extended_profile
            if EXTENDED_FIELDS.intersection(event.get('vals', {}))
            else self.profile
        )
        mapping_id = profile['id']
        self.connection.execute(
            'INSERT INTO observations VALUES(?,?,?,?,?)',
            (observation_id, event_id, shot_id, mapping_id, provenance),
        )
        for mapping in profile['fields']:
            field, metric, unit = mapping['source_field'], mapping['metric'], mapping['source_unit']
            operation = mapping['transform']['operation']
            if operation not in ('identity', 'scale'):
                raise ValueError('Unsupported archived metric transform.')
            factor = mapping['transform'].get('factor', 1)
            value = event.get('vals', {}).get(field)
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            )
            availability = 'available' if valid else 'unavailable' if value is None else 'invalid'
            self.connection.execute(
                'INSERT INTO metric_values VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (
                    observation_id,
                    metric,
                    1,
                    float(value) * factor if valid else None,
                    None,
                    None,
                    None,
                    field,
                    unit,
                    encoded(value),
                    availability,
                    'synthetic_demo'
                    if event.get('simulated')
                    else mapping.get('method', 'provider_unknown'),
                    mapping['semantic_variant'],
                ),
            )
        self.connection.execute(
            'INSERT INTO delivery_events VALUES(?,?,?,?)',
            (
                identity('delivery:' + event_id),
                event_id,
                'socket_write_reported_unacknowledged'
                if event.get('result') == 'sent'
                else 'not_established',
                encoded(
                    {
                        'result': event.get('result'),
                        'note': event.get('note'),
                        'sent_fields': event.get('sent_fields'),
                    }
                ),
            ),
        )
        from shot_schema import write_source, source_features

        write_source(self.connection, observation_id)
        if shot_id:
            source_features(self.connection, shot_id)
        return event_id

    def load_session(self, session_id, deleted=False):
        if not re.fullmatch('[0-9a-f]{32}', session_id):
            raise ValueError('Invalid session identifier.')
        with self.lock:
            row = self.connection.execute(
                'SELECT payload_json FROM sessions WHERE id=? AND (deleted_at IS NOT NULL)=?',
                (session_id, int(deleted)),
            ).fetchone()
            if not row:
                raise FileNotFoundError('Session not found.')
            from domain_schema import read_session

            return read_session(self.connection, session_id)

    def list_sessions(self, deleted=False):
        with self.lock:
            from domain_schema import read_session

            return [
                read_session(self.connection, r[0])
                for r in self.connection.execute(
                    'SELECT id FROM sessions WHERE (deleted_at IS NOT NULL)=? ORDER BY started DESC',
                    (int(deleted),),
                ).fetchall()
            ]

    def append_attempt(self, data):
        """Commit one new attempt and its resulting session state atomically.

        Scorers own the append-only historical prefix. Corrections use save_session.
        """
        return self.save_session(data, append=True)

    def save_session(self, data, imported=False, deleted=False, append=False):
        with self.transaction():
            sid = data['id']
            old = self.connection.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
            if old and old['deleted_at'] and not imported:
                raise ValueError('This session has been deleted; restore it before editing.')
            if old and imported:
                if old['payload_json'] != encoded(data) or bool(old['deleted_at']) != deleted:
                    raise ValueError(f'Conflicting legacy copies of session {sid}.')
                return
            links = self.connection.execute(
                'SELECT ordinal,legacy_key FROM session_attempts WHERE session_id=? ORDER BY ordinal',
                (sid,),
            ).fetchall()
            if len(data['shots']) < len(links) or any(
                data['shots'][row['ordinal'] - 1]['key'] != row['legacy_key'] for row in links
            ):
                raise ValueError(
                    'Recorded attempts cannot be removed or reordered; use audited cleanup.'
                )
            cache = self._attempt_updates.get(sid, self._attempt_cache.get(sid))
            revision = old['revision'] if old else 0
            if not cache or cache[0] != revision:
                cache = (revision, None)
            if append:
                if not old or len(data['shots']) != len(links) + 1:
                    raise ValueError(
                        'Append requires exactly one new attempt on an existing session.'
                    )
                ordinal = len(data['shots'])
                changed = {ordinal}
                fingerprints = dict(cache[1] or {})
                fingerprints[ordinal] = digest(encoded(data['shots'][-1]).encode())
            else:
                from domain_schema import read_session

                previous = cache[1]
                if old and (previous is None or len(previous) != len(links)):
                    previous = {
                        i: digest(encoded(shot).encode())
                        for i, shot in enumerate(read_session(self.connection, sid)['shots'], 1)
                    }
                previous = previous or {}
                fingerprints = {
                    i: digest(encoded(shot).encode()) for i, shot in enumerate(data['shots'], 1)
                }
                changed = {i for i, value in fingerprints.items() if previous.get(i) != value}
            self.connection.execute(
                'INSERT INTO sessions VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                'started=excluded.started, ended=excluded.ended, drill=excluded.drill, revision=sessions.revision+1',
                (
                    sid,
                    data['started'],
                    data.get('ended'),
                    data['drill'],
                    now() if deleted else None,
                    1,
                    old['payload_json'] if old else encoded(data),
                ),
            )
            for ordinal, shot in enumerate(data['shots'], 1):
                if ordinal not in changed:
                    continue
                previous = self.connection.execute(
                    'SELECT * FROM session_attempts WHERE session_id=? AND legacy_key=?',
                    (sid, shot['key']),
                ).fetchone()
                if previous:
                    shot_id, obs_id = previous['shot_id'], previous['observation_id']
                    if previous['excluded'] != int(shot['excluded']):
                        correction = shot.get('game_correction')
                        new_misread = (
                            correction
                            and correction['kind'] == 'misread'
                            and not self.connection.execute(
                                "SELECT 1 FROM attempt_fields WHERE session_id=? AND ordinal=? AND path='/game_correction/kind'",
                                (sid, ordinal),
                            ).fetchone()
                        )
                        self.connection.execute(
                            'INSERT INTO inclusion_decisions VALUES(?,?,?,?,?,?)',
                            (
                                uuid.uuid4().hex,
                                sid,
                                shot['key'],
                                int(shot['excluded']),
                                'game_misread' if new_misread else 'manual_session_only',
                                now(),
                            ),
                        )
                else:
                    receipt_id = shot.get('receipt_id')
                    candidates = (
                        self.connection.execute(
                            'SELECT id FROM ingest_events WHERE legacy_key=? AND import_file_id IS NOT NULL',
                            (shot['key'],),
                        ).fetchall()
                        if imported
                        else []
                    )
                    linked = receipt_id or (candidates[0]['id'] if len(candidates) == 1 else None)
                    shared = (
                        self.connection.execute(
                            'SELECT o.shot_id FROM observations o WHERE event_id=?', (linked,)
                        ).fetchone()
                        if linked
                        else None
                    )
                    if shared and not shared['shot_id']:
                        linked_shot = identity('shot:' + linked)
                        self.connection.execute(
                            'INSERT INTO shots VALUES(?,?,?,?,?)',
                            (
                                linked_shot,
                                linked,
                                shot.get('captured'),
                                'utc_practice_receipt',
                                None,
                            ),
                        )
                        self.connection.execute(
                            "UPDATE ingest_events SET acceptance='accepted' WHERE id=?", (linked,)
                        )
                        self.connection.execute(
                            'UPDATE observations SET shot_id=? WHERE event_id=?',
                            (linked_shot, linked),
                        )
                    else:
                        linked_shot = shared['shot_id'] if shared else None
                    event_id = identity('practice:' + sid + ':' + shot['key'])
                    event = dict(
                        session_id=shot['key'].rsplit(':', 1)[0],
                        seq=shot['key'].rsplit(':', 1)[-1],
                        captured_at=shot.get('captured'),
                        result='validated',
                        vals=shot['vals'],
                        practice_session_id=sid,
                        linking='unique_legacy_key'
                        if linked_shot
                        else 'unresolved_or_practice_only',
                    )
                    if shot.get('simulated'):
                        event.update(
                            simulated=True,
                            source_configuration={
                                'acquisition': 'synthetic_demo',
                                'generator': 'golfdata-demo-v1',
                            },
                        )
                    self.ingest(
                        event, event_id, 'legacy_practice' if imported else 'practice_measurements'
                    )
                    obs_id = identity('observation:' + event_id)
                    own_shot = identity('shot:' + event_id)
                    shot_id = linked_shot or own_shot
                    if linked_shot:
                        self.connection.execute(
                            'UPDATE observations SET shot_id=? WHERE id=?', (linked_shot, obs_id)
                        )
                        from shot_schema import write_source, source_features

                        # Transfer the practice report before deleting its temporary shot identity.
                        self.connection.execute(
                            'DELETE FROM derived_metric_selection WHERE shot_id=?', (own_shot,)
                        )
                        self.connection.execute(
                            'DELETE FROM calculation_inputs WHERE result_id IN (SELECT result_id FROM shot_derived_metrics WHERE shot_id=?)',
                            (own_shot,),
                        )
                        self.connection.execute(
                            'DELETE FROM shot_derived_metrics WHERE shot_id=?', (own_shot,)
                        )
                        write_source(self.connection, obs_id)
                        source_features(self.connection, linked_shot)
                        self.connection.execute(
                            'DELETE FROM shot_owners WHERE shot_id=?', (own_shot,)
                        )
                        self.connection.execute('DELETE FROM shots WHERE id=?', (own_shot,))
                self.connection.execute(
                    'INSERT INTO session_attempts VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(session_id,ordinal) DO UPDATE SET '
                    'excluded=excluded.excluded',
                    (
                        sid,
                        ordinal,
                        shot['key'],
                        shot_id,
                        obs_id,
                        shot.get('captured'),
                        shot.get('target', data['target']),
                        int(shot['success']),
                        int(shot['excluded']),
                        encoded(shot),
                    ),
                )
                from shot_schema import write_source, save_attempt_results, source_features

                write_source(self.connection, obs_id)
                source_features(self.connection, shot_id)
                save_attempt_results(self.connection, data, shot, ordinal, legacy=imported)
            from domain_schema import write_session

            write_session(self.connection, data, backfill=imported, changed_attempts=changed)
            from analysis_schema import save_collection

            save_collection(self.connection, data)
            self.audit(
                sid,
                'import_session' if imported else 'save_session',
                {'shots': len(data['shots']), 'changed_attempts': sorted(changed)},
            )
            self._attempt_updates[sid] = (revision + 1, fingerprints)

    def set_deleted(self, session_id, deleted):
        with self.transaction():
            self.load_session(session_id, deleted=not deleted)
            self.connection.execute(
                'UPDATE sessions SET deleted_at=?, revision=revision+1 WHERE id=?',
                (now() if deleted else None, session_id),
            )
            self.audit(session_id, 'delete' if deleted else 'restore', {})

    def backup(self, directory=None):
        directory = Path(directory or self.path.parent / 'backups')
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / (
            'golfdata-'
            + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            + '-'
            + uuid.uuid4().hex[:8]
            + '.sqlite3'
        )
        # A separate read connection copies one committed snapshot in a single backup step,
        # so the writer lock (and with it shot intake) is never held for the copy/verification.
        with contextlib.closing(self._read_connection()) as source:
            with contextlib.closing(sqlite3.connect(target)) as destination:
                source.backup(destination)
                destination.execute('PRAGMA journal_mode=DELETE')
                if (
                    destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok'
                    or destination.execute('PRAGMA foreign_key_check').fetchall()
                ):
                    raise OSError('Backup integrity verification failed.')
                counts = {
                    t: destination.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
                    for t in ('shots', 'ingest_events', 'sessions', 'session_attempts')
                }
                schema = destination.execute('PRAGMA user_version').fetchone()[0]
        atomic_json(
            target.with_suffix('.manifest.json'),
            dict(
                schema=schema,
                created=now(),
                sha256=digest(target.read_bytes()),
                counts=counts,
                protection='local_only',
                includes='database and embedded imported evidence; crop/training archives remain separate',
            ),
        )
        return target

    def export(self):
        """One committed snapshot, separate observation rows, blank unavailable cells."""
        from storage_export import export_archive

        return export_archive(self)
