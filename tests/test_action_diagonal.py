import math
import struct
import unittest
from engine.action_diagonal import correct_diagonal,EPSILON,DIAGONAL_SCALE

class DiagonalTests(unittest.TestCase):
    def test_diagonal_and_axis(self):
        self.assertEqual(correct_diagonal([1,1,0,0]),[DIAGONAL_SCALE,DIAGONAL_SCALE,0,0])
        self.assertEqual(correct_diagonal([-1,0,0,0]),[-1,0,0,0])
    def test_preserves_dominant_magnitude_not_unit_length(self):
        x,y,*_=correct_diagonal([.8,.3,2,3])
        self.assertAlmostEqual(math.hypot(x,y),.8,places=6)
        self.assertEqual(correct_diagonal([.8,.3,2,3])[2:],[2,3])
    def test_four_lane_early_return(self):
        small=EPSILON/2
        self.assertEqual(correct_diagonal([small,small,0,0])[:2],[small,small])
        self.assertLess(correct_diagonal([small,small,1,0])[0],small)
    def test_signed_zero_and_nonfinite_boundary(self):
        self.assertEqual(struct.pack('<f',correct_diagonal([-0.,0.,0.,0.])[0]),b'\0\0\0\x80')
        for value in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):correct_diagonal([value,0,0,0])
