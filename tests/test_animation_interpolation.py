import math
import unittest
from engine.animation_interpolation import quaternion_sample_blend as blend


class QuaternionSampleTests(unittest.TestCase):
    def test_near_absolute_unit_dot_copies_source_without_normalizing(self):
        a = [2,0,0,0]
        self.assertEqual(blend(a,[.5,0,0,0],.9), a)
        self.assertEqual(blend(a,[-.5,0,0,0],.9), a)

    def test_negative_hemisphere_and_polynomial_symmetry(self):
        a=[0,0,0,1]; b=[0,0,math.sqrt(.5),math.sqrt(.5)]
        for t in (0,.25,.5,.75,1):
            positive=blend(a,b,t)
            self.assertEqual(positive,blend(a,[-v for v in b],t))
            for x,y in zip(positive,blend(b,a,1-t)):
                self.assertAlmostEqual(x,y,places=6)
            self.assertAlmostEqual(sum(x*x for x in positive),1,places=6)

    def test_aligned_branch_and_explicit_seed(self):
        b=[0,0,.1,math.sqrt(.99)]
        q=blend([0,0,0,1],b,.5)
        self.assertGreater(q[2],0)
        self.assertAlmostEqual(sum(x*x for x in q),1,places=6)
        self.assertNotEqual(q,blend([0,0,0,1],b,.5,rsqrt_estimate=.9))

    def test_invalid_inputs(self):
        for a,b,t in (([0]*4,[0]*4,.5),([0,0,0,1],[0,0,0,1],2)):
            with self.assertRaises(ValueError):blend(a,b,t)


class QuaternionCopyThresholdTests(unittest.TestCase):
    def test_exact_float32_epsilon_copies_but_next_value_blends(self):
        from engine.animation_endpoints import f32
        source=[0,0,0,1]
        boundary=[.001,0,0,f32(1-2**-23)]
        outside=[.001,0,0,f32(1-3*2**-24)]
        self.assertEqual(blend(source,boundary,.5),source)
        result=blend(source,outside,.5)
        self.assertGreater(result[0],0)
        self.assertNotEqual(result,source)
