"""Protocol, atomic recording and direct output using isolated SQLite and TCP peers."""

import asyncio
import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from open_connect import Frames, heartbeat, simulator_packet, validate_packet, wire
from web_service import GolfService
from web_app import create_app
from fastapi.testclient import TestClient


def shot(number=1):
    return dict(
        DeviceID='Test monitor',
        APIversion='1',
        Units='Yards',
        ShotNumber=number,
        BallData=dict(Speed=4.2, HLA=-0.4, VLA=0, TotalSpin=0, SpinAxis=0),
        ShotDataOptions=dict(ContainsBallData=True, ContainsClubData=False),
    )


class ProtocolTests(unittest.TestCase):
    def test_fragmentation_concatenation_and_utf8(self):
        p = shot()
        p['DeviceID'] = 'Monitör'
        data = wire(p) + wire(heartbeat())
        for split in range(len(data) + 1):
            frames = Frames()
            self.assertEqual(
                frames.feed(data[:split]) + frames.feed(data[split:]), [p, heartbeat()]
            )

    def test_reject_bad_json_and_unsupported_values(self):
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}', b'[]', b'{' + b' ' * 262144):
            with self.assertRaises(ValueError):
                Frames().feed(data)
        for key, value in [
            ('Speed', None),
            ('Speed', True),
            ('VLA', float('nan')),
            ('SpinAxis', None),
        ]:
            p = shot()
            p['BallData'][key] = value
            with self.assertRaises(ValueError):
                validate_packet(p)
        p = shot()
        p['Units'] = 'Meters'
        with self.assertRaises(ValueError):
            validate_packet(p)

    def test_zero_spin_and_alternate_components(self):
        self.assertEqual(validate_packet(shot())['total_spin'], 0)
        p = shot()
        p['BallData'].pop('TotalSpin')
        p['BallData'].pop('SpinAxis')
        p['BallData'].update(BackSpin=0, SideSpin=0)
        self.assertEqual(validate_packet(p)['back_spin'], 0)

    def test_declared_spin_unavailable_shot_needs_no_spin_and_plays_as_zero(self):
        p = shot()
        for key in ('TotalSpin', 'SpinAxis'):
            p['BallData'].pop(key)
        with self.assertRaises(ValueError):
            validate_packet(p)  # undeclared missing spin stays an error
        p['TraceLoft'] = dict(SpinUnavailable=True)
        vals = validate_packet(p)
        self.assertNotIn('total_spin', vals)
        outgoing = simulator_packet(p, 7)['BallData']
        self.assertEqual(
            [outgoing[k] for k in ('TotalSpin', 'SpinAxis', 'BackSpin', 'SideSpin')], [0] * 4
        )
        self.assertNotIn('TraceLoft', simulator_packet(p, 7))
        p['BallData']['BackSpin'] = 0
        with self.assertRaises(ValueError):
            validate_packet(p)  # a declared spinless shot must not also carry spin
        p['BallData'].pop('BackSpin')
        p['TraceLoft']['SpinUnavailable'] = 'yes'
        with self.assertRaises(ValueError):
            validate_packet(p)  # only literal true counts
        self.assertEqual(
            simulator_packet(shot(), 1)['BallData']['TotalSpin'], 0
        )  # measured zero kept

    def test_http_settings_shutdown_and_restart_preserve_session(self):
        with tempfile.TemporaryDirectory() as root:
            service = GolfService(root)
            with TestClient(create_app(service), base_url='http://localhost') as client:
                self.assertEqual(client.post('/api/capture/start', json={}).status_code, 404)
                self.assertEqual(client.post('/api/input/forwarding', json=[]).status_code, 409)
                self.assertEqual(
                    client.post('/api/input/forwarding', json={'destination': 'off'}).status_code,
                    200,
                )
                p = client.post('/api/practice', json={'drill': 'Pace consistency'}).json()[
                    'practice'
                ]
            service = GolfService(root)
            try:
                self.assertEqual(service.load_session(p['id']).data, p)
                saved = service.store.connection.execute(
                    "SELECT value FROM metadata WHERE key='active_session.v1'"
                ).fetchone()[0]
                service.resume_practice(json.loads(saved))
                self.assertEqual(service.practice.data, p)
            finally:
                asyncio.run(service.shutdown())


class SimulatorAddressTests(unittest.IsolatedAsyncioTestCase):
    """D69: the simulator may be this PC or another PC on the private network, never the internet."""

    async def test_private_network_address_is_accepted_and_kept(self):
        from shot_input import Relay

        relay = Relay()
        relay._connect = lambda: asyncio.sleep(0)  # no dialling in this test
        await relay.configure(dict(destination='gspro', host='10.10.0.190', port=921), 900)
        self.assertEqual((relay.state['host'], relay.state['port']), ('10.10.0.190', 921))
        await relay.close()

    async def test_names_and_public_addresses_are_refused(self):
        from shot_input import Relay, simulator_host

        for host in ('gspro.example.com', '8.8.8.8', '0.0.0.0', '', None, 921):
            with self.assertRaisesRegex(ValueError, 'network address'):
                simulator_host(host)
        self.assertEqual(simulator_host('192.168.1.20'), '192.168.1.20')
        relay = Relay()
        with self.assertRaises(ValueError):
            await relay.configure(dict(destination='gspro', host='8.8.8.8'), 900)

    async def test_input_port_conflict_applies_only_on_this_pc(self):
        from shot_input import Relay

        relay = Relay()
        relay._connect = lambda: asyncio.sleep(0)
        with self.assertRaisesRegex(ValueError, 'differ from input'):
            await relay.configure(dict(destination='gspro', host='127.0.0.1', port=921), 921)
        await relay.configure(dict(destination='gspro', host='10.10.0.190', port=921), 921)
        await relay.close()


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.service.input.port = 0
        await self.service.input.start()
        self.writers = []
        self.sim = None

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close()
        await self.service.shutdown()
        if self.sim:
            self.sim.close()
            await self.sim.wait_closed()
        self.temp.cleanup()

    async def client(self):
        r, w = await asyncio.open_connection('127.0.0.1', self.service.input.port)
        self.writers.append(w)
        return r, w

    async def exchange(self, r, w, p):
        w.write(wire(p))
        await w.drain()
        frames = Frames()
        while True:
            replies = frames.feed(await asyncio.wait_for(r.read(8192), 2))
            if replies:
                return replies[0]

    async def test_standard_sender_works_without_private_extensions_and_saves_raw(self):
        self.service.create_practice(
            dict(
                drill='Pace consistency',
                target=4,
                speed_tolerance=0.3,
                angle_tolerance=1,
                repetitions=10,
            )
        )
        r, w = await self.client()
        p = shot()
        p['VendorExtra'] = {'unknown': 123}
        p['ShotDataOptions']['ContainsClubData'] = True
        p['ClubData'] = {'Speed': 3, 'AngleOfAttack': -2, 'VerticalFaceImpact': 7}
        response = await self.exchange(r, w, p)
        self.assertEqual(response['Code'], 200)
        self.assertEqual(self.service.store.count('shots'), 1)
        self.assertEqual(len(self.service.practice.data['shots']), 1)
        event = json.loads(
            self.service.store.connection.execute('SELECT raw_json FROM ingest_events').fetchone()[
                0
            ]
        )
        self.assertEqual(event['raw_packet'], p)
        self.assertEqual(event['vals']['club_speed'], 3)
        self.assertNotIn('impact_vertical', event['vals'])  # Undocumented unit retained raw.
        self.assertTrue((await self.exchange(r, w, p))['TraceLoft']['duplicate'])
        self.assertEqual(self.service.store.count('shots'), 1)
        p['BallData']['Speed'] = 5
        self.assertEqual((await self.exchange(r, w, p))['Code'], 501)

    async def test_atomic_failure_rolls_back_and_same_shot_can_retry(self):
        self.service.create_practice(
            dict(
                drill='Pace consistency',
                target=4,
                speed_tolerance=0.3,
                angle_tolerance=1,
                repetitions=10,
            )
        )
        before = copy.deepcopy(self.service.practice.data)
        r, w = await self.client()
        with patch.object(
            self.service.practice, 'save', side_effect=sqlite3.OperationalError('disk full')
        ):
            response = await self.exchange(r, w, shot())
        self.assertEqual(response['Code'], 503)
        self.assertEqual(self.service.store.count('shots'), 0)
        self.assertEqual(self.service.practice.data, before)
        self.assertEqual((await self.exchange(r, w, shot()))['Code'], 200)
        self.assertEqual(self.service.store.count('shots'), 1)

    async def test_durable_identity_and_stale_recording_without_live_scoring(self):
        p = shot()
        p['TraceLoft'] = dict(
            ReceiptId='stable',
            ProducerId='sender',
            StreamId='stream',
            CapturedAt=(datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        )
        self.service.create_practice(
            dict(
                drill='Pace consistency',
                target=4,
                speed_tolerance=0.3,
                angle_tolerance=1,
                repetitions=10,
            )
        )
        p['TraceLoft']['Context'] = self.service.input.context()
        response = await self.service.input.accept_packet(p, 'first')
        self.assertFalse(response['forwarded'])
        self.assertEqual(len(self.service.practice.data['shots']), 0)
        self.assertTrue((await self.service.input.accept_packet(p, 'second'))['duplicate'])
        self.assertEqual(self.service.store.count('shots'), 1)

    async def test_spinless_memory_putt_is_stored_with_null_spin(self):
        p = shot()
        p['BallData'] = dict(Speed=4.3, HLA=-1.2, VLA=0.0)
        spin = dict.fromkeys(('back_spin', 'side_spin', 'total_spin', 'spin_axis'))
        p['TraceLoft'] = dict(
            ReceiptId='putt1',
            ProducerId='capture',
            StreamId='premier-20261011-130000',
            CapturedAt=datetime.now(timezone.utc).isoformat(),
            SpinUnavailable=True,
            Metrics=dict(ball_speed=4.3, launch_dir=-1.2, launch_ang=0.0, club_speed=4.6, **spin),
            Source=dict(acquisition='premier_memory'),
        )
        r, w = await self.client()
        response = await self.exchange(r, w, p)
        self.assertEqual(response['Code'], 200, response)
        event = json.loads(
            self.service.store.connection.execute('SELECT raw_json FROM ingest_events').fetchone()[
                0
            ]
        )
        self.assertEqual({k: event['vals'][k] for k in spin}, spin)  # null, never zero
        self.assertEqual(event['vals']['club_speed'], 4.6)
        self.assertTrue(event['raw_packet']['TraceLoft']['SpinUnavailable'])

    async def test_ipad_table_import_becomes_its_own_finished_range_session(self):
        """D65: imported shots never join the active drill or the simulator, keep the chosen club, and
        are flagged when a live capture already has the same shot."""
        bag = self.service.equipment['bags'][0]
        club = bag['clubs'][0]
        active = self.service.create_practice(dict(drill='Driving range'))
        catalog = self.service.input.context()['equipment_catalog']
        self.assertEqual(catalog[0]['clubs'][0]['club_id'], club['id'])
        live = shot(1)
        live['BallData'] = dict(Speed=120.0, VLA=18.0, HLA=2.0, TotalSpin=5000, SpinAxis=8.0)
        await self.service.input.accept_packet(live, 'live')  # a live capture of table row 2
        batch = 'b' * 32
        rows = [(110.0, 19.0, -1.0), (120.0, 18.0, 2.0), (130.0, 15.0, 0.5)]
        order = [3, 1, 2]  # delivery order is not guaranteed: the last index arrives first
        for index, (speed, vla, hla) in sorted(enumerate(rows, 1), key=lambda r: order.index(r[0])):
            p = shot(index)
            p['BallData'] = dict(Speed=speed, VLA=vla, HLA=hla, TotalSpin=5000, SpinAxis=8.0)
            p['TraceLoft'] = dict(
                ReceiptId=f'import-{index}',
                ProducerId='import',
                StreamId='import-test',
                CapturedAt=datetime.now(timezone.utc).isoformat(),
                Context=dict(practice_session_id=active['id']),  # must be ignored
                Import=dict(
                    BatchId=batch,
                    Index=index,
                    Count=len(rows),
                    BagId=bag['id'],
                    ClubId=club['id'],
                    Label='iPad import',
                ),
            )
            reply = await self.service.input.accept_packet(p, 'importer')
            self.assertFalse(reply['forwarded'])
        imported = self.service.load_session(batch).data
        self.assertEqual(len(imported['shots']), 3)
        self.assertIsNotNone(imported['ended'])  # finished once all three indexes arrived
        self.assertEqual(imported['import_source']['received'], [1, 2, 3])
        self.assertEqual(imported['import_source']['kind'], 'ipad_table')
        self.assertEqual({s['club_label'] for s in imported['shots']}, {club['label']})
        flagged = {
            s['vals']['ball_speed']: s.get('possible_duplicate') is not None
            for s in imported['shots']
        }
        self.assertEqual(flagged, {110.0: False, 120.0: True, 130.0: False})
        self.assertEqual(self.service.practice.data['id'], active['id'])
        self.assertEqual(len(self.service.practice.data['shots']), 1)  # only the live shot
        with self.assertRaises(ValueError):
            bad = shot(9)
            bad['TraceLoft'] = dict(Import=dict(BatchId='nothex', Index=1, Count=1))
            await self.service.input.accept_packet(bad, 'importer')

    async def test_single_source_ownership(self):
        r, w = await self.client()
        await self.exchange(r, w, heartbeat())
        r2, w2 = await self.client()
        self.assertEqual(Frames().feed(await asyncio.wait_for(r2.read(8192), 2))[0]['Code'], 503)

    async def test_input_listens_on_localhost_unless_remote_input_is_enabled(self):
        # Default: loopback only, and the connected source's address is recorded.
        self.assertEqual(self.service.input.server.sockets[0].getsockname()[0], '127.0.0.1')
        self.assertFalse(self.service.input.state['remote'])
        r, w = await self.client()
        await self.exchange(r, w, heartbeat())
        self.assertEqual(self.service.input.state['peer'], '127.0.0.1')
        w.close()
        await asyncio.sleep(0.1)
        self.assertIsNone(self.service.input.state['peer'])
        # D66: remote input binds every interface; one-source ownership still applies.
        folder = tempfile.TemporaryDirectory()
        remote = GolfService(folder.name)
        try:
            remote.input.port = 0
            remote.input.accept_remote('192.0.2.10')
            await remote.input.start()
            self.assertEqual(remote.input.server.sockets[0].getsockname()[0], '0.0.0.0')
            self.assertEqual(
                (remote.input.state['remote'], remote.input.state['address']), (True, '192.0.2.10')
            )
            r, w = await asyncio.open_connection('127.0.0.1', remote.input.port)
            self.writers.append(w)
            await self.exchange(r, w, heartbeat())
            r2, w2 = await asyncio.open_connection('127.0.0.1', remote.input.port)
            self.writers.append(w2)
            self.assertEqual(
                Frames().feed(await asyncio.wait_for(r2.read(8192), 2))[0]['Code'], 503
            )
        finally:
            for writer in self.writers[-2:]:
                writer.close()
            await remote.shutdown()
            folder.cleanup()

    async def test_shutdown_closes_a_connected_source_without_waiting_for_it(self):
        r, w = await self.client()
        await self.exchange(r, w, heartbeat())
        await asyncio.wait_for(self.service.input.close(), 2)
        self.assertEqual(await asyncio.wait_for(r.read(1), 1), b'')

    async def test_direct_output_optional_no_adapter_no_replay(self):
        received = []
        arrived = asyncio.Event()

        async def simulator(reader, writer):
            self.writers.append(writer)
            frames = Frames()
            try:
                while data := await reader.read(8192):
                    for p in frames.feed(data):
                        received.append(p)
                        writer.write(wire(dict(Code=200, Message='OK')))
                        await writer.drain()
                        arrived.set()
            except OSError:
                pass

        self.sim = await asyncio.start_server(simulator, '127.0.0.1', 0)
        port = self.sim.sockets[0].getsockname()[1]
        await self.service.input.relay.configure(
            dict(destination='infinite_tees', port=port), self.service.input.port
        )
        await asyncio.wait_for(arrived.wait(), 2)
        arrived.clear()
        p = shot()
        p['VendorExtra'] = 'local only'
        self.assertTrue((await self.service.input.accept_packet(p, 'sender'))['forwarded'])
        await asyncio.wait_for(arrived.wait(), 2)
        outgoing = [x for x in received if x['ShotDataOptions']['ContainsBallData']]
        self.assertEqual(len(outgoing), 1)
        self.assertNotIn('VendorExtra', outgoing[0])
        await self.service.input.relay.configure(dict(destination='off'), self.service.input.port)
        self.assertFalse((await self.service.input.accept_packet(shot(2), 'sender'))['forwarded'])
        arrived.clear()
        await self.service.input.relay.configure(
            dict(destination='gspro', port=port), self.service.input.port
        )
        await asyncio.wait_for(arrived.wait(), 2)
        self.assertEqual(len([x for x in received if x['ShotDataOptions']['ContainsBallData']]), 1)
        self.assertEqual(self.service.store.count('shots'), 2)

    async def test_source_that_delivers_to_the_simulator_takes_over_from_the_relay(self):
        connections = []
        received = []

        async def simulator(reader, writer):
            connections.append(writer)
            self.writers.append(writer)
            frames = Frames()
            try:
                while data := await reader.read(8192):
                    received.extend(frames.feed(data))
                    writer.write(wire(dict(Code=200, Message='OK')))
                    await writer.drain()
            except OSError:
                pass

        self.sim = await asyncio.start_server(simulator, '127.0.0.1', 0)
        port = self.sim.sockets[0].getsockname()[1]
        relay = self.service.input.relay
        await relay.configure(dict(destination='gspro', port=port), self.service.input.port)
        for _ in range(40):
            if relay.state['connected']:
                break
            await asyncio.sleep(0.05)
        self.assertTrue(relay.state['connected'])
        context = self.service.input.context()['simulator']
        self.assertEqual(context, dict(destination='gspro', host='127.0.0.1', port=port))

        beat = heartbeat(True)
        beat['DeviceID'] = 'TraceCapture'
        beat['TraceLoft'] = dict(SimulatorDelivery='source')
        r, w = await self.client()
        reply = await self.exchange(r, w, beat)
        self.assertEqual(reply['TraceLoft']['Context']['simulator']['destination'], 'gspro')
        for _ in range(40):
            if not relay.state['connected']:
                break
            await asyncio.sleep(0.05)
        self.assertFalse(relay.state['connected'])  # the simulator is free for the source
        self.assertTrue(relay.state['delegated'])

        p = shot()
        p['DeviceID'] = 'TraceCapture'
        p['TraceLoft'] = dict(
            ReceiptId='r1', ProducerId='tc', StreamId='s', SimulatorDelivery='source'
        )
        p['TraceLoft']['CapturedAt'] = datetime.now(timezone.utc).isoformat()
        response = await self.exchange(r, w, p)
        self.assertFalse(response['TraceLoft']['forwarded'])
        status, evidence = self.service.store.connection.execute(
            'SELECT status, evidence_json FROM delivery_events'
        ).fetchone()
        self.assertEqual(status, 'handled_by_source')
        self.assertEqual(json.loads(evidence)['simulator_sender'], 'source')
        self.assertFalse([x for x in received if x['ShotDataOptions']['ContainsBallData']])

        w.close()  # the source disconnects: the relay serves the next source again
        for _ in range(80):
            if relay.state['connected']:
                break
            await asyncio.sleep(0.05)
        self.assertFalse(relay.state['delegated'])
        self.assertTrue(relay.state['connected'])
        self.assertGreaterEqual(len(connections), 2)

    async def test_live_view_estimates_flight_only_without_reported_carry(self):
        swing = shot()
        swing['BallData'] = dict(Speed=120.0, VLA=14.0, HLA=1.0, TotalSpin=3000, SpinAxis=2.0)
        await self.service.input.accept_packet(swing, 'sender')
        estimate = self.service.latest_read.get('estimate')
        if estimate is None:  # OpenGolfCoach not installed in this environment
            self.skipTest('OpenGolfCoach unavailable')
        self.assertGreater(estimate['carry'], 100)
        self.assertNotIn('carry', self.service.latest_read['vals'])  # measurements unchanged
        reported = shot(2)
        reported['BallData'] = dict(swing['BallData'], CarryDistance=150.0)
        await self.service.input.accept_packet(reported, 'sender')
        self.assertNotIn('estimate', self.service.latest_read)
        await self.service.input.accept_packet(shot(3), 'sender')  # a putt: zero spin and launch
        self.assertNotIn('estimate', self.service.latest_read)


if __name__ == '__main__':
    unittest.main()
