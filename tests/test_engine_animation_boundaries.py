"""Malformed numeric and discontinuous-key regressions for the animation API."""
import math
import unittest
from engine import animation


class AnimationBoundaryTests(unittest.TestCase):
    def test_large_finite_quaternion_keeps_rotation(self):
        q=animation._quat([1e300,0,0,1e300])
        self.assertAlmostEqual(math.hypot(*q),1.)
        self.assertAlmostEqual(q[0],math.sqrt(.5))

    def test_before_duplicate_first_time_and_exact_step(self):
        keys=[{'time':.1,'value':[1,0,0]}, {'time':.1,'value':[2,0,0]}, {'time':.2,'value':[3,0,0]}]
        for recovered in (False,True):
            self.assertEqual(animation._sample_separate(keys,0.,'translation',recovered),[1,0,0])
            self.assertEqual(animation._sample_separate(keys,.1,'translation',recovered),[2,0,0])
            self.assertEqual(animation._sample_separate(keys,.2,'translation',recovered),[3,0,0])

    def test_recovered_unrepresentable_tick_rejected(self):
        keys=[{'time':0.,'value':[0,0,0]}, {'time':1.,'value':[1,0,0]}]
        with self.assertRaises(ValueError):
            animation._sample_separate(keys,1e300,'translation',True)


if __name__=='__main__': unittest.main()
