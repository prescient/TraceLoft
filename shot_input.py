"""Versioned source-neutral shot input and optional live-only simulator output."""
import asyncio
import copy
import json
import math
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from storage import encoded, digest, now

FIELDS = {'ball_speed': (0, 250), 'launch_ang': (-90, 90), 'launch_dir': (-90, 90),
          'back_spin': (-50000, 50000), 'side_spin': (-50000, 50000), 'total_spin': (0, 50000),
          'spin_axis': (-180, 180), 'carry': (0, 1000), 'total': (0, 1000), 'offline': (-1000, 1000),
          'peak_height': (0, 1000), 'descent_ang': (-90, 90), 'curve': (-1000, 1000), 'hang_time': (0, 60)}
FIELDS.update({key: (-10000,10000) for key in ('club_speed','attack_angle','face_angle','dynamic_lie','dynamic_loft','club_path','closure_rate','impact_vertical','impact_horizontal')})
BALL = {'Speed': 'ball_speed', 'VLA': 'launch_ang', 'HLA': 'launch_dir', 'BackSpin': 'back_spin',
        'SideSpin': 'side_spin', 'TotalSpin': 'total_spin', 'SpinAxis': 'spin_axis', 'CarryDistance': 'carry'}


def validate(envelope):
    if not isinstance(envelope, dict) or envelope.get('schema') != 'traceloft.shot.v1':
        raise ValueError('Expected traceloft.shot.v1.')
    if len(encoded(envelope).encode()) > 262144:
        raise ValueError('Shot envelope exceeds 256 KiB.')
    event = copy.deepcopy(envelope.get('event'))
    if not isinstance(event, dict): raise ValueError('A shot event is required.')
    for key in ('receipt_id', 'producer_id', 'session_id'):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', str(event.get(key, ''))):
            raise ValueError('Invalid ' + key)
    if type(event.get('seq')) is not int or event['seq'] < 0: raise ValueError('Invalid shot sequence.')
    if event.get('simulated'): raise ValueError('Synthetic events use the explicit demo controls.')
    try:
        captured = datetime.fromisoformat(event['captured_at'])
        if captured.tzinfo is None: raise ValueError()
        age = (datetime.now(timezone.utc) - captured).total_seconds()
        if age < -5: raise ValueError()
    except (KeyError, TypeError, ValueError): raise ValueError('Invalid timezone-aware capture time.') from None
    if event.get('result') not in ('validated', 'failed', 'logged'): raise ValueError('Invalid acquisition result.')
    vals = event.get('vals')
    if not isinstance(vals, dict): raise ValueError('Metrics are required.')
    for key, value in vals.items():
        if key == 'fs_shot': continue  # Legacy source label, never a measurement mapping.
        if key not in FIELDS: raise ValueError('Unsupported metric: ' + key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or
                                 not math.isfinite(value) or not FIELDS[key][0] <= value <= FIELDS[key][1]):
            raise ValueError('Invalid metric: ' + key)
    if event['result'] == 'validated' and any(vals.get(k) is None for k in ('ball_speed','launch_ang','launch_dir')):
        raise ValueError('Accepted shots require ball speed and launch angles.')
    if not isinstance(event.get('source_configuration'), dict): raise ValueError('Source provenance is required.')
    for key in ('equipment_selection', 'range_context', 'collection_context', 'game_context'):
        if event.get(key) is not None and not isinstance(event[key], dict): raise ValueError('Invalid ' + key)
    sid = event.get('practice_session_id')
    if sid is not None and not re.fullmatch('[a-f0-9]{32}', str(sid)): raise ValueError('Invalid practice identity.')
    event.update(kind='record', wire_digest=digest(encoded(event).encode()), mapping_id='traceloft.normalized.v1')
    return event, age <= 15 and not envelope.get('recovered', False)


class Relay:
    """Direct optional simulator output. A reconnect never replays a stored shot."""
    def __init__(self):
        self.writer=None; self.task=None; self.number=0; self.ready=False
        self.state=dict(destination='off',enabled=False,host='127.0.0.1',port=921,connected=False,
            status='Forwarding off',last_response=None,player={},sent=0)
        self.lock=asyncio.Lock()

    async def configure(self,settings,input_port):
        destination=settings.get('destination','off')
        if destination not in ('off','gspro','infinite_tees'):raise ValueError('Select Off, GSPro or Infinite Tees.')
        host=settings.get('host','127.0.0.1')
        if host not in ('localhost','127.0.0.1','::1'):raise ValueError('Use a localhost simulator address.')
        port=settings.get('port',999 if destination=='infinite_tees' else 921)
        if type(port) is not int or not 1<=port<=65535 or port==input_port:raise ValueError('Simulator port must differ from input port.')
        await self.close()
        self.state.update(destination=destination,enabled=destination!='off',host=host,port=port,last_response=None,player={})
        if self.state['enabled']:self.task=asyncio.create_task(self._connect())

    async def _connect(self):
        from open_connect import Frames,heartbeat
        while self.state['enabled']:
            writer=None
            try:
                reader,writer=await asyncio.wait_for(asyncio.open_connection(self.state['host'],self.state['port']),2)
                self.writer=writer;self.state.update(connected=True,status='Connected; waiting for simulator response')
                await self.send(heartbeat(self.ready,self.number))
                frames=Frames()
                while True:
                    try:data=await asyncio.wait_for(reader.read(8192),5)
                    except asyncio.TimeoutError:
                        if not await self.send(heartbeat(self.ready,self.number)):raise ConnectionError('Heartbeat write failed')
                        continue
                    if not data:raise ConnectionError('Simulator disconnected')
                    for reply in frames.feed(data):
                        if type(reply.get('Code')) is not int:raise ValueError('Invalid simulator response')
                        self.state['last_response']=reply
                        if reply['Code']==201:self.state['player']=reply.get('Player',{})
                        self.state['status']='Simulator protocol acknowledged' if reply['Code'] in (200,201) else str(reply.get('Message','Simulator error'))[:200]
            except asyncio.CancelledError:raise
            except (OSError,ValueError,UnicodeError,asyncio.TimeoutError) as ex:
                self.state['status']='Disconnected: '+str(ex)
            finally:
                if writer:writer.close()
                self.writer=None;self.state['connected']=False;self.state['player']={}
            await asyncio.sleep(2)

    async def send(self,payload):
        from open_connect import wire
        async with self.lock:
            writer=self.writer
            if not writer:return False
            try:
                writer.write(wire(payload));await asyncio.wait_for(writer.drain(),1)
                return True
            except (OSError,asyncio.TimeoutError):writer.close();return False

    async def close(self):
        self.state['enabled']=False
        if self.task:
            self.task.cancel()
            try:await self.task
            except asyncio.CancelledError:pass
        self.task=None
        if self.writer:self.writer.close()
        self.writer=None;self.state.update(connected=False,status='Forwarding off',player={})


class ShotInput:
    def __init__(self,service,port=900):
        self.service,self.port=service,port
        self.server=None;self.relay=Relay();self.last_seen=0;self.source=None
        self.clients=set();self.tasks=set();self.accept_lock=asyncio.Lock()
        self.state=dict(listening=False,port=port,device=None,received=0,duplicates=0,last_shot=None,error='')

    def context(self):return copy.deepcopy(self.service.input_context)

    async def accept_packet(self,packet,connection_id):
        from open_connect import validate_packet,simulator_packet
        vals=validate_packet(packet)
        options=packet['ShotDataOptions'];extension=packet.get('TraceLoft',{})
        if not isinstance(extension,dict):raise ValueError('TraceLoft extension must be an object.')
        result=extension.get('Result','validated')
        if result not in ('validated','failed','logged'):raise ValueError('Invalid acquisition result.')
        if not vals and result=='validated':return None
        if vals and result!='validated':raise ValueError('Failed acquisition must not claim ball data.')
        seq=packet['ShotNumber']
        context=extension.get('Context',self.context())
        if not isinstance(context,dict):raise ValueError('Invalid shot context.')
        metrics=extension.get('Metrics',{})
        if not isinstance(metrics,dict):raise ValueError('Invalid extension metrics.')
        for key,value in metrics.items():
            if key in vals and vals[key]!=value:raise ValueError('Extension contradicts BallData: '+key)
        vals.update(metrics)
        event=dict(kind='record',receipt_id=extension.get('ReceiptId',uuid.uuid5(uuid.NAMESPACE_URL,connection_id+':'+str(seq)).hex),
            producer_id=extension.get('ProducerId',connection_id),session_id=extension.get('StreamId',connection_id),
            seq=seq,captured_at=extension.get('CapturedAt',now()),result=result,vals=vals,
            source_configuration=extension.get('Source',dict(acquisition='open_connect',device=packet['DeviceID'])),
            raw_packet=copy.deepcopy(packet),**{k:context.get(k) for k in
                ('practice_session_id','equipment_selection','range_context','collection_context','game_context')})
        event,live=validate(dict(schema='traceloft.shot.v1',event=event,recovered=extension.get('Recovered',False)))
        event['wire_digest']=digest(encoded(packet).encode())
        async with self.accept_lock:
            store=self.service.store
            old=store.connection.execute('SELECT raw_json FROM ingest_events WHERE id=?',(event['receipt_id'],)).fetchone()
            if old:
                if json.loads(old[0]).get('wire_digest')!=event['wire_digest']:raise ValueError('Receipt identity conflicts with different data.')
                self.state['duplicates']+=1
                return dict(accepted=True,duplicate=True,forwarded=False,receipt_id=event['receipt_id'])
            target=self.service.practice
            if not live or not target or target.data['id']!=event.get('practice_session_id') or target.data['ended']:target=None
            previous=copy.deepcopy(target.data) if target else None
            try:
                with store.transaction():
                    store.ingest(event,provenance='open_connect')
                    if target:target.add(event)
            except Exception:
                if target:target.data=previous
                raise
            self.service.history.appendleft(event);self.service.latest_read=event
            self.service.sessions_revision+=1;self.service.publish_context();self.service.save_error=''
            self.state.update(received=self.state['received']+1,last_shot=event['captured_at'],error='')
            forwarded=False
            if live and result=='validated' and self.relay.state['enabled']:
                self.relay.number+=1
                forwarded=await self.relay.send(simulator_packet(packet,self.relay.number))
                if forwarded:self.relay.state['sent']+=1
            try:
                with store.transaction():
                    store.connection.execute('UPDATE delivery_events SET status=?,evidence_json=? WHERE event_id=?',
                        ('socket_write_reported_unacknowledged' if forwarded else 'not_established',
                         encoded(dict(forwarded=forwarded,live=live,destination=self.relay.state['destination'],simulator_receipt='unconfirmed')),event['receipt_id']))
            except (OSError,sqlite3.Error) as ex:self.service.logs.append('Shot saved; delivery audit update failed: '+str(ex))
            if target and target.data['ended']:self.service.backup_after_session()
            return dict(accepted=True,duplicate=False,forwarded=forwarded,receipt_id=event['receipt_id'])

    async def start(self):
        self.server=await asyncio.start_server(self._client,'127.0.0.1',self.port,limit=262144)
        self.port=self.server.sockets[0].getsockname()[1];self.state.update(listening=True,port=self.port)

    async def _client(self,reader,writer):
        from open_connect import Frames,wire,validate_packet
        connection_id=uuid.uuid4().hex;task=asyncio.current_task();self.tasks.add(task)
        # One producer owns live context; an extra connection cannot interleave shots.
        if self.clients:
            writer.write(wire(dict(Code=503,Message='Another shot source is connected')))
            await writer.drain();writer.close();self.tasks.discard(task);return
        self.clients.add(writer);self.source=connection_id;frames=Frames();last=-1;device=None
        try:
            while True:
                data=await asyncio.wait_for(reader.read(8192),20)
                if not data:break
                for packet in frames.feed(data):
                    try:
                        validate_packet(packet)
                        if device is not None and device!=packet['DeviceID']:raise ValueError('DeviceID changed on the same connection.')
                        device=packet['DeviceID'];options=packet['ShotDataOptions'];self.last_seen=time.monotonic()
                        ready=options.get('LaunchMonitorIsReady',True)
                        self.state['device']=device
                        self.service.capture.update(running=ready,connected=True,mode='run',status='Source ready' if ready else 'Source connected; not ready',error='')
                        self.relay.ready=ready
                        # Standard packets are numbered per connection. Extended durable receipts survive reconnects.
                        if options['ContainsBallData'] and 'TraceLoft' not in packet and packet['ShotNumber']<last:
                            raise ValueError('Stale shot number; reconnect when starting a new shot sequence.')
                        reply=await self.accept_packet(packet,connection_id)
                        if reply:last=max(last,packet['ShotNumber'])
                        response=dict(Code=200,Message='Stored in TraceLoft' if reply else 'Ready',
                            TraceLoft=dict(Context=self.context(),**(reply or {})))
                        writer.write(wire(response))
                        if self.relay.state['player']:writer.write(wire(dict(Code=201,Message='Simulator player information',Player=self.relay.state['player'])))
                    except (ValueError,TypeError,KeyError) as ex:
                        self.state['error']=str(ex);writer.write(wire(dict(Code=501,Message=str(ex))))
                    except (OSError,sqlite3.Error) as ex:
                        self.service.save_error='Shot save failed: '+str(ex)
                        writer.write(wire(dict(Code=503,Message=self.service.save_error)))
                    await writer.drain()
        except (OSError,ValueError,UnicodeError,asyncio.TimeoutError) as ex:
            self.state['error']=str(ex)
        finally:
            self.clients.discard(writer);self.tasks.discard(task);writer.close()
            if self.source==connection_id:
                self.source=None;self.service.capture.update(running=False,connected=False,status='Waiting for shot source');self.relay.ready=False

    def tick(self):
        if time.monotonic()-self.last_seen>15:
            self.service.capture.update(running=False,status='Waiting for shot source');self.relay.ready=False

    async def close(self):
        if self.server:self.server.close();await self.server.wait_closed()
        self.state['listening']=False
        for writer in list(self.clients):writer.close()
        if self.tasks:
            _,pending=await asyncio.wait(self.tasks,timeout=2)
            for task in pending:task.cancel()
            if pending:await asyncio.gather(*pending,return_exceptions=True)
        await self.relay.close()
