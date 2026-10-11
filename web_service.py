"""SQLite and practice authority; external launch monitors connect through Open Connect."""

import asyncio
import copy
import json
import os
import contextlib
import sqlite3
import uuid
from collections import deque
from pathlib import Path

from shot_input import ShotInput
from putting import PuttingSession
from distance_ladder import DistanceLadderSession, RANGE_FIELDS, restore_model
from storage import Store, database_path, import_legacy
from database_tools import ServiceLease, preserve_legacy
from equipment import edit_catalog, selection
from driving_range import DrivingRangeSession, DRIVING_FIELDS, demo_event

from collection import CollectionSession, COLLECTION_FIELDS
from golf_sim import GolfSimSession, GAME_FIELDS, simulated_event

ROOT = Path(__file__).resolve().parent
DRILLS = [
    dict(
        id='golf-sim',
        title='Meadow One · 2D golf',
        description='Play an original par four with estimated lies and putting.',
        drill='2D golf',
        category='PLAY',
        random_pace=False,
    ),
    dict(
        id='wedge-matrix',
        title='Wedge matrix',
        description='Map each wedge at your own swing lengths and find a shot for every yardage.',
        drill='Wedge matrix',
        category='WEDGES',
        random_pace=False,
    ),
    dict(
        id='bag-mapping',
        title='Bag mapping / gapping',
        description='Collect per-club samples and discover distance gaps and overlaps.',
        drill='Bag mapping',
        category='FULL SWING',
        random_pace=False,
    ),
    dict(
        id='driving-range',
        title='Driving range',
        description='Free practice, shot dispersion, flight estimates and a workspace to review your shots.',
        drill='Driving range',
        category='FULL SWING',
        random_pace=False,
    ),
    dict(
        id='distance-ladder',
        title='Distance ladder',
        description='Build carry or total-distance control with wedges, irons and custom yardages.',
        drill='Distance ladder',
        category='FULL SWING',
        random_pace=False,
    ),
    dict(
        id="pace",
        title="Pace consistency",
        description="Repeat a speed target and build a consistent stroke.",
        drill="Pace consistency",
        random_pace=False,
    ),
    dict(
        id="line",
        title="Start line",
        description="Train your launch direction inside a chosen window.",
        drill="Start line",
        random_pace=False,
    ),
    dict(
        id="combined",
        title="Pace + start line",
        description="Combine pace and direction in one scored session.",
        drill="Pace + start line",
        random_pace=False,
    ),
    dict(
        id="random",
        title="Random pace",
        description="A fresh target after every putt. Stay adaptable.",
        drill="Pace + start line",
        random_pace=True,
    ),
    dict(
        id="ladder",
        title="Putting ladder",
        description="Climb distance targets on a flat virtual green. Train estimated short/long control.",
        drill="Putting ladder",
        random_pace=False,
    ),
]


class GolfService:
    def __init__(self, root=ROOT, database=None):
        self.root = Path(root)
        db_path = database or (
            database_path() if self.root == ROOT else self.root / 'data/golfdata.sqlite3'
        )
        self.lease = ServiceLease(db_path)
        self.store = None
        try:
            self.store = Store(db_path, migration_lease_held=True)
            if not self.store.migrated():
                preserve_legacy(self.root, self.store.path.parent / 'backups')
                import_legacy(self.store, self.root)
                self.store.backup()
        except BaseException:
            if self.store:
                self.store.close()
            self.lease.close()
            raise
        self.receipt_dir = self.store.path.parent / 'receipts'
        self.practice = None
        # Legacy capture fields (fps/drops/image) remain in the DTO for older browser builds.
        self.capture = dict(
            running=False,
            stopping=False,
            mode=None,
            status="Waiting for shot source",
            connected=False,
            fps=0,
            drops=0,
            image=None,
            error="",
        )
        self.settings = dict(host='127.0.0.1', port=921, enabled=False)
        self.input_context = {}
        self.input = ShotInput(
            self,
            port=int(os.environ.get('TRACELOFT_INPUT_PORT', '900')) if self.root == ROOT else 0,
        )
        self.history, self.logs = deque(maxlen=50), deque(maxlen=100)
        self.latest_read = None
        self._records = 0
        self.pending = deque()
        self.save_error = ""
        self.last_retry = 0
        self.access = dict(lan=False, addresses=[], port=8765)
        self.sessions_revision = 0
        self._live_epoch = uuid.uuid4().hex
        self._live_revision = 0
        self._live_fingerprint = None
        self.equipment = self.store.equipment_catalog()
        self.publish_context()

    def publish_context(self):
        active = (
            self.practice and not self.practice.data['ended'] and not self.practice.data.get('demo')
        )
        self.input_context = dict(
            practice_session_id=self.practice.data['id'] if active else None,
            user_id=self.store.session_owner(self.practice.data['id']) if active else None,
            required_distance=self.practice.data.get('range_metric') if active else None,
            equipment_selection=copy.deepcopy(self.practice.data.get('equipment_selection'))
            if active
            else None,
            collection_context={'swing_label': self.practice.data.get('swing_label')}
            if active
            else None,
            game_context=self.practice.context()
            if active and isinstance(self.practice, GolfSimSession)
            else None,
            range_context={
                k: self.practice.data[k] for k in ('range_target', 'range_width', 'range_depth')
            }
            if active and self.practice.data.get('session_kind') == 'driving_range'
            else None,
        )
        return True

    def load_session(self, session_id, deleted=False):
        if self.store.session_owner(session_id) not in (None, self.store.active_user()):
            raise FileNotFoundError('Switch golfer to open this session.')
        return restore_model(PuttingSession.from_store(self.store, session_id, deleted))

    def _session(self, session_id):
        """The active session object when it matches, otherwise the saved copy."""
        if self.practice and self.practice.data['id'] == session_id:
            return self.practice
        return self.load_session(session_id)

    def _require_saved(self, message):
        """Retry queued saves; refuse a state change while any shot remains unsaved."""
        self.flush_practice()
        if self.pending:
            raise ValueError(message)

    @contextlib.contextmanager
    def _changing(self, session):
        """Mutate a session inside one transaction; any failure restores its prior state.

        Without this, an exception after an in-memory change would leave the live
        session disagreeing with SQLite (for example, shown as ended but saved as active).
        """
        previous = copy.deepcopy(session.data) if session else None
        try:
            with self.store.transaction():
                yield session
        except BaseException:
            if session:
                session.data = previous
            raise

    def remember_record(self, event, read=False):
        """Show a received record in live history; the counter makes the change detectable."""
        self.history.appendleft(event)
        if read:
            self.latest_read = event
        self._records += 1

    def live_revision(self):
        """Cheap change detection: never walk session attempts or trajectories.

        Never takes the writer lock: a background export, backup or calculation must not
        stall the event loop. Database changes (including background publication) are
        detected through committed_version(), which ignores uncommitted work in progress.
        """
        data = self.practice.data if self.practice else None
        fingerprint = json.dumps(
            dict(
                database=self.store.committed_version(),
                sessions=self.sessions_revision,
                practice=(data['id'], data.get('ended'), len(data['shots'])) if data else None,
                equipment=self.equipment.get('revision'),
                capture=self.capture,
                settings=self.settings,
                access=self.access,
                input_port=self.input.port,
                input=self.input.state,
                relay=self.input.relay.state,
                error=self.save_error,
                records=self._records,
                logs=(len(self.logs), tuple(self.logs)),
            ),
            sort_keys=True,
        )
        if fingerprint != self._live_fingerprint:
            self._live_fingerprint = fingerprint
            self._live_revision += 1
        return dict(epoch=self._live_epoch, revision=self._live_revision)

    def snapshot(self):
        # In-memory state belongs to the event loop; golfer rows come from a committed read,
        # so a long background transaction cannot block a state request.
        golfers, golfer_id = self.store.golfers()
        return copy.deepcopy(
            dict(
                live=self.live_revision(),
                capture=self.capture,
                settings=self.settings,
                input_port=self.input.port,
                relay=self.input.relay.state,
                input=self.input.state,
                practice=self.practice.data if self.practice else None,
                summary=self.practice.summary() if self.practice else None,
                practice_error=self.save_error,
                history=list(self.history),
                logs=list(self.logs),
                read=self.latest_read,
                access=self.access,
                sessions_revision=self.sessions_revision,
                equipment=self.equipment,
                golfers=golfers,
                golfer_id=golfer_id,
                storage=dict(engine='sqlite', path=str(self.store.path), backup='local_only'),
            )
        )

    def ingest(self, event):
        """Queue a recovered/in-process record event; Open Connect input uses ShotInput."""
        kind = event.get("kind")
        if kind == "record":
            if (
                'equipment_selection' not in event
                and self.practice
                and self.practice.data.get('practice_type') == 'full_swing'
                and event.get('practice_session_id', self.practice.data['id'])
                == self.practice.data['id']
            ):
                event = dict(
                    event,
                    equipment_selection=copy.deepcopy(
                        self.practice.data.get('equipment_selection')
                    ),
                )
            self.remember_record(event)
            self.pending.append(event)
            self.flush_practice()
        elif kind in ("error", "log"):
            self.logs.append(event.get("message", ""))
            if kind == "error":
                self.capture["error"] = event.get("message", "")

    def flush_practice(self):
        while self.pending:
            event = self.pending[0]
            target = self.practice
            if 'practice_session_id' in event:
                sid = event['practice_session_id']
                target = (
                    self.practice if self.practice and self.practice.data['id'] == sid else None
                )
                if sid and not target:
                    try:
                        target = self.load_session(sid)
                    except FileNotFoundError:
                        target = None
            try:
                with self._changing(target):
                    receipt_id, fresh = self.store.ingest(event)
                    practice_event = dict(event, receipt_id=receipt_id)
                    added = target.add(practice_event) if fresh and target else False
            except (OSError, ValueError) as exc:
                self.save_error = f"Practice save failed; waiting to retry: {exc}"
                return
            self.pending.popleft()
            if event.get('receipt_id'):
                # Receipt removal is an acknowledgment only; a leftover file is safe to replay into SQLite.
                try:
                    (self.receipt_dir / (event['receipt_id'] + '.json')).unlink(missing_ok=True)
                except OSError:
                    pass
            if added:
                self.sessions_revision += 1
                self.publish_context()
                if target.data['ended']:
                    self.backup_after_session()
        self.save_error = ""

    def recover_receipts(self):
        if self.pending:
            return
        try:
            events = [json.loads(p.read_text('utf-8')) for p in self.receipt_dir.glob('*.json')]
            events.sort(key=lambda event: event.get('captured_at', ''))
            self.pending.extend(events)
            self.flush_practice()
        except (OSError, ValueError) as exc:
            self.save_error = f'Receipt recovery failed: {exc}'

    def backup_after_session(self):
        """Copy and verify the database without stalling shot intake.

        Inside the running service the copy runs on a worker thread; it reads its own
        snapshot connection, so it needs no shared state. Without a loop (scripts/tests)
        it runs inline. Store.close() waits for outstanding copies.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                self.store.backup()
            except (OSError, sqlite3.Error) as exc:
                self._backup_failed(exc)
            return
        self.store.backup_in_background(self._backup_failed)

    def _backup_failed(self, exc):
        self.capture['error'] = f'Session saved; local backup failed: {exc}'

    async def run(self):
        self.publish_context()
        while True:
            self.input.tick()
            now = asyncio.get_running_loop().time()
            if self.pending and now - self.last_retry > 5:
                self.flush_practice()
                self.last_retry = now
            if not self.pending:
                self.recover_receipts()
            await asyncio.sleep(0.05)

    async def shutdown(self):
        await self.input.close()
        self.flush_practice()
        await asyncio.to_thread(self.store.wait_for_background)
        try:
            self.publish_context()
            with self.store.transaction():
                self.store.connection.execute(
                    "INSERT OR REPLACE INTO metadata VALUES('active_session.v1',?)",
                    (
                        json.dumps(
                            self.practice.data['id']
                            if self.practice and not self.practice.data['ended']
                            else None
                        ),
                    ),
                )
            self.store.backup()
        finally:
            self.store.close()
            self.lease.close()

    def create_practice(self, params):
        if self.practice and not self.practice.data["ended"]:
            raise ValueError("Finish or abandon the active session before launching another drill.")
        if params['drill'] == '2D golf':
            from course_import import load

            selected = selection(
                self.equipment, params.get('range_bag_id', ''), params.get('range_club_id', '')
            )
            self.practice = GolfSimSession(
                self.root / 'practice_sessions',
                store=self.store,
                equipment_selection=selected,
                course=load(self.store, params.get('game_course_id', 'pebble-boulder-blue-v3')),
                **{k: v for k, v in params.items() if k in GAME_FIELDS or k in ('demo', 'stimp')},
            )
        elif params['drill'] in ('Bag mapping', 'Wedge matrix'):
            self.practice = CollectionSession(
                self.root / 'practice_sessions',
                self.equipment,
                params.get('range_bag_id', ''),
                params.get('collection_clubs', []),
                samples=params.get('collection_samples', 5),
                metric=params.get('range_metric', 'carry'),
                demo=params.get('demo', False),
                handedness=params.get('handedness', 'right_handed'),
                store=self.store,
                swing_labels=params.get('swing_labels')
                if params['drill'] == 'Wedge matrix'
                else None,
            )
        elif params['drill'] == 'Driving range':
            selected = selection(
                self.equipment, params.get('range_bag_id', ''), params.get('range_club_id', '')
            )
            self.practice = DrivingRangeSession(
                self.root / 'practice_sessions',
                store=self.store,
                equipment_selection=selected,
                **{k: v for k, v in params.items() if k in DRIVING_FIELDS},
            )
        elif params['drill'] == 'Distance ladder':
            selected = selection(
                self.equipment, params.get('range_bag_id', ''), params.get('range_club_id', '')
            )
            self.practice = DistanceLadderSession(
                self.root / 'practice_sessions',
                store=self.store,
                equipment_selection=selected,
                **{
                    k: v
                    for k, v in params.items()
                    if k in RANGE_FIELDS and k not in ('range_bag_id', 'range_club_id')
                },
            )
        else:
            self.practice = PuttingSession(
                self.root / 'practice_sessions',
                store=self.store,
                **{
                    k: v
                    for k, v in params.items()
                    if k not in RANGE_FIELDS
                    and k not in DRIVING_FIELDS
                    and k not in COLLECTION_FIELDS
                    and k not in GAME_FIELDS
                },
            )
        self.publish_context()
        self.sessions_revision += 1
        return self.practice.data

    def change_golfer(self, user_id=None, name=None, handedness='right_handed'):
        if self.practice and not self.practice.data['ended']:
            raise ValueError('Finish or abandon the active session before changing golfer.')
        self._require_saved('Resolve pending saves before changing golfer.')
        with self.store.transaction():
            if name is not None:
                user_id = self.store.create_user(name, handedness)
            self.store.select_user(user_id)
        self.practice = None
        self.equipment = self.store.equipment_catalog()
        self.publish_context()
        self.sessions_revision += 1

    def edit_bag(self, revision, name, bag_id=None, clubs=None):
        updated, edited_id = edit_catalog(self.equipment, revision, name, bag_id, clubs)
        self._require_saved(
            'Results are waiting to save. Resolve the save error before editing bags.'
        )
        with self._changing(self.practice):
            self.store.save_equipment_catalog(updated)
            current = (
                self.practice.data.get('equipment_selection')
                if self.practice and not self.practice.data['ended']
                else None
            )
            if current and current['bag_id'] == edited_id:
                bag = next(b for b in updated['bags'] if b['id'] == edited_id)
                club_id = (
                    current['club_id']
                    if any(c['id'] == current['club_id'] for c in bag['clubs'])
                    else ''
                )
                self.practice.data['equipment_selection'] = selection(updated, edited_id, club_id)
                self.practice.save()
        self.equipment = updated
        self.publish_context()
        self.sessions_revision += 1
        return edited_id

    def select_equipment(self, session_id, bag_id, club_id):
        if (
            not self.practice
            or self.practice.data['id'] != session_id
            or self.practice.data['ended']
            or self.practice.data.get('practice_type') != 'full_swing'
        ):
            raise ValueError(
                'Only the active full-swing ladder can change its next-shot equipment.'
            )
        selected = selection(self.equipment, bag_id, club_id)
        self._require_saved(
            'Results are waiting to save. Resolve the save error before changing clubs.'
        )
        if self.practice.data['ended']:
            raise ValueError('This ladder has completed; new club selection was not applied.')
        with self._changing(self.practice):
            self.practice.data['equipment_selection'] = selected
            self.practice.save()
        self.publish_context()
        self.sessions_revision += 1

    def select_collection_cell(self, session_id, club_id, swing_label):
        saved = self.range_session(session_id)
        if (
            saved is not self.practice
            or saved.data['ended']
            or saved.data.get('collection_kind') != 'wedge'
        ):
            raise ValueError('Only an active wedge matrix can select a cell.')
        if swing_label not in saved.data['swing_labels']:
            raise ValueError('Choose a planned swing label.')
        planned = next((p for p in saved.data['collection_plan'] if p['club_id'] == club_id), None)
        if not planned:
            raise ValueError('Choose a planned wedge.')
        selected = selection(self.equipment, planned['bag_id'], club_id)
        self._require_saved('Resolve pending saves before changing your swing label.')
        with self._changing(saved):
            saved.data.update(equipment_selection=selected, swing_label=swing_label)
            saved.save()
        self.publish_context()
        self.sessions_revision += 1

    def resume_practice(self, session_id):
        """Maintenance handoff: restore an unchanged active drill after a service reload."""
        if self.practice:
            raise ValueError("Only an idle service can accept a session handoff.")
        saved = self.load_session(session_id)
        if saved.data["ended"] or saved.data.get("abandoned"):
            raise ValueError("Only an unfinished session can be handed over.")
        self.practice = saved
        self.publish_context()
        self.sessions_revision += 1

    def range_session(self, session_id):
        saved = self._session(session_id)
        if saved.data.get('session_kind') != 'driving_range':
            raise ValueError('This action requires a driving range session.')
        return saved

    def game_action(self, session_id, action, params):
        self._require_saved('Resolve pending saves before changing the round.')
        saved = self.practice
        if (
            not isinstance(saved, GolfSimSession)
            or saved.data['id'] != session_id
            or saved.data['ended']
        ):
            raise ValueError('This action requires the active round.')
        if params['turn'] != saved.data['game']['turn']:
            raise ValueError(
                'The round advanced. Wait for the updated position before hitting again.'
            )
        with self._changing(saved):
            if action == 'aim':
                saved.set_aim(params['x'], params['y'], params['turn'])
            elif action == 'next':
                saved.next_hole(params['turn'])
            elif action == 'simulate':
                event = simulated_event(
                    saved, params['distance_yd'], params['offline_yd'], params.get('carry_yd')
                )
                self.store.ingest(event, provenance='synthetic_demo')
                saved.add(event)
            else:
                raise ValueError('Unknown game action.')
        self.publish_context()
        self.sessions_revision += 1
        if saved.data['ended']:
            self.backup_after_session()

    def correct_game(self, session_id, params):
        self._require_saved('Resolve pending saves before correcting the round.')
        if (
            self.practice
            and self.practice.data['id'] != session_id
            and not self.practice.data['ended']
        ):
            raise ValueError('Finish or abandon the active session before reopening this round.')
        saved = self._session(session_id)
        if not isinstance(saved, GolfSimSession):
            raise ValueError('Choose a golf round.')
        with self._changing(saved):
            audit = saved.correct_shot(params['kind'], params['key'], params['turn'])
            self.store.audit(session_id, 'game_correction', audit)
        self.practice = saved
        self.publish_context()
        self.sessions_revision += 1

    def _round(self, session_id):
        saved = self._session(session_id)
        if not isinstance(saved, GolfSimSession):
            raise ValueError('Choose a golf round.')
        return saved

    def game_preview(self, session_id):
        return self.preview_round(self.preview_inputs(session_id))

    def preview_inputs(self, session_id):
        """Copy the round on the event loop so preview_round() can run on a worker thread."""
        return copy.deepcopy(self._round(session_id).data)

    def preview_round(self, data):
        """Historical dispersion for a copied round, read from a committed snapshot."""
        from club_preview import build_preview
        from analysis_schema import preview_sessions

        with self.store.reading() as connection:
            sessions, warnings = preview_sessions(connection, data)
        result = build_preview(sessions, data)
        result['warnings'] = warnings
        return result

    def game_recommendations(self, session_id):
        inputs = self.recommendation_inputs(session_id)
        return self.recommend_clubs(*inputs) if inputs else []

    def recommendation_inputs(self, session_id):
        """Copies for recommend_clubs(), or None when no full-swing suggestion applies."""
        saved = self._round(session_id)
        bag = (saved.data.get('equipment_selection') or {}).get('bag_id')
        if not bag or saved.data['game']['lie'] == 'green':
            return None
        factor = (
            1 - saved.data['game_settings'].get(saved.data['game']['lie'] + '_percent', 0) / 100
        )
        if factor <= 0:
            return None
        return (
            copy.deepcopy(saved.data),
            saved.summary()['remaining_yd'],
            copy.deepcopy(self.equipment),
        )

    def recommend_clubs(self, data, remaining_yd, equipment):
        """Closest clubs by historical median total; safe on a worker thread."""
        from analysis import build_report
        from analysis_schema import preview_sessions

        bag = data['equipment_selection']['bag_id']
        collections = []
        with self.store.reading() as connection:
            current = next((b for b in equipment['bags'] if b['id'] == bag), None)
            for club in (current or {}).get('clubs', []):
                game = {**data, 'equipment_selection': dict(bag_id=bag, club_id=club['id'])}
                collections.extend(preview_sessions(connection, game)[0])
        report = build_report(
            collections,
            dict(mode='demo' if data['demo'] else 'real', bag=bag, metric='total'),
        )
        factor = 1 - data['game_settings'].get(data['game']['lie'] + '_percent', 0) / 100
        needed = remaining_yd / factor
        available = [g for g in report['groups'] if g['metrics']['total']['count'] >= 5]
        available.sort(key=lambda g: abs(g['metrics']['total']['median'] - needed))
        return [
            dict(
                club_id=g['club_id'],
                club_label=g['club_label'],
                swing_label=g['swing_label'],
                median_yd=g['metrics']['total']['median'],
                iqr_yd=g['metrics']['total']['iqr'],
                adjusted_yd=g['metrics']['total']['median'] * factor,
                count=g['metrics']['total']['count'],
            )
            for g in available[:3]
        ]

    def cleanup_range(self, session_id, params):
        self._require_saved('Resolve the pending shot save before cleanup.')
        saved = self.range_session(session_id)
        equipment = (
            selection(self.equipment, params.get('bag_id', ''), params.get('club_id', ''))
            if params['action'] == 'retag'
            else None
        )
        with self._changing(saved):
            batch = saved.cleanup(
                params['action'],
                params['keys'],
                params['revision'],
                params['reason'],
                equipment,
                params.get('batch_id'),
            )
            self.store.audit(session_id, 'range_cleanup', saved.data['cleanup_history'][-1])
        self.sessions_revision += 1
        return dict(practice=saved.data, summary=saved.summary(), batch_id=batch)

    def target_range(self, session_id, target, width, depth):
        self._require_saved('Resolve the pending shot save before changing the target.')
        saved = self.range_session(session_id)
        if saved is not self.practice or saved.data['ended']:
            raise ValueError('Only the active range can change its next-shot target.')
        with self._changing(saved):
            saved.data.update(
                range_target=target, target=target, range_width=width, range_depth=depth
            )
            saved.save()
        self.publish_context()
        self.sessions_revision += 1

    def simulate_range(self, session_id, count):
        saved = self.range_session(session_id)
        if saved is not self.practice or saved.data['ended'] or not saved.data.get('demo'):
            raise ValueError('Simulated shots are only available in an active Demo range.')
        if count not in (1, 10):
            raise ValueError('Generate one shot or a set of ten.')
        with self._changing(saved):
            for _ in range(count):
                event = demo_event(saved, len(saved.data['shots']) + 1)
                self.store.ingest(event, provenance='synthetic_demo')
                saved.add(event)
        self.sessions_revision += 1

    def change_practice(self, session_id, action, key=None):
        if not self.practice or self.practice.data["id"] != session_id:
            raise ValueError("This session is no longer active. Refresh before changing it.")
        if action == 'exclude' and self.practice.data.get('session_kind') == 'driving_range':
            return self.exclude_saved(session_id, key)
        self._require_saved(
            "Results are waiting to save. Resolve the save error before changing the session."
        )
        with self._changing(self.practice):
            if action == "finish":
                self.practice.finish()
            elif action == "abandon":
                self.practice.abandon()
            elif action == "exclude":
                if not any(s["key"] == key for s in self.practice.data["shots"]):
                    raise ValueError("Choose a shot from this session.")
                self.practice.toggle_excluded(key)
        if action == "abandon":
            self.practice = None
        self.publish_context()
        self.sessions_revision += 1
        if action in ('finish', 'abandon'):
            self.backup_after_session()

    def exclude_saved(self, session_id, key):
        saved = self._session(session_id)
        if saved.data.get('session_kind') == 'driving_range':
            shot = next((s for s in saved.data['shots'] if s['key'] == key), None)
            if not shot:
                raise ValueError('Choose a shot from this session.')
            return self.cleanup_range(
                session_id,
                dict(
                    action='include' if shot['excluded'] else 'exclude',
                    keys=[key],
                    revision=saved.data['cleanup_revision'],
                    reason='Single-shot inclusion change',
                ),
            )
        if self.practice and self.practice.data["id"] == session_id:
            self.change_practice(session_id, "exclude", key)
            saved = self.practice
        else:
            saved = self.load_session(session_id)
            if not any(s["key"] == key for s in saved.data["shots"]):
                raise ValueError("Choose a shot from this session.")
            saved.toggle_excluded(key)
            self.sessions_revision += 1
        return dict(practice=saved.data, summary=saved.summary())

    def delete_session(self, session_id):
        if self.practice and self.practice.data["id"] == session_id:
            if not self.practice.data["ended"]:
                raise ValueError("Finish or abandon the active session before deleting it.")
            if self.pending:
                raise ValueError(
                    "Results are waiting to save. Resolve the save error before deleting this session."
                )
        self.store.set_deleted(session_id, True)
        if self.practice and self.practice.data['id'] == session_id:
            self.practice = None
        self.sessions_revision += 1

    def restore_session(self, session_id):
        self.store.set_deleted(session_id, False)
        self.sessions_revision += 1

    def sessions(self, deleted=False):
        """Session list for the selected golfer, read from one committed snapshot.

        Safe to run on a worker thread: it touches no in-memory service state, reads each
        session once (other golfers' sessions are filtered in SQL) and holds no writer lock.
        """
        from domain_schema import active_user, read_session

        result = []
        with self.store.reading() as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    'SELECT s.id FROM sessions s JOIN session_owners o ON o.session_id=s.id '
                    'WHERE o.user_id=? AND (s.deleted_at IS NOT NULL)=? ORDER BY s.started DESC',
                    (active_user(connection), int(deleted)),
                )
            ]
            loaded = [read_session(connection, session_id) for session_id in ids]
        for data in loaded:
            session = restore_model(PuttingSession.from_data(self.store, data))
            result.append(
                dict(
                    id=data['id'],
                    started=data['started'],
                    ended=data['ended'],
                    drill=data['drill'],
                    random_pace=data.get('random_pace', False),
                    abandoned=data.get('abandoned', False),
                    practice_type=data.get('practice_type', 'putting'),
                    demo=data.get('demo', False),
                    session_kind=data.get('session_kind'),
                    captured=len(data['shots']),
                    summary=session.summary(),
                )
            )
        return result
