"""Versioned source-neutral shot input and optional live-only simulator output."""

import asyncio
import copy
import ipaddress
import json
import math
import re
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone

from storage import encoded, digest, now

FIELDS = {
    'ball_speed': (0, 250),
    'launch_ang': (-90, 90),
    'launch_dir': (-90, 90),
    'back_spin': (-50000, 50000),
    'side_spin': (-50000, 50000),
    'total_spin': (0, 50000),
    'spin_axis': (-180, 180),
    'carry': (0, 1000),
    'total': (0, 1000),
    'offline': (-1000, 1000),
    'peak_height': (0, 1000),
    'descent_ang': (-90, 90),
    'curve': (-1000, 1000),
    'hang_time': (0, 60),
}
FIELDS.update(
    {
        key: (-10000, 10000)
        for key in (
            'club_speed',
            'attack_angle',
            'face_angle',
            'dynamic_lie',
            'dynamic_loft',
            'club_path',
            'closure_rate',
            'impact_vertical',
            'impact_horizontal',
        )
    }
)
FIELDS['smash_factor'] = (0, 5)
BALL = {
    'Speed': 'ball_speed',
    'VLA': 'launch_ang',
    'HLA': 'launch_dir',
    'BackSpin': 'back_spin',
    'SideSpin': 'side_spin',
    'TotalSpin': 'total_spin',
    'SpinAxis': 'spin_axis',
    'CarryDistance': 'carry',
}


def validate(envelope):
    if not isinstance(envelope, dict) or envelope.get('schema') != 'traceloft.shot.v1':
        raise ValueError('Expected traceloft.shot.v1.')
    if len(encoded(envelope).encode()) > 262144:
        raise ValueError('Shot envelope exceeds 256 KiB.')
    event = copy.deepcopy(envelope.get('event'))
    if not isinstance(event, dict):
        raise ValueError('A shot event is required.')
    for key in ('receipt_id', 'producer_id', 'session_id'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', str(event.get(key, ''))):
            raise ValueError('Invalid ' + key)
    if type(event.get('seq')) is not int or event['seq'] < 0:
        raise ValueError('Invalid shot sequence.')
    if event.get('simulated'):
        raise ValueError('Synthetic events use the explicit demo controls.')
    try:
        captured = datetime.fromisoformat(event['captured_at'])
        if captured.tzinfo is None:
            raise ValueError()
        age = (datetime.now(timezone.utc) - captured).total_seconds()
        if age < -5:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ValueError('Invalid timezone-aware capture time.') from None
    if event.get('result') not in ('validated', 'failed', 'logged'):
        raise ValueError('Invalid acquisition result.')
    vals = event.get('vals')
    if not isinstance(vals, dict):
        raise ValueError('Metrics are required.')
    for key, value in vals.items():
        if key == 'fs_shot':
            continue  # Legacy source label, never a measurement mapping.
        if key not in FIELDS:
            raise ValueError('Unsupported metric: ' + key)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not FIELDS[key][0] <= value <= FIELDS[key][1]
        ):
            raise ValueError('Invalid metric: ' + key)
    if event['result'] == 'validated' and any(
        vals.get(k) is None for k in ('ball_speed', 'launch_ang', 'launch_dir')
    ):
        raise ValueError('Accepted shots require ball speed and launch angles.')
    if not isinstance(event.get('source_configuration'), dict):
        raise ValueError('Source provenance is required.')
    for key in ('equipment_selection', 'range_context', 'collection_context', 'game_context'):
        if event.get(key) is not None and not isinstance(event[key], dict):
            raise ValueError('Invalid ' + key)
    sid = event.get('practice_session_id')
    if sid is not None and not re.fullmatch('[a-f0-9]{32}', str(sid)):
        raise ValueError('Invalid practice identity.')
    # Keep the durable envelope identity stable across upgrades/recovered receipt retries.
    # Store archives the current v2 normalization specification on the observation itself.
    event.update(
        kind='record',
        wire_digest=digest(encoded(event).encode()),
        mapping_id='traceloft.normalized.v1',
    )
    return event, age <= 15 and not envelope.get('recovered', False)


def live_estimate(event):
    """The live-view copy of a stored event, with an OpenGolfCoach flight estimate when the source
    reported no carry (e.g. Premier memory capture). Display only: the stored measurements never
    change (range-family drills compute their own OpenGolfCoach distances, D63). Shots without
    measured spin and launch (putts) get no estimate; a putt is not a flight."""
    from flight_model import MODEL, predict, with_spin_pair

    vals = with_spin_pair(event['vals'])
    if vals.get('carry') is not None or not (vals.get('total_spin') or 0) > 0:
        return event
    if not (vals.get('launch_ang') or 0) > 0:
        return event
    flight = predict(vals)
    if flight.get('status') != 'ready':
        return event
    m = flight['metrics']
    return dict(
        event,
        estimate=dict(
            model=MODEL, carry=m['carry_yd'], total=m['total_yd'], offline=m['offline_yd']
        ),
    )


# Estimates a source may report alongside its measurements (D70): wire field -> (metric key,
# canonical unit, factor from the source unit, source unit). Stored in source_estimates only,
# never as measurements, so they can be compared with TraceLoft's own estimates.
SOURCE_ESTIMATES = {
    'face_angle': ('club.face_angle', 'deg', 1, 'deg'),
    'dynamic_lie': ('club.dynamic_lie', 'deg', 1, 'deg'),
    'dynamic_loft': ('club.dynamic_loft', 'deg', 1, 'deg'),
    'closure_rate': ('club.closure_rate', 'deg/s', 1, 'deg/s'),
    'impact_horizontal': ('impact.horizontal', 'mm', 1, 'mm'),
    'impact_vertical': ('impact.vertical', 'mm', 1, 'mm'),
    'carry': ('flight.carry_distance', 'm', 0.9144, 'yd'),
}


def source_estimates(value):
    """The validated TraceLoft.SourceEstimates block (D70), or None.

    {Estimator: name, Values: {wire field: number}}. A malformed block is refused like any other
    invalid extension; a number outside the field's range is left out (the raw packet keeps it),
    because an implausible estimate must not cost the shot's measurements.
    """
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get('Values'), dict):
        raise ValueError('Invalid source estimates.')
    estimator = value.get('Estimator')
    if not isinstance(estimator, str) or not re.fullmatch(r'[A-Za-z0-9 _.-]{1,100}', estimator):
        raise ValueError('Invalid source estimator.')
    values = {}
    for key, number in value['Values'].items():
        if key not in SOURCE_ESTIMATES:
            raise ValueError('Unsupported source estimate: ' + str(key)[:50])
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError('Invalid source estimate: ' + key)
        if math.isfinite(number) and FIELDS[key][0] <= number <= FIELDS[key][1]:
            values[key] = number
    return dict(estimator=estimator, values=values) if values else None


ALERT_LEVELS = ('error', 'warning')


def source_alerts(extension):
    """The alerts a source's heartbeat carries (TraceLoft.Alerts, D73), cleaned for display:
    at most 5 of {level: 'error'|'warning', message: <=300 chars}. Malformed entries are dropped,
    never refused: they are status text, not shot data."""
    alerts = extension.get('Alerts') if isinstance(extension, dict) else None
    if not isinstance(alerts, list):
        return []
    cleaned = []
    for alert in alerts[:5]:
        if not isinstance(alert, dict) or alert.get('Level') not in ALERT_LEVELS:
            continue
        message = alert.get('Message')
        if isinstance(message, str) and message.strip():
            cleaned.append(dict(level=alert['Level'], message=message.strip()[:300]))
    return cleaned


IMPORT_PROVENANCE = 'ipad_import'
OVERLAP_DAYS = 30  # how far back an imported shot is compared with live captures


def import_batch(value):
    """The validated TraceLoft.Import block of an iPad table import (D65), or None for live shots.

    BatchId (32 hex) names the import and becomes its driving range session's id; Index/Count order
    the shots (the session is finished at the last one); BagId/ClubId tag them; Label names the import.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError('Invalid import block.')
    batch_id, index, count = value.get('BatchId'), value.get('Index'), value.get('Count')
    if not isinstance(batch_id, str) or not re.fullmatch('[a-f0-9]{32}', batch_id):
        raise ValueError('Invalid import batch.')
    if type(index) is not int or type(count) is not int or not 1 <= index <= count <= 10000:
        raise ValueError('Invalid import position.')
    text = {k: value.get(k, '') for k in ('BagId', 'ClubId', 'Label')}
    if any(not isinstance(v, str) or len(v) > 200 for v in text.values()):
        raise ValueError('Invalid import labels.')
    return dict(
        batch_id=batch_id,
        index=index,
        count=count,
        bag_id=text['BagId'],
        club_id=text['ClubId'],
        label=text['Label'] or 'iPad import',
    )


def find_overlap(connection, vals):
    """A live-captured shot (not an import) from the last OVERLAP_DAYS with the same ball speed, launch
    angles and, when both have it, club speed: the imported shot was probably already captured live.
    Returns {shot_id, captured} or None. Display precision is 0.1, so values within 0.051 match."""
    keys = ('ball_speed', 'launch_ang', 'launch_dir')
    if any(not isinstance(vals.get(k), (int, float)) for k in keys):
        return None
    since = (datetime.now(timezone.utc) - timedelta(days=OVERLAP_DAYS)).isoformat()
    club = vals.get('club_speed') if isinstance(vals.get('club_speed'), (int, float)) else None
    row = connection.execute(
        '''SELECT m.shot_id, m.created_at FROM shot_source_metrics m
           JOIN observations o ON o.id = m.observation_id
           WHERE o.provenance != ? AND m.created_at >= ?
             AND abs(m.ball_speed_mph - ?) < 0.051
             AND abs(m.vertical_launch_angle_deg - ?) < 0.051
             AND abs(m.horizontal_launch_angle_deg - ?) < 0.051
             AND (? IS NULL OR m.club_head_speed_mph IS NULL OR abs(m.club_head_speed_mph - ?) < 0.051)
           ORDER BY m.created_at DESC LIMIT 1''',
        (
            IMPORT_PROVENANCE,
            since,
            vals['ball_speed'],
            vals['launch_ang'],
            vals['launch_dir'],
            club,
            club,
        ),
    ).fetchone()
    return dict(shot_id=row[0], captured=row[1]) if row else None


LOCAL_SIMULATOR_HOSTS = ('localhost', '127.0.0.1', '::1')


def simulator_host(host):
    """The simulator address to dial: this PC, or a private-network IP address such as a GSPro PC on
    the same LAN (D69). Host names and public addresses are refused, so the relay never resolves a
    name or sends shots off the local network."""
    if host in LOCAL_SIMULATOR_HOSTS:
        return host
    try:
        address = ipaddress.ip_address(host if isinstance(host, str) else '')
    except ValueError:
        address = None
    if address is None or not address.is_private or address.is_unspecified:
        raise ValueError(
            'Use 127.0.0.1 for this PC, or the simulator PC\'s network address (such as 10.10.0.190).'
        )
    return str(address)


def source_delivers(packet):
    """Whether the sender declared that it sends shots to the simulator itself (TraceCapture)."""
    extension = packet.get('TraceLoft')
    return isinstance(extension, dict) and extension.get('SimulatorDelivery') == 'source'


class Relay:
    """Direct optional simulator output. A reconnect never replays a stored shot.

    While a connected shot source delivers to the simulator itself (`SimulatorDelivery: 'source'`),
    the relay steps aside: it holds no simulator connection, so the source can connect (GSPro accepts
    one client), and it forwards nothing, so no shot reaches the simulator twice. The destination
    setting still applies: it reaches the source through TraceLoft.Context['simulator'].
    """

    def __init__(self):
        self.writer = None
        self.task = None
        self.number = 0
        self.ready = False
        self.delegated = False
        self.state = dict(
            destination='off',
            enabled=False,
            host='127.0.0.1',
            port=921,
            connected=False,
            status='Forwarding off',
            last_response=None,
            player={},
            sent=0,
            delegated=False,
        )
        self.lock = asyncio.Lock()

    async def configure(self, settings, input_port):
        if not isinstance(settings, dict):
            raise ValueError('Destination settings must be an object.')
        destination = settings.get('destination', 'off')
        if destination not in ('off', 'gspro', 'infinite_tees'):
            raise ValueError('Select Off, GSPro or Infinite Tees.')
        host = simulator_host(settings.get('host', '127.0.0.1'))
        port = settings.get('port', 999 if destination == 'infinite_tees' else 921)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('Simulator port must be between 1 and 65535.')
        if port == input_port and host in LOCAL_SIMULATOR_HOSTS:
            raise ValueError('Simulator port must differ from input port.')
        await self.close()
        self.state.update(
            destination=destination,
            enabled=destination != 'off',
            host=host,
            port=port,
            last_response=None,
            player={},
        )
        if self.state['enabled']:
            self.task = asyncio.create_task(self._connect())

    async def _connect(self):
        from open_connect import Frames, heartbeat

        while self.state['enabled']:
            if self.delegated:
                self.state['status'] = 'Sent directly by the shot source'
                await asyncio.sleep(0.5)
                continue
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.state['host'], self.state['port']), 2
                )
                self.writer = writer
                self.state.update(
                    connected=True, status='Connected; waiting for simulator response'
                )
                await self.send(heartbeat(self.ready, self.number))
                frames = Frames()
                while True:
                    try:
                        data = await asyncio.wait_for(reader.read(8192), 5)
                    except asyncio.TimeoutError:
                        if not await self.send(heartbeat(self.ready, self.number)):
                            raise ConnectionError('Heartbeat write failed')
                        continue
                    if not data:
                        raise ConnectionError('Simulator disconnected')
                    for reply in frames.feed(data):
                        if type(reply.get('Code')) is not int:
                            raise ValueError('Invalid simulator response')
                        self.state['last_response'] = reply
                        if reply['Code'] == 201:
                            self.state['player'] = reply.get('Player', {})
                        self.state['status'] = (
                            'Simulator protocol acknowledged'
                            if reply['Code'] in (200, 201)
                            else str(reply.get('Message', 'Simulator error'))[:200]
                        )
            except asyncio.CancelledError:
                raise
            except (OSError, ValueError, UnicodeError, asyncio.TimeoutError) as ex:
                self.state['status'] = 'Disconnected: ' + str(ex)
            finally:
                if writer:
                    writer.close()
                self.writer = None
                self.state['connected'] = False
                self.state['player'] = {}
            if not self.delegated:
                await asyncio.sleep(2)

    def delegate(self, delegated):
        """Step aside while the connected source delivers to the simulator (see the class doc)."""
        if delegated == self.delegated:
            return
        self.delegated = self.state['delegated'] = delegated
        if delegated and self.writer:
            self.writer.close()  # frees the simulator for the source; _connect then idles
        if not delegated and self.state['enabled']:
            self.state['status'] = 'Reconnecting to the simulator'

    async def send(self, payload):
        from open_connect import wire

        async with self.lock:
            writer = self.writer
            if not writer:
                return False
            try:
                writer.write(wire(payload))
                await asyncio.wait_for(writer.drain(), 1)
                return True
            except (OSError, asyncio.TimeoutError):
                writer.close()
                return False

    async def close(self):
        self.state['enabled'] = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        if self.writer:
            self.writer.close()
        self.writer = None
        self.state.update(connected=False, status='Forwarding off', player={})


LOCAL_INPUT = '127.0.0.1'
ANY_MACHINE = '0.0.0.0'  # remote shot input (D66): every interface, e.g. rēlā in a VM or over a VPN


class ShotInput:
    def __init__(self, service, port=900, host=LOCAL_INPUT):
        self.service, self.port, self.host = service, port, host
        self.server = None
        self.relay = Relay()
        self.last_seen = 0
        self.source = None
        self.clients = set()
        self.tasks = set()
        self.accept_lock = asyncio.Lock()
        self.state = dict(
            listening=False,
            port=port,
            remote=host != LOCAL_INPUT,
            peer=None,  # address of the connected source (shown when it is another machine)
            alerts=[],  # the connected source's problems for the golfer, from its heartbeats (D73)
            device=None,
            received=0,
            duplicates=0,
            last_shot=None,
            error='',
        )

    def context(self):
        """Context returned with every Code 200. `simulator` is the user's Relay destination, for a
        source that delivers to the simulator itself ('off' means send nothing)."""
        relay = self.relay.state
        return dict(
            copy.deepcopy(self.service.input_context),
            simulator=dict(
                destination=relay['destination'], host=relay['host'], port=relay['port']
            ),
            # Bags and clubs, so a source can tag an iPad table import (D65) before sending it.
            equipment_catalog=[
                dict(
                    bag_id=bag['id'],
                    bag_name=bag['name'],
                    clubs=[dict(club_id=c['id'], label=c['label']) for c in bag['clubs']],
                )
                for bag in self.service.equipment.get('bags', [])
            ],
        )

    def import_equipment(self, batch):
        """The bag/club selection for an import, or None (untagged) if it is unknown or changed."""
        from equipment import selection

        try:
            return selection(self.service.equipment, batch['bag_id'], batch['club_id'])
        except ValueError:
            return None

    def import_session(self, batch):
        """The driving range session of an import batch: loaded when it exists (retries, restarts),
        else created with the batch id as its id, the chosen bag/club and no target. An unknown or
        changed bag/club leaves the shots untagged rather than refusing the import."""
        from driving_range import DrivingRangeSession

        try:
            return self.service.load_session(batch['batch_id'])
        except FileNotFoundError:
            pass
        return DrivingRangeSession(
            self.service.root / 'practice_sessions',
            store=self.service.store,
            equipment_selection=self.import_equipment(batch),
            range_target=0,
            session_id=batch['batch_id'],
            import_source=dict(
                kind='ipad_table', label=batch['label'], count=batch['count'], imported=now()
            ),
        )

    async def accept_packet(self, packet, connection_id):
        from open_connect import validate_packet, simulator_packet

        vals = validate_packet(packet)
        extension = packet.get('TraceLoft', {})
        if not isinstance(extension, dict):
            raise ValueError('TraceLoft extension must be an object.')
        result = extension.get('Result', 'validated')
        if result not in ('validated', 'failed', 'logged'):
            raise ValueError('Invalid acquisition result.')
        if not vals and result == 'validated':
            return None
        if vals and result != 'validated':
            raise ValueError('Failed acquisition must not claim ball data.')
        seq = packet['ShotNumber']
        context = extension.get('Context', self.context())
        if not isinstance(context, dict):
            raise ValueError('Invalid shot context.')
        metrics = extension.get('Metrics', {})
        if not isinstance(metrics, dict):
            raise ValueError('Invalid extension metrics.')
        for key, value in metrics.items():
            if key in vals and vals[key] != value:
                raise ValueError('Extension contradicts BallData: ' + key)
        vals.update(metrics)
        event = dict(
            kind='record',
            receipt_id=extension.get(
                'ReceiptId', uuid.uuid5(uuid.NAMESPACE_URL, connection_id + ':' + str(seq)).hex
            ),
            producer_id=extension.get('ProducerId', connection_id),
            session_id=extension.get('StreamId', connection_id),
            seq=seq,
            captured_at=extension.get('CapturedAt', now()),
            result=result,
            vals=vals,
            source_configuration=extension.get(
                'Source', dict(acquisition='open_connect', device=packet['DeviceID'])
            ),
            raw_packet=copy.deepcopy(packet),
            **{
                k: context.get(k)
                for k in (
                    'practice_session_id',
                    'user_id',
                    'equipment_selection',
                    'range_context',
                    'collection_context',
                    'game_context',
                )
            },
        )
        evidence = extension.get('Evidence', {})
        if not isinstance(evidence, dict):
            raise ValueError('Invalid source evidence.')
        event.update(
            {
                k: copy.deepcopy(evidence[k])
                for k in ('raw', 'count', 'latency', 'source_time', 'note', 'sent_fields', 'club')
                if k in evidence
            }
        )
        estimates = source_estimates(extension.get('SourceEstimates'))
        if estimates and result == 'validated':
            event['source_estimates'] = estimates
        batch = import_batch(extension.get('Import'))
        if batch:
            # An iPad table import (D65): never live, never forwarded, and never part of the active
            # drill; its shots go to their own driving range session named by the batch id, tagged
            # with the club chosen for the import (not the active drill's context).
            event.update(
                import_batch=batch,
                practice_session_id=batch['batch_id'],
                equipment_selection=self.import_equipment(batch),
                range_context=None,
                collection_context=None,
                game_context=None,
            )
        event, live = validate(
            dict(
                schema='traceloft.shot.v1',
                event=event,
                recovered=extension.get('Recovered', False) or batch is not None,
            )
        )
        event['wire_digest'] = digest(encoded(packet).encode())
        async with self.accept_lock:
            store = self.service.store
            # The writer connection is shared with worker threads; read it only under its lock.
            with store.lock:
                old = store.connection.execute(
                    'SELECT raw_json FROM ingest_events WHERE id=?', (event['receipt_id'],)
                ).fetchone()
            if old:
                if json.loads(old[0]).get('wire_digest') != event['wire_digest']:
                    raise ValueError('Receipt identity conflicts with different data.')
                self.state['duplicates'] += 1
                return dict(
                    accepted=True, duplicate=True, forwarded=False, receipt_id=event['receipt_id']
                )
            target = self.import_session(batch) if batch else self.service.practice
            if not batch and (
                not live
                or not target
                or target.data['id'] != event.get('practice_session_id')
                or target.data['ended']
            ):
                target = None
            previous = copy.deepcopy(target.data) if target else None
            try:
                with store.transaction():
                    overlap = find_overlap(store.connection, event['vals']) if batch else None
                    store.ingest(event, provenance=IMPORT_PROVENANCE if batch else 'open_connect')
                    added = target.add(event) if target else False
                    if batch:
                        if added and overlap:
                            target.data['shots'][-1]['possible_duplicate'] = overlap
                        # Delivery order is not guaranteed: finish once every index has arrived
                        # (a shot the range rejects still counts as delivered).
                        source = target.data.setdefault('import_source', {})
                        received = sorted(set(source.get('received', [])) | {batch['index']})
                        source['received'] = received
                        if len(received) >= batch['count']:
                            target.finish()
                        else:
                            target.save()
            except Exception:
                if target:
                    target.data = previous
                raise
            self.service.remember_record(live_estimate(event), read=not batch)
            self.service.sessions_revision += 1
            self.service.publish_context()
            self.service.save_error = ''
            self.state.update(
                received=self.state['received'] + 1, last_shot=event['captured_at'], error=''
            )
            forwarded = False
            by_source = source_delivers(packet)
            if (
                live
                and result == 'validated'
                and self.relay.state['enabled']
                and not by_source
                and not self.relay.delegated
            ):
                self.relay.number += 1
                forwarded = await self.relay.send(simulator_packet(packet, self.relay.number))
                if forwarded:
                    self.relay.state['sent'] += 1
            try:
                with store.transaction():
                    store.connection.execute(
                        'UPDATE delivery_events SET status=?,evidence_json=? WHERE event_id=?',
                        (
                            'socket_write_reported_unacknowledged'
                            if forwarded
                            # The source sends live shots itself; TraceLoft has no evidence of it.
                            else 'handled_by_source'
                            if by_source and self.relay.state['enabled']
                            else 'not_established',
                            encoded(
                                dict(
                                    forwarded=forwarded,
                                    live=live,
                                    destination=self.relay.state['destination'],
                                    simulator_receipt='unconfirmed',
                                    simulator_sender='source' if by_source else 'relay',
                                )
                            ),
                            event['receipt_id'],
                        ),
                    )
            except (OSError, sqlite3.Error) as ex:
                self.service.logs.append('Shot saved; delivery audit update failed: ' + str(ex))
            if target and target.data['ended']:
                self.service.backup_after_session()
            return dict(
                accepted=True, duplicate=False, forwarded=forwarded, receipt_id=event['receipt_id']
            )

    def accept_remote(self, address=None):
        """Listen on every interface instead of localhost only (D66, the user's choice 2026-10-13).

        Open Connect has no authentication: anyone who can reach the port can send shots. One-source
        ownership still applies, so a remote source also blocks TraceCapture while it is connected.
        `address` is this PC's network address, shown on the Relay page. Call before start()."""
        self.host = ANY_MACHINE
        self.state.update(remote=True, address=address)

    async def start(self):
        self.server = await asyncio.start_server(self._client, self.host, self.port, limit=262144)
        self.port = self.server.sockets[0].getsockname()[1]
        self.state.update(listening=True, port=self.port)

    async def _client(self, reader, writer):
        from open_connect import Frames, wire, validate_packet

        connection_id = uuid.uuid4().hex
        task = asyncio.current_task()
        self.tasks.add(task)
        # One producer owns live context; an extra connection cannot interleave shots.
        if self.clients:
            writer.write(wire(dict(Code=503, Message='Another shot source is connected')))
            await writer.drain()
            writer.close()
            self.tasks.discard(task)
            return
        self.clients.add(writer)
        self.source = connection_id
        peer = writer.get_extra_info('peername')
        self.state['peer'] = peer[0] if peer else None
        frames = Frames()
        last = -1
        device = None
        try:
            while True:
                data = await asyncio.wait_for(reader.read(8192), 20)
                if not data:
                    break
                for packet in frames.feed(data):
                    try:
                        validate_packet(packet)
                        if device is not None and device != packet['DeviceID']:
                            raise ValueError('DeviceID changed on the same connection.')
                        device = packet['DeviceID']
                        options = packet['ShotDataOptions']
                        self.last_seen = time.monotonic()
                        ready = options.get('LaunchMonitorIsReady', True)
                        self.state['device'] = device
                        self.service.capture.update(
                            running=ready,
                            connected=True,
                            mode='run',
                            status='Source ready' if ready else 'Source connected; not ready',
                            error='',
                        )
                        self.relay.ready = ready
                        self.relay.delegate(source_delivers(packet))
                        if options.get('IsHeartBeat'):
                            # The source's current problems; shots and other packets leave them as is.
                            self.state['alerts'] = source_alerts(packet.get('TraceLoft'))
                        # Standard packets are numbered per connection. Extended durable receipts survive reconnects.
                        if (
                            options['ContainsBallData']
                            and 'TraceLoft' not in packet
                            and packet['ShotNumber'] < last
                        ):
                            raise ValueError(
                                'Stale shot number; reconnect when starting a new shot sequence.'
                            )
                        reply = await self.accept_packet(packet, connection_id)
                        if reply:
                            last = max(last, packet['ShotNumber'])
                        response = dict(
                            Code=200,
                            Message='Stored in TraceLoft' if reply else 'Ready',
                            TraceLoft=dict(Context=self.context(), **(reply or {})),
                        )
                        writer.write(wire(response))
                        if self.relay.state['player']:
                            writer.write(
                                wire(
                                    dict(
                                        Code=201,
                                        Message='Simulator player information',
                                        Player=self.relay.state['player'],
                                    )
                                )
                            )
                    except (ValueError, TypeError, KeyError) as ex:
                        self.state['error'] = str(ex)
                        writer.write(wire(dict(Code=501, Message=str(ex))))
                    except (OSError, sqlite3.Error) as ex:
                        self.service.save_error = 'Shot save failed: ' + str(ex)
                        writer.write(wire(dict(Code=503, Message=self.service.save_error)))
                    await writer.drain()
        except (OSError, ValueError, UnicodeError, asyncio.TimeoutError) as ex:
            self.state['error'] = str(ex)
        finally:
            self.clients.discard(writer)
            self.tasks.discard(task)
            writer.close()
            if self.source == connection_id:
                self.source = None
                self.state['peer'] = None
                self.state['alerts'] = []  # "Waiting for source" covers a missing source
                self.service.capture.update(
                    running=False, connected=False, status='Waiting for shot source'
                )
                self.relay.ready = False
                self.relay.delegate(False)  # the relay serves the next source again

    def tick(self):
        if time.monotonic() - self.last_seen > 15:
            self.service.capture.update(running=False, status='Waiting for shot source')
            self.relay.ready = False

    async def close(self):
        if self.server:
            self.server.close()
        self.state['listening'] = False
        for writer in list(self.clients):
            writer.close()
        if self.tasks:
            _, pending = await asyncio.wait(self.tasks, timeout=2)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        # Python 3.12 waits for client transports too: close them before waiting.
        if self.server:
            await self.server.wait_closed()
        await self.relay.close()
