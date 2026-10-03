import copy
import unittest
from club_preview import build_preview
from flight_model import MODEL


class ClubPreviewTests(unittest.TestCase):
    def setUp(self):
        self.game = dict(demo=True, equipment_selection=dict(bag_id='b', club_id='c'),
                         game_settings=dict(geometry='downrange'))
        self.shot = dict(bag_id='b', club_id='c', vals=dict(total=100, offline=6, carry=90),
                         flight=dict(model=MODEL,status='ready',carry_point_yd=dict(forward=89,right=4),
                                     total_point_yd=dict(forward=99,right=6)))

    def session(self, **kw):
        return dict(dict(collection_kind='bag', demo=True, started='2026-10-02', shots=[copy.deepcopy(self.shot)]), **kw)

    def test_cohorts_cleanup_and_effective_retags(self):
        shots=[copy.deepcopy(self.shot) for _ in range(5)]
        shots[1]['excluded']=True
        shots[2]['removed']=True
        shots[3]['corrected_equipment']=dict(bag_id='other',club_id='c')
        shots[4]['club_id']='old'
        shots[4]['corrected_equipment']=dict(bag_id='b',club_id='c')
        sessions=[self.session(shots=shots),self.session(demo=False),self.session(collection_kind=None),self.session(deleted=True)]
        before=copy.deepcopy(sessions)
        p=build_preview(sessions,self.game)['profiles'][0]
        self.assertEqual((p['included'],p['excluded'],p['removed']),(2,1,1))
        self.assertEqual(len(p['views']['reported_total']['points']),2)
        self.assertEqual(sessions,before)
        self.game['equipment_selection']['club_id']='missing'
        self.assertFalse(build_preview(sessions,self.game)['profiles'])

    def test_wedge_intents_and_bag_mapping_are_never_blended(self):
        full=copy.deepcopy(self.shot);full['swing_label']='Full'
        half=copy.deepcopy(self.shot);half['swing_label']='Half'
        data=build_preview([self.session(),self.session(collection_kind='wedge',shots=[full,half])],self.game)
        self.assertEqual([p['id'] for p in data['profiles']],['bag:','wedge:Full','wedge:Half'])
        self.assertTrue(all(p['included']==1 for p in data['profiles']))

    def test_paired_provenance_missing_fields_and_radial_geometry(self):
        missing=copy.deepcopy(self.shot);missing['vals'].pop('offline');missing['flight']['model']='other-model'
        impossible=copy.deepcopy(self.shot);impossible['vals'].update(total=5,offline=6)
        self.game['game_settings']['geometry']='radial'
        views=build_preview([self.session(shots=[self.shot,missing,impossible])],self.game)['profiles'][0]['views']
        self.assertNotIn('reported_carry',views)
        self.assertAlmostEqual(views['reported_total']['points'][0]['forward'],(10000-36)**.5)
        self.assertEqual(views['reported_total']['missing'],2)
        self.assertEqual(views['model_carry']['points'][0],dict(forward=89,right=4))
        self.assertEqual(views['model_carry']['missing'],1)

    def test_empty_singleton_and_invalid_numbers(self):
        self.assertFalse(build_preview([],self.game)['profiles'])
        self.shot['vals'].update(total=float('nan'),offline=True)
        p=build_preview([self.session()],self.game)['profiles'][0]
        self.assertIsNone(p['views']['reported_total']['distance']['median'])
        self.assertIsNone(p['views']['model_total']['distance']['iqr'])
        self.assertEqual(p['views']['model_total']['distance']['median'],99)
