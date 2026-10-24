import math
import unittest
from engine.markup_snow_vector import snow_vector


class SnowVectorTests(unittest.TestCase):
    def test_projection_and_nonunit_normal(self):
        seed=lambda x:1/math.sqrt(x)
        for scale in (1.,2.):
            result=snow_vector([1,0,1],[0,0,scale],3,seed)
            self.assertAlmostEqual(result[0],3*scale,places=5)
            self.assertEqual(result[1:],[0.,0.])

    def test_near_parallel_fallback_skips_seed(self):
        def forbidden(x):self.fail('seed should not run')
        self.assertEqual(snow_vector([0,0,2],[0,0,1],3,forbidden),[0.,0.,6.])
        self.assertEqual(snow_vector([1,2,3],[0,0,0],2,forbidden),[2.,4.,6.])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):snow_vector([0,0],[0,0,1],1,None)
        with self.assertRaises(ValueError):snow_vector([0,0,float('nan')],[0,0,1],1,None)
