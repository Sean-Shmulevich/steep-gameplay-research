import math
import unittest
from engine.snow_axis_rotation import rotate_basis_axis


class AxisRotationTests(unittest.TestCase):
    def test_right_hand_quarter_turn_with_nonunit_axis(self):
        output=rotate_basis_axis([1,0,0,0],[0,0,3,9],math.pi/2,0,math.sin,math.cos)
        for a,b in zip(output,[0,1,0,0]): self.assertAlmostEqual(a,b,places=6)

    def test_threshold_inclusive_and_still_calls_trig(self):
        calls=[]
        def sine(x): calls.append(('s',x)); return math.sin(x)
        def cosine(x): calls.append(('c',x)); return math.cos(x)
        output=rotate_basis_axis([2,-3,4,7],[0,0,2,8],1,2,sine,cosine)
        self.assertEqual(output,[2,-3,4,0])
        self.assertEqual(calls,[('s',.5),('c',.5)])

    def test_zero_axis_rejected_without_invented_native_policy(self):
        with self.assertRaises(ValueError):
            rotate_basis_axis([1,0,0,0],[0,0,0,1],1,.001,math.sin,math.cos)
