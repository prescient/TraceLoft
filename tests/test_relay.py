"""Protocol, atomic recording and direct output using isolated SQLite and TCP peers."""
import asyncio
import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from open_connect import Frames, heartbeat, validate_packet, wire
from web_service import GolfService
from web_app import create_app
from fastapi.testclient import TestClient


def shot(number=1):
    return dict(DeviceID='Test monitor', APIversion='1', Units='Yards', ShotNumber=number,
        BallData=dict(Speed=4.2, HLA=-.4, VLA=0, TotalSpin=0, SpinAxis=0),
        ShotDataOptions=dict(ContainsBallData=True, ContainsClubData=False))


class ProtocolTests(unittest.TestCase):
    def test_fragmentation_concatenation_and_utf8(self):
        p=shot();p['DeviceID']='Monitör';data=wire(p)+wire(heartbeat())
        for split in range(len(data)+1):
            frames=Frames()
            self.assertEqual(frames.feed(data[:split])+frames.feed(data[split:]),[p,heartbeat()])

    def test_reject_bad_json_and_unsupported_values(self):
        for data in (b'{"a":1,"a":2}',b'{"a":NaN}',b'[]',b'{'+b' '*262144):
            with self.assertRaises(ValueError):Frames().feed(data)
        for key,value in [('Speed',None),('Speed',True),('VLA',float('nan')),('SpinAxis',None)]:
            p=shot();p['BallData'][key]=value
            with self.assertRaises(ValueError):validate_packet(p)
        p=shot();p['Units']='Meters'
        with self.assertRaises(ValueError):validate_packet(p)

    def test_zero_spin_and_alternate_components(self):
        self.assertEqual(validate_packet(shot())['total_spin'],0)
        p=shot();p['BallData'].pop('TotalSpin');p['BallData'].pop('SpinAxis')
        p['BallData'].update(BackSpin=0,SideSpin=0)
        self.assertEqual(validate_packet(p)['back_spin'],0)

    def test_http_settings_shutdown_and_restart_preserve_session(self):
        with tempfile.TemporaryDirectory() as root:
            service=GolfService(root)
            with TestClient(create_app(service),base_url='http://localhost') as client:
                self.assertEqual(client.post('/api/capture/start',json={}).status_code,404)
                self.assertEqual(client.post('/api/input/forwarding',json=[]).status_code,409)
                self.assertEqual(client.post('/api/input/forwarding',json={'destination':'off'}).status_code,200)
                p=client.post('/api/practice',json={'drill':'Pace consistency'}).json()['practice']
            service=GolfService(root)
            try:
                self.assertEqual(service.load_session(p['id']).data,p)
                saved=service.store.connection.execute("SELECT value FROM metadata WHERE key='active_session.v1'").fetchone()[0]
                service.resume_practice(json.loads(saved))
                self.assertEqual(service.practice.data,p)
            finally:asyncio.run(service.shutdown())


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.service=GolfService(self.temp.name)
        self.service.input.port=0
        await self.service.input.start()
        self.writers=[];self.sim=None

    async def asyncTearDown(self):
        for writer in self.writers:writer.close()
        await self.service.shutdown()
        if self.sim:self.sim.close();await self.sim.wait_closed()
        self.temp.cleanup()

    async def client(self):
        r,w=await asyncio.open_connection('127.0.0.1',self.service.input.port)
        self.writers.append(w)
        return r,w

    async def exchange(self,r,w,p):
        w.write(wire(p));await w.drain()
        frames=Frames()
        while True:
            replies=frames.feed(await asyncio.wait_for(r.read(8192),2))
            if replies:return replies[0]

    async def test_standard_sender_works_without_private_extensions_and_saves_raw(self):
        self.service.create_practice(dict(drill='Pace consistency',target=4,speed_tolerance=.3,angle_tolerance=1,repetitions=10))
        r,w=await self.client();p=shot();p['VendorExtra']={'unknown':123}
        p['ShotDataOptions']['ContainsClubData']=True
        p['ClubData']={'Speed':3,'AngleOfAttack':-2,'VerticalFaceImpact':7}
        response=await self.exchange(r,w,p)
        self.assertEqual(response['Code'],200)
        self.assertEqual(self.service.store.count('shots'),1)
        self.assertEqual(len(self.service.practice.data['shots']),1)
        event=json.loads(self.service.store.connection.execute('SELECT raw_json FROM ingest_events').fetchone()[0])
        self.assertEqual(event['raw_packet'],p)
        self.assertEqual(event['vals']['club_speed'],3)
        self.assertNotIn('impact_vertical',event['vals']) # Undocumented unit retained raw.
        self.assertTrue((await self.exchange(r,w,p))['TraceLoft']['duplicate'])
        self.assertEqual(self.service.store.count('shots'),1)
        p['BallData']['Speed']=5
        self.assertEqual((await self.exchange(r,w,p))['Code'],501)

    async def test_atomic_failure_rolls_back_and_same_shot_can_retry(self):
        self.service.create_practice(dict(drill='Pace consistency',target=4,speed_tolerance=.3,angle_tolerance=1,repetitions=10))
        before=copy.deepcopy(self.service.practice.data)
        r,w=await self.client()
        with patch.object(self.service.practice,'save',side_effect=sqlite3.OperationalError('disk full')):
            response=await self.exchange(r,w,shot())
        self.assertEqual(response['Code'],503)
        self.assertEqual(self.service.store.count('shots'),0)
        self.assertEqual(self.service.practice.data,before)
        self.assertEqual((await self.exchange(r,w,shot()))['Code'],200)
        self.assertEqual(self.service.store.count('shots'),1)

    async def test_durable_identity_and_stale_recording_without_live_scoring(self):
        p=shot();p['TraceLoft']=dict(ReceiptId='stable',ProducerId='sender',StreamId='stream',
            CapturedAt=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat())
        self.service.create_practice(dict(drill='Pace consistency',target=4,speed_tolerance=.3,angle_tolerance=1,repetitions=10))
        p['TraceLoft']['Context']=self.service.input.context()
        response=await self.service.input.accept_packet(p,'first')
        self.assertFalse(response['forwarded'])
        self.assertEqual(len(self.service.practice.data['shots']),0)
        self.assertTrue((await self.service.input.accept_packet(p,'second'))['duplicate'])
        self.assertEqual(self.service.store.count('shots'),1)

    async def test_single_source_ownership(self):
        r,w=await self.client();await self.exchange(r,w,heartbeat())
        r2,w2=await self.client()
        self.assertEqual(Frames().feed(await asyncio.wait_for(r2.read(8192),2))[0]['Code'],503)

    async def test_shutdown_closes_a_connected_source_without_waiting_for_it(self):
        r,w=await self.client();await self.exchange(r,w,heartbeat())
        await asyncio.wait_for(self.service.input.close(),2)
        self.assertEqual(await asyncio.wait_for(r.read(1),1),b'')

    async def test_direct_output_optional_no_adapter_no_replay(self):
        received=[];arrived=asyncio.Event()
        async def simulator(reader,writer):
            self.writers.append(writer);frames=Frames()
            try:
                while data:=await reader.read(8192):
                    for p in frames.feed(data):
                        received.append(p)
                        writer.write(wire(dict(Code=200,Message='OK')))
                        await writer.drain();arrived.set()
            except OSError:pass
        self.sim=await asyncio.start_server(simulator,'127.0.0.1',0)
        port=self.sim.sockets[0].getsockname()[1]
        await self.service.input.relay.configure(dict(destination='infinite_tees',port=port),self.service.input.port)
        await asyncio.wait_for(arrived.wait(),2);arrived.clear()
        p=shot();p['VendorExtra']='local only'
        self.assertTrue((await self.service.input.accept_packet(p,'sender'))['forwarded'])
        await asyncio.wait_for(arrived.wait(),2)
        outgoing=[x for x in received if x['ShotDataOptions']['ContainsBallData']]
        self.assertEqual(len(outgoing),1);self.assertNotIn('VendorExtra',outgoing[0])
        await self.service.input.relay.configure(dict(destination='off'),self.service.input.port)
        self.assertFalse((await self.service.input.accept_packet(shot(2),'sender'))['forwarded'])
        arrived.clear()
        await self.service.input.relay.configure(dict(destination='gspro',port=port),self.service.input.port)
        await asyncio.wait_for(arrived.wait(),2)
        self.assertEqual(len([x for x in received if x['ShotDataOptions']['ContainsBallData']]),1)
        self.assertEqual(self.service.store.count('shots'),2)


if __name__=='__main__':unittest.main()
