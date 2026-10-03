import json
import math
import unittest
from pathlib import Path
from course_geometry import classify, in_polygon
from golf_sim import COURSE, GolfSimSession, simulated_event
import tempfile

class CourseGeometryTests(unittest.TestCase):
    def setUp(self):
        self.course=json.loads((Path(__file__).parents[1]/'courses/meadow-one-v2.json').read_text())

    def test_polygon_islands_edges_and_surface_priority(self):
        polygon={'outer':[[0,0],[0,10],[10,10],[10,0]],'holes':[[[3,3],[3,7],[7,7],[7,3]]]}
        self.assertTrue(in_polygon([0,5],polygon))
        self.assertFalse(in_polygon([5,5],polygon))
        self.assertFalse(in_polygon([11,5],polygon))
        c=dict(bounds=[-5,15,-5,15],surfaces={'green':[polygon],'water':[polygon]})
        self.assertEqual(classify([1,1],c),'water')
        self.assertEqual(classify([5,5],c),'rough')
        self.assertEqual(classify([20,5],c),'out of bounds')

    def test_art_registration_and_irregular_shore(self):
        c=self.course;a,b,d,e,f,g=c['image']['transform']
        def world(x,y):return [b*x+e*y+g,a*x+d*y+f]
        self.assertAlmostEqual(math.dist(world(104,438),world(1590,418)),350)
        for pixel,lie in [((104,438),'tee'),((1590,418),'green'),((1100,210),'water'),((900,210),'rough'),((1540,286),'sand'),((1660,559),'sand'),((100,70),'nature')]:
            self.assertEqual(classify(world(*pixel),c),lie,pixel)
        self.assertGreater(len(c['surfaces']['water'][0]['outer']),20)

    def test_new_round_and_legacy_geometry_remain_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            p=GolfSimSession(folder)
            self.assertEqual(p.data['course']['id'],'meadow-one-v2')
            p.add(simulated_event(p,200));self.assertEqual(p.data['game']['lie'],'fairway')
            p.add(simulated_event(p,145));self.assertEqual(p.data['game']['lie'],'green')
            p.add(simulated_event(p,5));self.assertEqual(p.data['game']['strokes'],3)
            old=GolfSimSession(folder,game_course_id='meadow-one-v1')
            self.assertEqual(old.data['course'],COURSE)
            self.assertNotIn('surfaces',old.data['course'])
            self.assertEqual(classify([-43,225],old.data['course']),'water')
