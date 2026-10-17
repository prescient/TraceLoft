"""Voice club selection (D76): phrases, matching and what a recognized club does. No microphone needed."""

import tempfile
import unittest
from unittest.mock import patch

import voice
from equipment import COMMON_CLUBS
from web_service import GolfService


class PhraseTests(unittest.TestCase):
    def test_every_common_club_has_a_spoken_name(self):
        expected = {
            'Driver': 'driver', '3 wood': 'three wood', '4 hybrid': 'four hybrid', '7 iron': 'seven iron',
            'PW': 'pitching wedge', 'SW': 'sand wedge', 'LW': 'lob wedge', 'Putter': 'putter',
        }
        for label in COMMON_CLUBS:
            self.assertTrue(voice.spoken_names(label), label)
        for label, phrase in expected.items():
            self.assertIn(phrase, voice.spoken_names(label))

    def test_short_labels_and_lofts(self):
        self.assertIn('seven iron', voice.spoken_names('7i'))
        self.assertIn('five wood', voice.spoken_names('5W'))
        self.assertIn('fifty six degree', voice.spoken_names('56°'))
        self.assertIn('putter', voice.spoken_names('PT'))
        self.assertEqual(voice.spoken_names('Chipper'), ['chipper'])

    def test_a_phrase_two_clubs_share_is_left_out(self):
        bag = dict(clubs=[dict(id='a', label='7 iron'), dict(id='b', label='7i'), dict(id='c', label='Putter')])
        words = voice.vocabulary(bag)
        self.assertNotIn('seven iron', words)
        self.assertEqual(words['putter']['id'], 'c')

    def test_only_whole_confident_phrases_match(self):
        words = {'seven iron': dict(id='7')}
        sure = dict(text='seven iron', result=[dict(word='seven', conf=0.98), dict(word='iron', conf=0.95)])
        self.assertEqual(voice.match(sure, words)['id'], '7')
        unsure = dict(sure, result=[dict(word='seven', conf=0.4), dict(word='iron', conf=0.95)])
        self.assertIsNone(voice.match(unsure, words))
        self.assertIsNone(voice.match(dict(text='seven'), words))
        self.assertIsNone(voice.match(dict(text='[unk]'), words))


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = GolfService(self.temp.name)
        self.bag = self.service.equipment['bags'][0]
        self.club = {c['label']: c for c in self.bag['clubs']}

    async def asyncTearDown(self):
        await self.service.shutdown()
        self.temp.cleanup()

    async def test_a_heard_club_is_selected_for_the_next_shot(self):
        self.service.create_practice(dict(drill='Driving range', range_bag_id=self.bag['id']))
        self.assertIn('seven iron', self.service.voice_vocab)  # the active bag's phrases
        self.service.voice_heard(self.club['7 iron'], 'seven iron')
        self.assertEqual(self.service.practice.data['equipment_selection']['club_label'], '7 iron')
        self.assertIn('7 iron for the next shot', self.service.voice_state['message'])

    async def test_with_nothing_running_voice_starts_a_quick_range(self):
        self.service.voice_heard(self.club['PW'], 'pitching wedge')
        self.assertTrue(self.service.practice.data['quick_range'])
        self.assertEqual(self.service.practice.data['equipment_selection']['club_label'], 'PW')
        self.service.input.state['quick_range'] = False
        self.service.change_practice(self.service.practice.data['id'], 'finish')
        self.service.voice_heard(self.club['PW'], 'pitching wedge')
        self.assertIn('start a full-swing drill', self.service.voice_state['message'])

    async def test_turning_voice_on_without_it_installed_says_what_is_missing(self):
        with patch('voice.available', return_value=(False, 'Needs the vosk package.')):
            with self.assertRaisesRegex(ValueError, 'vosk'):
                self.service.set_voice(True)
        self.assertFalse(self.service.voice_state['enabled'])


if __name__ == '__main__':
    unittest.main()
