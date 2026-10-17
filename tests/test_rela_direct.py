"""rēlā straight into TraceLoft (D74): the input profile, the GSPro acknowledgement trail and alerts."""

import asyncio
import copy
import tempfile
import unittest
from unittest.mock import patch

import source_profiles
from open_connect import Frames, validate_packet, wire
from web_service import GolfService

# rēlā's packet for an LPi chip, 2026-10-16 (rela.log). Its own log read face=n/a lie=n/a loft=n/a.
CHIP = dict(
    DeviceID='DESKTOP-00UC2B2', Units='Yards', ShotNumber=17, APIversion='1',
    BallData=dict(Speed=10.32, SpinAxis=3.08, TotalSpin=1134.64, BackSpin=1133, SideSpin=61, HLA=-5.66,
                  VLA=26.12, CarryDistance=1.9),
    ClubData=dict(Speed=10.90, AngleOfAttack=-5.06, FaceToTarget=-13.50, Lie=1.36, Loft=17.18, Path=-14.95,
                  SpeedAtImpact=10.90, VerticalFaceImpact=11.6, HorizontalFaceImpact=0.4, ClosureRate=352.00),
    ShotDataOptions=dict(ContainsBallData=True, ContainsClubData=True, LaunchMonitorIsReady=True,
                         LaunchMonitorBallDetected=True, IsHeartBeat=False),
)
# rēlā's putt: zero-filled spin and carry, no club data.
PUTT = dict(CHIP, ShotNumber=18, ClubData=None,
            BallData=dict(Speed=4.29, SpinAxis=0, TotalSpin=0, BackSpin=0, SideSpin=0, HLA=-11.07, VLA=0.2,
                          CarryDistance=0),
            ShotDataOptions=dict(CHIP['ShotDataOptions'], ContainsClubData=False))
ESTIMATED = {'face_angle', 'dynamic_lie', 'dynamic_loft', 'closure_rate', 'impact_horizontal',
             'impact_vertical', 'carry'}


class ProfileTests(unittest.TestCase):
    def test_standard_keeps_every_value_as_a_measurement(self):
        measured, estimates, fields = source_profiles.classify('standard', CHIP, validate_packet(CHIP))
        self.assertEqual(measured['face_angle'], -13.5)
        self.assertEqual(estimates, {})
        self.assertTrue(all(f['stored'] in ('measurement', 'evidence') for f in fields))

    def test_rela_lpi_keeps_relas_estimates_apart(self):
        measured, estimates, fields = source_profiles.classify('rela_lpi', CHIP, validate_packet(CHIP))
        self.assertEqual((measured['club_speed'], measured['attack_angle'], measured['club_path']),
                         (10.9, -5.06, -14.95))
        self.assertFalse(ESTIMATED & {k for k, v in measured.items() if v is not None})
        self.assertEqual(set(estimates), ESTIMATED)
        self.assertEqual(estimates['carry'], 1.9)
        rows = {f['key']: f for f in fields}
        self.assertEqual(rows['FaceToTarget']['stored'], 'estimate')
        self.assertIn('rēlā estimate', rows['FaceToTarget']['reason'])
        self.assertEqual(rows['Path']['stored'], 'measurement')

    def test_rela_putt_zero_fill_is_not_measured(self):
        measured, estimates, fields = source_profiles.classify('rela_lpi', PUTT, validate_packet(PUTT))
        self.assertEqual({k: measured[k] for k in ('total_spin', 'back_spin', 'side_spin', 'spin_axis')},
                         dict.fromkeys(('total_spin', 'back_spin', 'side_spin', 'spin_axis')))
        self.assertEqual(measured['launch_ang'], 0.2)
        self.assertNotIn('carry', measured)
        self.assertEqual(estimates, {})
        rows = {f['key']: f for f in fields}
        self.assertEqual(rows['TotalSpin']['stored'], 'missing')
        self.assertEqual(rows['CarryDistance']['stored'], 'missing')

    def test_club_data_without_club_speed_is_ignored(self):
        packet = copy.deepcopy(CHIP)
        packet['ClubData']['Speed'] = 0
        measured, estimates, fields = source_profiles.classify('rela_lpi', packet, validate_packet(packet))
        self.assertNotIn('club_path', measured)
        self.assertEqual(set(estimates), {'carry'})


class RelaDirectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.service.input.port = 0
        await self.service.input.start()
        self.service.input.set_profile('rela_lpi')
        self.sim, self.writers, self.received = None, [], []

    async def asyncTearDown(self):
        for writer in self.writers:
            writer.close()
        await self.service.shutdown()
        if self.sim:
            self.sim.close()
            await self.sim.wait_closed()
        self.temp.cleanup()

    async def gspro(self, silent=False):
        """A fake GSPro: 201 on connect, then 200 and 202 per shot (none when silent)."""
        async def serve(reader, writer):
            self.writers.append(writer)
            if not silent:
                writer.write(wire(dict(Code=201, Message='GSPro Player Information', Player=dict(Club='DR'))))
            frames = Frames()
            try:
                while data := await reader.read(8192):
                    for p in frames.feed(data):
                        self.received.append(p)
                        if p['ShotDataOptions']['ContainsBallData'] and not silent:
                            writer.write(wire(dict(Code=200, Message='Shot received successfully')))
                            writer.write(wire(dict(Code=202, Message='GSPro ready')))
                    await writer.drain()
            except OSError:
                pass

        self.sim = await asyncio.start_server(serve, '127.0.0.1', 0)
        await self.service.input.relay.configure(
            dict(destination='gspro', port=self.sim.sockets[0].getsockname()[1]), self.service.input.port
        )

    async def wait(self, condition, seconds=3.0):
        for _ in range(int(seconds / 0.02)):
            if condition():
                return True
            await asyncio.sleep(0.02)
        return False

    async def test_a_rela_chip_is_classified_stored_forwarded_and_acknowledged(self):
        await self.gspro()
        relay = self.service.input.relay
        self.assertTrue(await self.wait(lambda: relay.state['answering'] is True))
        entry = self.service.input.diagnose(CHIP)
        reply = await self.service.input.accept_packet(copy.deepcopy(CHIP), 'rela', entry)
        self.assertTrue(reply['forwarded'])
        self.assertTrue(await self.wait(lambda: entry['simulator']['status'] == 'acknowledged'))
        self.assertEqual(entry['simulator']['reply'], '200 Shot received successfully')
        self.assertEqual(entry['profile'], 'rela_lpi')
        self.assertEqual(set(entry['stored']['estimates']), ESTIMATED)
        # GSPro gets rēlā's packet as sent, club data included.
        sent = [p for p in self.received if p['ShotDataOptions']['ContainsBallData']][-1]
        self.assertEqual(sent['ClubData']['FaceToTarget'], -13.5)
        c = self.service.store.connection
        measured = {r[0] for r in c.execute("SELECT metric_key FROM metric_values WHERE availability='available'")}
        self.assertTrue({'club.speed', 'club.attack_angle', 'club.path'} <= measured)
        self.assertFalse({'club.face_angle', 'club.dynamic_lie', 'club.dynamic_loft', 'flight.carry_distance'}
                         & measured)
        self.assertEqual(c.execute("SELECT count(*) FROM source_estimates WHERE estimator='rela'").fetchone()[0], 7)
        source = c.execute('SELECT configuration_json FROM sources').fetchone()[0]
        self.assertIn('"input_profile": "rela_lpi"', source)

    async def test_a_silent_gspro_is_retried_once_then_reported_and_the_shot_marked(self):
        with patch('shot_input.REPLY_TIMEOUT', 0.3):
            await self.gspro(silent=True)
            relay = self.service.input.relay
            self.assertTrue(await self.wait(lambda: relay.state['connected']))
            entry = self.service.input.diagnose(CHIP)
            await self.service.input.accept_packet(copy.deepcopy(CHIP), 'rela', entry)
            self.assertTrue(await self.wait(lambda: entry['simulator']['status'] == 'no_reply', 6))
            self.assertTrue(await self.wait(lambda: relay.state['answering'] is False, 8))
        self.assertTrue(relay.retried)
        warnings = [a for a in self.service.input.alerts() if a['level'] == 'warning']
        self.assertIn("isn't answering", warnings[0]['message'])
        self.assertIn('range', warnings[0]['message'])

    async def test_alerts_when_rela_is_not_connected(self):
        errors = [a['message'] for a in self.service.input.alerts() if a['level'] == 'error']
        self.assertIn("rēlā isn't connected to TraceLoft", errors[0])
        self.service.input.set_profile('standard')
        self.assertEqual(self.service.input.alerts(), [])
        with self.assertRaises(ValueError):
            self.service.input.set_profile('unknown')

    async def test_the_input_port_moves_live_and_refuses_a_port_in_use(self):
        import socket

        old = self.service.input.port
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            free = probe.getsockname()[1]
        await self.service.input.move(free)
        self.assertEqual((self.service.input.port, self.service.input.state['port']), (free, free))
        r, w = await asyncio.open_connection('127.0.0.1', free)  # the new port accepts a source
        self.writers.append(w)
        with self.assertRaises(OSError):
            await asyncio.open_connection('127.0.0.1', old)  # the old one is closed
        blocker = socket.socket()
        blocker.bind(('127.0.0.1', 0))
        blocker.listen(1)
        self.addCleanup(blocker.close)
        with self.assertRaisesRegex(ValueError, 'already in use'):
            await self.service.input.move(blocker.getsockname()[1])
        self.assertEqual(self.service.input.port, free)  # unchanged after a refusal
        with self.assertRaisesRegex(ValueError, '1 to 65535'):
            await self.service.input.move(70000)

    async def test_a_source_hanging_up_is_a_disconnect_not_an_error(self):
        r, w = await asyncio.open_connection('127.0.0.1', self.service.input.port)
        w.write(wire(dict(CHIP, ShotDataOptions=dict(ContainsBallData=False, ContainsClubData=False,
                                                     IsHeartBeat=True, LaunchMonitorIsReady=True))))
        await w.drain()
        await asyncio.wait_for(r.read(8192), 2)
        w.transport.abort()  # an abrupt close, as when rēlā is closed
        self.assertTrue(await self.wait(lambda: not self.service.input.clients))
        self.assertEqual(self.service.input.state['error'], '')

    async def test_a_refused_packet_is_in_the_trail_with_its_reason(self):
        r, w = await asyncio.open_connection('127.0.0.1', self.service.input.port)
        self.writers.append(w)
        bad = dict(copy.deepcopy(CHIP), Units='Meters')
        w.write(wire(bad))
        await w.drain()
        frames, replies = Frames(), []
        while not replies:
            replies = frames.feed(await asyncio.wait_for(r.read(8192), 2))
        self.assertEqual(replies[0]['Code'], 501)
        entry = self.service.input.diagnostics[0]
        self.assertFalse(entry['stored']['ok'])
        self.assertEqual(entry['source_reply']['code'], 501)
        self.assertEqual(entry['simulator']['status'], 'not_sent')


if __name__ == '__main__':
    unittest.main()
