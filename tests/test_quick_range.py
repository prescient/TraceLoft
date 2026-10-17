"""Quick range for loose shots and automatic putter tags (D75)."""

import copy
import tempfile
import unittest

from web_service import GolfService

SWING = dict(
    DeviceID='DESKTOP-00UC2B2', Units='Yards', ShotNumber=1, APIversion='1',
    BallData=dict(Speed=11.06, SpinAxis=15.29, TotalSpin=1077.12, BackSpin=1039, SideSpin=284, HLA=-5.11,
                  VLA=30.27),
    ShotDataOptions=dict(ContainsBallData=True, ContainsClubData=False, LaunchMonitorIsReady=True),
)
PUTT = dict(SWING, ShotNumber=2,
            BallData=dict(Speed=4.29, SpinAxis=0, TotalSpin=0, BackSpin=0, SideSpin=0, HLA=-1.1, VLA=0.2))


class QuickRangeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.service.input.port = 0
        await self.service.input.start()
        self.bag = self.service.equipment['bags'][0]
        self.club = {c['label']: c['id'] for c in self.bag['clubs']}

    async def asyncTearDown(self):
        await self.service.shutdown()
        self.temp.cleanup()

    async def send(self, packet, number):
        entry = self.service.input.diagnose(packet)
        await self.service.input.accept_packet(dict(copy.deepcopy(packet), ShotNumber=number), 'rela', entry)
        return entry

    async def test_a_shot_with_nothing_running_starts_a_quick_range_and_joins_it(self):
        self.assertIsNone(self.service.practice)
        entry = await self.send(SWING, 1)
        practice = self.service.practice
        self.assertTrue(practice.data['quick_range'])
        self.assertEqual(practice.data['range_target'], 0)
        self.assertEqual(len(practice.data['shots']), 1)
        self.assertEqual(entry['quick_range'], practice.data['id'])
        # One bag: it is preselected (no club), so putts can still find the putter.
        self.assertEqual(practice.data['equipment_selection']['bag_id'], self.bag['id'])
        await self.send(SWING, 2)
        self.assertIs(self.service.practice, practice)  # the next shot joins the same session
        self.assertEqual(len(practice.data['shots']), 2)

    async def test_launching_a_drill_finishes_the_quick_range(self):
        await self.send(SWING, 1)
        quick = self.service.practice.data['id']
        self.service.create_practice(dict(drill='Driving range', range_target=150))
        self.assertNotEqual(self.service.practice.data['id'], quick)
        self.assertTrue(self.service.load_session(quick).data['ended'])

    async def test_quick_range_can_be_turned_off(self):
        self.service.input.state['quick_range'] = False
        await self.send(SWING, 1)
        self.assertIsNone(self.service.practice)
        self.assertEqual(self.service.store.count('shots'), 1)  # still recorded

    async def test_a_putt_is_tagged_with_the_putter_for_that_shot_only(self):
        self.service.create_practice(
            dict(drill='Driving range', range_target=150, range_bag_id=self.bag['id'],
                 range_club_id=self.club['7 iron'])
        )
        entry = await self.send(PUTT, 1)
        await self.send(SWING, 2)
        putt, swing = self.service.practice.data['shots']
        self.assertEqual((putt['club_label'], putt['selection_mode']), ('Putter', 'auto_putt'))
        self.assertEqual(entry['auto_club'], 'Putter')
        self.assertEqual((swing['club_label'], swing['selection_mode']), ('7 iron', 'manual'))
        self.assertEqual(self.service.practice.data['equipment_selection']['club_label'], '7 iron')

    async def test_no_putter_or_spin_measured_means_no_automatic_tag(self):
        self.assertIsNone(self.service.input.putt_selection(dict(result='validated', vals=dict(total_spin=900))))
        self.assertIsNone(self.service.input.putt_selection(
            dict(result='validated', vals=dict(total_spin=None), simulated=True)))
        bag = dict(self.bag, clubs=[c for c in self.bag['clubs'] if c['label'] != 'Putter'])
        self.service.equipment = dict(self.service.equipment, bags=[bag])
        self.assertIsNone(self.service.input.putt_selection(dict(result='validated', vals=dict(total_spin=0))))


if __name__ == '__main__':
    unittest.main()
