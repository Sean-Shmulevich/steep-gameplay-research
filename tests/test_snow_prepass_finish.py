import math
import unittest
from engine.snow_prepass_finish import finish_prepass_basis


class PrepassFinishTests(unittest.TestCase):
    def finish(self, replace=False):
        calls=[]
        def speed(x):calls.append(('speed',x));return .5
        def immersion(x):calls.append(('immersion',x));return .25
        r=finish_prepass_basis([2,0,0,0],[0,0,3,0],0,0,4,5,replace,
                              [[9,8,7,6],[5,4,3,2],[1,2,3,4]],speed,immersion,
                              math.sin,math.cos,lambda n:1/math.sqrt(n))
        return r,calls

    def test_third_axis_keeps_cross_magnitude(self):
        r,calls=self.finish()
        self.assertEqual(r['basis'],[[1,0,0,0],[0,0,1,0],[0,-6,0,0]])
        self.assertEqual(calls,[('speed',4),('immersion',5)])

    def test_replacement_keeps_raw_captured_vectors_after_calculating(self):
        r,calls=self.finish(True)
        self.assertEqual(r['basis'],[[9,8,7,6],[5,4,3,2],[1,2,3,4]])
        self.assertEqual(r['computed_basis'][2],[0,-6,0,0])
        self.assertEqual(len(calls),2)
