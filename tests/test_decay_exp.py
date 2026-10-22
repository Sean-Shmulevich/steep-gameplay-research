import math
import unittest
from reference.central_impulse import f32
from reference.decay_exp import exp_lane
from reference.decay_table import sample_arguments, build, evaluate


class DecayExpTests(unittest.TestCase):
    def test_paths_agree_on_grid_and_preserve_monotonic_decay(self):
        xs=sample_arguments()
        sse2=[exp_lane(x,path='sse2') for x in xs]
        self.assertEqual(sse2,[exp_lane(x,path='sse41') for x in xs])
        self.assertEqual(sse2[-1],1)
        self.assertTrue(all(a<b for a,b in zip(sse2,sse2[1:])))
        table=build(sse2)
        self.assertGreater(evaluate(-5,**table),0)
        self.assertLess(evaluate(-5,**table),1)

    def test_native_arithmetic_is_not_host_exp_rounding(self):
        for path in ('sse2','sse41'):
            self.assertEqual(exp_lane(-5,path=path),0.006737947463989258)
            self.assertNotEqual(exp_lane(-5,path=path),f32(math.exp(-5)))

    def test_rejects_unreconstructed_domain_and_unspecified_path(self):
        for x in (-11,1,float('inf'),float('nan')):
            with self.assertRaises(ValueError): exp_lane(x,path='sse2')
        with self.assertRaises(ValueError): exp_lane(-1,path='auto')
