"""User scorecard, sand cutouts and independent lakeside landmarks."""
import math
import tempfile
import unittest
from bundled_courses import load_bundled, bundled_catalog
from course_geometry import classify
from golf_sim import GolfSimSession


class JudgesCourseTests(unittest.TestCase):
    def test_user_yardages_and_selected_nines(self):
        c=load_bundled('judges-course-v1')
        yards=[353,460,157,365,372,496,380,153,330,362,552,322,335,137,424,145,442,378]
        self.assertEqual([h['yards'] for h in c['holes']],yards)
        self.assertEqual((c['yards'],c['par']),(6163,72))
        with tempfile.TemporaryDirectory() as folder:
            for selection,expected in [('full',list(range(1,19))),('front',list(range(1,10))),('back',list(range(10,19)))]:
                p=GolfSimSession(folder,game_course_id=c['id'],game_holes=selection)
                self.assertEqual([h['hole_number'] for h in p.data['round']['holes']],expected)
                self.assertEqual(p.data['round']['yards'],sum(yards[n-1] for n in expected))
        row=next(r for r in bundled_catalog() if r['id']==c['id'])
        self.assertEqual([o['id'] for o in row['round_options']],['full','front','back'])

    def test_grass_islands_and_split_fairways_are_not_filled(self):
        c=load_bundled('judges-course-v1')
        for number in (2,5):
            h=c['holes'][number-1]
            cutouts=[r for p in h['surfaces']['sand'] for r in p['holes']]
            self.assertTrue(cutouts)
            points={2:[[653,246],[693,250],[730,223],[841,184]],5:[[432,319]]}
            for x,y in points[number]:
                a,_,_,e,f,g=h['image']['transform'];x*=h['image']['width']/1000;y*=h['image']['width']/1000
                self.assertNotEqual(classify([y*e+g,x*a+f],h),'sand')
        for number in (12,15):self.assertEqual(len(c['holes'][number-1]['surfaces']['fairway']),2)

    def test_water_carry_and_native_image_scale(self):
        c=load_bundled('judges-course-v1')
        h=c['holes'][15]
        middle=[(a+b)/2 for a,b in zip(h['tee'],h['pin'])]
        self.assertEqual(classify(middle,h),'water')
        for h in c['holes']:
            a,b,d,e,_,_=h['image']['transform']
            self.assertEqual((b,d),(0,0));self.assertEqual(a,e)
            self.assertAlmostEqual(h['viewbox'][2]/h['viewbox'][3],h['image']['width']/h['image']['height'])
            self.assertAlmostEqual(sum(math.dist(a,b) for a,b in zip(h['playing_line'],h['playing_line'][1:])),h['yards'],places=4)
