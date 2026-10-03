"""SQLite and practice authority; external launch monitors connect through Open Connect."""
import asyncio
import copy
import json
import os
import re
import subprocess
import contextlib
import sqlite3
from collections import deque
from pathlib import Path

from shot_input import ShotInput
from putting import PuttingSession
from distance_ladder import DistanceLadderSession, RANGE_FIELDS, restore_model
from storage import Store, database_path, import_legacy, atomic_json
from database_tools import ServiceLease, preserve_legacy
from equipment import default_catalog, edit_catalog, selection
from driving_range import DrivingRangeSession, DRIVING_FIELDS, demo_event

from collection import CollectionSession, COLLECTION_FIELDS
from golf_sim import GolfSimSession, GAME_FIELDS, simulated_event

ROOT = Path(__file__).resolve().parent
DRILLS = [
    dict(id='golf-sim', title='Meadow One · 2D golf', description='Play an original par four with estimated lies and putting.', drill='2D golf', category='PLAY', random_pace=False),
    dict(id='wedge-matrix', title='Wedge matrix', description='Map each wedge at your own swing lengths and find a shot for every yardage.', drill='Wedge matrix', category='WEDGES', random_pace=False),
    dict(id='bag-mapping', title='Bag mapping / gapping', description='Collect per-club samples and discover distance gaps and overlaps.', drill='Bag mapping', category='FULL SWING', random_pace=False),
    dict(id='driving-range', title='Driving range', description='Free practice, shot dispersion, flight estimates and a workspace to review your shots.', drill='Driving range', category='FULL SWING', random_pace=False),
    dict(id='distance-ladder', title='Distance ladder', description='Build carry or total-distance control with wedges, irons and custom yardages.', drill='Distance ladder', category='FULL SWING', random_pace=False),
    dict(id="pace", title="Pace consistency", description="Repeat a speed target and build a consistent stroke.", drill="Pace consistency", random_pace=False),
    dict(id="line", title="Start line", description="Train your launch direction inside a chosen window.", drill="Start line", random_pace=False),
    dict(id="combined", title="Pace + start line", description="Combine pace and direction in one scored session.", drill="Pace + start line", random_pace=False),
    dict(id="random", title="Random pace", description="A fresh target after every putt. Stay adaptable.", drill="Pace + start line", random_pace=True),
    dict(id="ladder", title="Putting ladder", description="Climb distance targets on a flat virtual green. Train estimated short/long control.", drill="Putting ladder", random_pace=False),
]


def desktop_capture_running():
    """Compatibility hook: this application never owns screen capture."""
    return False


class GolfService:
    def __init__(self, root=ROOT, worker_factory=None, capture_detector=desktop_capture_running, database=None):
        self.root, self.worker_factory, self.capture_detector = Path(root), worker_factory, capture_detector
        db_path = database or (database_path() if self.root == ROOT else self.root / 'data/golfdata.sqlite3')
        self.lease = None if database is False else ServiceLease(db_path)
        self.store = None
        try:
            self.store = None if database is False else Store(db_path)
            if self.store and not self.store.migrated():
                if self.capture_detector():
                    raise OSError('Stop desktop capture before migrating legacy data.')
                preserve_legacy(self.root, self.store.path.parent / 'backups')
                import_legacy(self.store, self.root)
                self.store.backup()
        except BaseException:
            if self.store:
                self.store.close()
            if self.lease:
                self.lease.close()
            raise
        self.receipt_dir = self.store.path.parent / 'receipts' if self.store else None
        self.context_path = self.store.path.parent / 'capture-context.json' if self.store else None
        self.worker = self.practice = None
        self.capture_lock = asyncio.Lock()
        self.capture = dict(running=False, stopping=False, mode=None, status="Waiting for shot source", connected=False,
                            fps=0, drops=0, image=None, error="")
        self.settings = dict(host='127.0.0.1', port=921, enabled=False)
        self.displays = []
        self.input_context = {}
        self.input = ShotInput(self, port=int(os.environ.get('TRACELOFT_INPUT_PORT', '900')) if self.root == ROOT else 0)
        self.history, self.logs = deque(maxlen=50), deque(maxlen=100)
        self.latest_read = None
        self.pending = deque()
        self.save_error = ""
        self.last_retry = 0
        self.access = dict(lan=False, addresses=[], port=8765)
        self.sessions_revision = 0
        self.equipment = self.store.equipment_catalog() if self.store else default_catalog()
        self.publish_context()

    def publish_context(self):
        active = self.practice and not self.practice.data['ended'] and not self.practice.data.get('demo')
        self.input_context = dict(practice_session_id=self.practice.data['id'] if active else None,
            required_distance=self.practice.data.get('range_metric') if active else None,
            equipment_selection=copy.deepcopy(self.practice.data.get('equipment_selection')) if active else None,
            collection_context={'swing_label':self.practice.data.get('swing_label')} if active else None,
            game_context=self.practice.context() if active and isinstance(self.practice,GolfSimSession) else None,
            range_context={k:self.practice.data[k] for k in ('range_target','range_width','range_depth')}
                if active and self.practice.data.get('session_kind')=='driving_range' else None)
        return True

    def load_session(self, session_id, deleted=False):
        if self.store:
            return restore_model(PuttingSession.from_store(self.store, session_id, deleted))
        path = self.session_path(session_id)
        return restore_model(PuttingSession.load(path.parent / '.trash' / path.name if deleted else path))

    def snapshot(self):
        return copy.deepcopy(dict(capture=self.capture, settings=self.settings, profiles={}, displays=[], input_port=self.input.port, relay=self.input.relay.state, input=self.input.state,
             practice=self.practice.data if self.practice else None, summary=self.practice.summary() if self.practice else None,
             practice_error=self.save_error, history=list(self.history), logs=list(self.logs), read=self.latest_read,
             access=self.access, sessions_revision=self.sessions_revision, equipment=self.equipment,
             storage=dict(engine='sqlite' if self.store else 'legacy_test', path=str(self.store.path) if self.store else None,
                          backup='local_only')))

    def ingest(self, event):
        kind = event.get("kind")
        if kind == "frame":
            self.capture.update({key: event[key] for key in ("status", "connected", "fps", "drops", "image", "error") if key in event})
        elif kind == "read":
            self.latest_read = event
        elif kind == "record":
            if 'equipment_selection' not in event and self.practice and self.practice.data.get('practice_type') == 'full_swing' and event.get('practice_session_id', self.practice.data['id']) == self.practice.data['id']:
                event = dict(event, equipment_selection=copy.deepcopy(self.practice.data.get('equipment_selection')))
            self.history.appendleft(event)
            if self.store or (self.practice and not self.practice.data["ended"] and event.get("result") in ("sent", "validated")):
                self.pending.append(event)
                self.flush_practice()
        elif kind in ("error", "log"):
            self.logs.append(event.get("message", ""))
            if kind == "error":
                self.capture["error"] = event.get("message", "")

    def flush_practice(self):
        while self.pending and (self.practice or self.store):
            event = self.pending[0]
            target = self.practice
            if self.store and 'practice_session_id' in event:
                sid = event['practice_session_id']
                target = self.practice if self.practice and self.practice.data['id'] == sid else None
                if sid and not target:
                    try:
                        target = self.load_session(sid)
                    except FileNotFoundError:
                        target = None
            previous = copy.deepcopy(target.data) if target else None
            try:
                with self.store.transaction() if self.store else contextlib.nullcontext():
                    receipt_id, fresh = self.store.ingest(event) if self.store else (None, True)
                    practice_event = dict(event, receipt_id=receipt_id) if self.store else event
                    added = target.add(practice_event) if fresh and target else False
            except (OSError, ValueError) as exc:
                if target:
                    target.data = previous
                self.save_error = f"Practice save failed; waiting to retry: {exc}"
                return
            self.pending.popleft()
            if self.receipt_dir and event.get('receipt_id'):
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
        if not self.receipt_dir or self.pending:
            return
        try:
            events = [json.loads(p.read_text('utf-8')) for p in self.receipt_dir.glob('*.json')]
            events.sort(key=lambda event: event.get('captured_at',''))
            self.pending.extend(events)
            self.flush_practice()
        except (OSError, ValueError) as exc:
            self.save_error = f'Receipt recovery failed: {exc}'

    def backup_after_session(self):
        if self.store:
            try:
                self.store.backup()
            except (OSError, sqlite3.Error) as exc:
                self.capture['error'] = f'Session saved; local backup failed: {exc}'

    def drain_worker(self):
        # Retained call sites drain legacy recovery records; external receipt acceptance is atomic.
        return

    async def run(self):
        self.publish_context()
        while True:
            self.input.tick()
            self.drain_worker()
            now = asyncio.get_running_loop().time()
            if self.pending and now - self.last_retry > 5:
                self.flush_practice()
                self.last_retry = now
            if not self.pending:
                self.recover_receipts()
            await asyncio.sleep(.05)

    async def shutdown(self):
        await self.input.close()
        self.flush_practice()
        if self.store:
            try:
                self.publish_context()
                with self.store.transaction():
                    self.store.connection.execute("INSERT OR REPLACE INTO metadata VALUES('active_session.v1',?)",
                        (json.dumps(self.practice.data['id'] if self.practice and not self.practice.data['ended'] else None),))
                self.store.backup()
            finally:
                self.store.close()
                self.lease.close()

    def create_practice(self, params):
        if self.practice and not self.practice.data["ended"]:
            raise ValueError("Finish or abandon the active session before launching another drill.")
        self.drain_worker()  # Shots queued before launch belong to the preceding session.
        if params['drill']=='2D golf':
            from course_import import load
            selected=selection(self.equipment,params.get('range_bag_id',''),params.get('range_club_id',''))
            self.practice=GolfSimSession(self.root/'practice_sessions',store=self.store,equipment_selection=selected,
                course=load(self.store,params.get('game_course_id','meadow-one-v2')),
                **{k:v for k,v in params.items() if k in GAME_FIELDS or k in ('demo','stimp')})
        elif params['drill'] in ('Bag mapping','Wedge matrix'):
            self.practice = CollectionSession(self.root / 'practice_sessions', self.equipment,
                params.get('range_bag_id',''), params.get('collection_clubs',[]),
                samples=params.get('collection_samples',5), metric=params.get('range_metric','carry'),
                demo=params.get('demo',False), handedness=params.get('handedness','right_handed'), store=self.store,
                swing_labels=params.get('swing_labels') if params['drill']=='Wedge matrix' else None)
        elif params['drill'] == 'Driving range':
            selected = selection(self.equipment, params.get('range_bag_id', ''), params.get('range_club_id', ''))
            self.practice = DrivingRangeSession(self.root / 'practice_sessions', store=self.store,
                equipment_selection=selected, **{k:v for k,v in params.items() if k in DRIVING_FIELDS})
        elif params['drill'] == 'Distance ladder':
            selected = selection(self.equipment, params.get('range_bag_id', ''), params.get('range_club_id', ''))
            self.practice = DistanceLadderSession(self.root / 'practice_sessions', store=self.store,
                equipment_selection=selected,
                **{k:v for k,v in params.items() if k in RANGE_FIELDS and k not in ('range_bag_id', 'range_club_id')})
        else:
            self.practice = PuttingSession(self.root / 'practice_sessions', store=self.store,
                **{k:v for k,v in params.items() if k not in RANGE_FIELDS and k not in DRIVING_FIELDS and k not in COLLECTION_FIELDS and k not in GAME_FIELDS})
        self.publish_context()
        self.sessions_revision += 1
        return self.practice.data

    def edit_bag(self, revision, name, bag_id=None, clubs=None):
        updated, edited_id = edit_catalog(self.equipment, revision, name, bag_id, clubs)
        self.drain_worker()
        self.flush_practice()
        if self.pending:
            raise ValueError('Results are waiting to save. Resolve the save error before editing bags.')
        previous = copy.deepcopy(self.practice.data) if self.practice else None
        try:
            with self.store.transaction() if self.store else contextlib.nullcontext():
                if self.store:
                    self.store.save_equipment_catalog(updated)
                current = self.practice.data.get('equipment_selection') if self.practice and not self.practice.data['ended'] else None
                if current and current['bag_id'] == edited_id:
                    bag = next(b for b in updated['bags'] if b['id'] == edited_id)
                    club_id = current['club_id'] if any(c['id'] == current['club_id'] for c in bag['clubs']) else ''
                    self.practice.data['equipment_selection'] = selection(updated, edited_id, club_id)
                    self.practice.save()
        except (OSError, sqlite3.Error, ValueError):
            if self.practice:
                self.practice.data = previous
            raise
        self.equipment = updated
        self.publish_context()
        self.sessions_revision += 1
        return edited_id

    def select_equipment(self, session_id, bag_id, club_id):
        if not self.practice or self.practice.data['id'] != session_id or self.practice.data['ended'] or self.practice.data.get('practice_type') != 'full_swing':
            raise ValueError('Only the active full-swing ladder can change its next-shot equipment.')
        selected = selection(self.equipment, bag_id, club_id)
        self.drain_worker()
        self.flush_practice()
        if self.pending:
            raise ValueError('Results are waiting to save. Resolve the save error before changing clubs.')
        if self.practice.data['ended']:
            raise ValueError('This ladder has completed; new club selection was not applied.')
        previous = copy.deepcopy(self.practice.data)
        try:
            self.practice.data['equipment_selection'] = selected
            self.practice.save()
        except (OSError, sqlite3.Error, ValueError):
            self.practice.data = previous
            raise
        self.publish_context()
        self.sessions_revision += 1

    def select_collection_cell(self, session_id, club_id, swing_label):
        saved=self.range_session(session_id)
        if saved is not self.practice or saved.data['ended'] or saved.data.get('collection_kind')!='wedge':
            raise ValueError('Only an active wedge matrix can select a cell.')
        if swing_label not in saved.data['swing_labels']:
            raise ValueError('Choose a planned swing label.')
        planned=next((p for p in saved.data['collection_plan'] if p['club_id']==club_id),None)
        if not planned:
            raise ValueError('Choose a planned wedge.')
        selected=selection(self.equipment,planned['bag_id'],club_id)
        self.drain_worker();self.flush_practice()
        if self.pending:
            raise ValueError('Resolve pending saves before changing your swing label.')
        previous=copy.deepcopy(saved.data)
        try:
            saved.data.update(equipment_selection=selected,swing_label=swing_label)
            saved.save()
        except (OSError,sqlite3.Error,ValueError):
            saved.data=previous
            raise
        self.publish_context();self.sessions_revision+=1

    def resume_practice(self, session_id):
        """Maintenance handoff: restore an unchanged active drill after a service reload."""
        if self.practice or self.worker:
            raise ValueError("Only an idle service can accept a session handoff.")
        saved = self.load_session(session_id)
        if saved.data["ended"] or saved.data.get("abandoned"):
            raise ValueError("Only an unfinished session can be handed over.")
        self.practice = saved
        self.publish_context()
        self.sessions_revision += 1

    def range_session(self, session_id):
        saved = self.practice if self.practice and self.practice.data['id']==session_id else self.load_session(session_id)
        if saved.data.get('session_kind')!='driving_range':
            raise ValueError('This action requires a driving range session.')
        return saved

    def game_action(self, session_id, action, params):
        self.drain_worker();self.flush_practice()
        saved=self.practice
        if self.pending:
            raise ValueError('Resolve pending saves before changing the round.')
        if not isinstance(saved,GolfSimSession) or saved.data['id']!=session_id or saved.data['ended']:
            raise ValueError('This action requires the active round.')
        if params['turn']!=saved.data['game']['turn']:
            raise ValueError('The round advanced. Wait for the updated position before hitting again.')
        previous=copy.deepcopy(saved.data)
        try:
            with self.store.transaction() if self.store else contextlib.nullcontext():
                if action=='aim':saved.set_aim(params['x'],params['y'],params['turn'])
                elif action=='simulate':
                    event=simulated_event(saved,params['distance_yd'],params['offline_yd'])
                    if self.store:self.store.ingest(event,provenance='synthetic_demo')
                    saved.add(event)
                else:raise ValueError('Unknown game action.')
        except (OSError,sqlite3.Error,ValueError):
            saved.data=previous
            raise
        self.publish_context();self.sessions_revision+=1
        if saved.data['ended']:self.backup_after_session()

    def game_preview(self, session_id):
        from club_preview import build_preview
        saved=self.practice if self.practice and self.practice.data['id']==session_id else self.load_session(session_id)
        if not isinstance(saved,GolfSimSession):raise ValueError('Choose a golf round.')
        return build_preview(self.store.list_sessions() if self.store else [],saved.data)

    def game_recommendations(self, session_id):
        from analysis import build_report
        saved=self.practice if self.practice and self.practice.data['id']==session_id else self.load_session(session_id)
        if not isinstance(saved,GolfSimSession):raise ValueError('Choose a golf round.')
        bag=(saved.data.get('equipment_selection') or {}).get('bag_id')
        if not bag or saved.data['game']['lie']=='green':return []
        sessions=self.store.list_sessions() if self.store else []
        collections=[s for s in sessions if s.get('collection_kind')]
        report=build_report(collections,dict(mode='demo' if saved.data['demo'] else 'real',bag=bag,metric='total'))
        factor=1-saved.data['game_settings'].get(saved.data['game']['lie']+'_percent',0)/100
        needed=saved.summary()['remaining_yd']/factor
        available=[g for g in report['groups'] if g['metrics']['total']['count']>=5]
        available.sort(key=lambda g:abs(g['metrics']['total']['median']-needed))
        return [dict(club_id=g['club_id'],club_label=g['club_label'],swing_label=g['swing_label'],
            median_yd=g['metrics']['total']['median'],iqr_yd=g['metrics']['total']['iqr'],
            adjusted_yd=g['metrics']['total']['median']*factor,count=g['metrics']['total']['count']) for g in available[:3]]

    def cleanup_range(self, session_id, params):
        self.drain_worker()
        self.flush_practice()
        if self.pending:
            raise ValueError('Resolve the pending shot save before cleanup.')
        saved=self.range_session(session_id)
        equipment=selection(self.equipment,params.get('bag_id',''),params.get('club_id','')) if params['action']=='retag' else None
        previous=copy.deepcopy(saved.data)
        try:
            with self.store.transaction() if self.store else contextlib.nullcontext():
                batch=saved.cleanup(params['action'],params['keys'],params['revision'],params['reason'],
                                    equipment,params.get('batch_id'))
                if self.store:
                    self.store._audit(session_id,'range_cleanup',saved.data['cleanup_history'][-1])
        except (OSError,sqlite3.Error,ValueError):
            saved.data=previous
            raise
        self.sessions_revision+=1
        return dict(practice=saved.data,summary=saved.summary(),batch_id=batch)

    def target_range(self, session_id, target, width, depth):
        self.drain_worker()
        if self.pending:
            raise ValueError('Resolve the pending shot save before changing the target.')
        saved=self.range_session(session_id)
        if saved is not self.practice or saved.data['ended']:
            raise ValueError('Only the active range can change its next-shot target.')
        previous=copy.deepcopy(saved.data)
        try:
            saved.data.update(range_target=target,target=target,range_width=width,range_depth=depth)
            saved.save()
        except (OSError,sqlite3.Error,ValueError):
            saved.data=previous
            raise
        self.publish_context()
        self.sessions_revision+=1

    def simulate_range(self, session_id, count):
        saved=self.range_session(session_id)
        if saved is not self.practice or saved.data['ended'] or not saved.data.get('demo'):
            raise ValueError('Simulated shots are only available in an active Demo range.')
        if count not in (1,10):
            raise ValueError('Generate one shot or a set of ten.')
        previous=copy.deepcopy(saved.data)
        try:
            with self.store.transaction() if self.store else contextlib.nullcontext():
                for _ in range(count):
                    event=demo_event(saved,len(saved.data['shots'])+1)
                    if self.store:
                        self.store.ingest(event,provenance='synthetic_demo')
                    saved.add(event)
        except (OSError,sqlite3.Error,ValueError):
            saved.data=previous
            raise
        self.sessions_revision+=1

    def change_practice(self, session_id, action, key=None):
        if not self.practice or self.practice.data["id"] != session_id:
            raise ValueError("This session is no longer active. Refresh before changing it.")
        if action=='exclude' and self.practice.data.get('session_kind')=='driving_range':
            return self.exclude_saved(session_id,key)
        self.drain_worker()
        self.flush_practice()
        if self.pending:
            raise ValueError("Results are waiting to save. Resolve the save error before changing the session.")
        previous = copy.deepcopy(self.practice.data)
        try:
            if action == "finish":
                self.practice.finish()
            elif action == "abandon":
                self.practice.abandon()
            elif action == "exclude":
                if not any(s["key"] == key for s in self.practice.data["shots"]):
                    raise ValueError("Choose a shot from this session.")
                self.practice.toggle_excluded(key)
        except OSError:
            self.practice.data = previous
            raise
        if action == "abandon":
            self.practice = None
        self.publish_context()
        self.sessions_revision += 1
        if action in ('finish', 'abandon'):
            self.backup_after_session()

    def session_path(self, session_id):
        if not re.fullmatch(r"[0-9a-f]{32}", session_id):
            raise ValueError("Invalid session identifier.")
        return self.root / "practice_sessions" / (session_id + ".json")

    def exclude_saved(self, session_id, key):
        saved=self.practice if self.practice and self.practice.data['id']==session_id else self.load_session(session_id)
        if saved.data.get('session_kind')=='driving_range':
            shot=next((s for s in saved.data['shots'] if s['key']==key),None)
            if not shot:
                raise ValueError('Choose a shot from this session.')
            return self.cleanup_range(session_id,dict(action='include' if shot['excluded'] else 'exclude',
                keys=[key],revision=saved.data['cleanup_revision'],reason='Single-shot inclusion change'))
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
        path = self.session_path(session_id)
        if self.practice and self.practice.data["id"] == session_id:
            if not self.practice.data["ended"]:
                raise ValueError("Finish or abandon the active session before deleting it.")
            if self.pending:
                raise ValueError("Results are waiting to save. Resolve the save error before deleting this session.")
        if self.store:
            self.store.set_deleted(session_id, True)
            if self.practice and self.practice.data['id'] == session_id:
                self.practice = None
            self.sessions_revision += 1
            return
        destination = path.parent / ".trash" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise ValueError("A deleted copy of this session already exists. Restore it first.")
        path.rename(destination)
        if self.practice and self.practice.data["id"] == session_id:
            self.practice = None
        self.sessions_revision += 1

    def restore_session(self, session_id):
        if self.store:
            self.store.set_deleted(session_id, False)
            self.sessions_revision += 1
            return
        path = self.session_path(session_id)
        source = path.parent / ".trash" / path.name
        if path.exists():
            raise ValueError("This session already exists; it was not overwritten.")
        source.rename(path)
        self.sessions_revision += 1

    def sessions(self, deleted=False):
        result = []
        if self.store:
            for data in self.store.list_sessions(deleted):
                session = self.load_session(data['id'], deleted)
                result.append(dict(id=data['id'],started=data['started'],ended=data['ended'],drill=data['drill'],
                    random_pace=data.get('random_pace',False),abandoned=data.get('abandoned',False),practice_type=data.get('practice_type','putting'),demo=data.get('demo',False),session_kind=data.get('session_kind'),
                    captured=len(data['shots']),summary=session.summary()))
            return result
        folder = self.root / "practice_sessions"
        if deleted:
            folder = folder / ".trash"
        for path in folder.glob("*.json"):
            try:
                session = restore_model(PuttingSession.load(path))
                result.append(dict(id=session.data["id"], started=session.data["started"], ended=session.data["ended"],
                                   drill=session.data["drill"], random_pace=session.data.get("random_pace", False),
                                   abandoned=session.data.get("abandoned", False), practice_type=session.data.get('practice_type','putting'), captured=len(session.data["shots"]), summary=session.summary()))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result, key=lambda s: s["started"], reverse=True)
