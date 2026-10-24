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


class Branch3GainTests(unittest.TestCase):
    def test_mapping_and_bit_preservation(self):
        from engine.markup_snow_vector import branch3_gain_bits
        for state,offset in [(0,0x60),(2,0x5c),(5,0x5c),(9,0x1a8)]:
            calls=[]
            def read(field):calls.append(field);return 0x7fc12345
            self.assertEqual(branch3_gain_bits(state,read),0x7fc12345)
            self.assertEqual(calls,[offset])
        for state in (1,3,4,6,7,8,10,0xffffffff):
            self.assertEqual(branch3_gain_bits(state,lambda _:self.fail('unexpected field read')),0)


class Branch3VectorTests(unittest.TestCase):
    def test_direct_and_reversed_low_magnitude(self):
        from engine.markup_snow_vector import branch3_vector
        def no_seed(x):self.fail('normalization must not run')
        args=([0,0,0],[0,0,1],[1,0,0],2)
        self.assertEqual(branch3_vector(*args,direct_direction=True,reverse_fallback=True,reciprocal_sqrt_seed=no_seed),[2.,0.,0.])
        self.assertEqual(branch3_vector(*args,direct_direction=False,reverse_fallback=True,reciprocal_sqrt_seed=no_seed),[-2.,-0.,-0.])

    def test_parallel_high_magnitude_is_not_replaced_with_fallback(self):
        from engine.markup_snow_vector import branch3_vector
        result=branch3_vector([0,0,2],[0,0,1],[1,0,0],1,direct_direction=False,reverse_fallback=False,reciprocal_sqrt_seed=lambda x:float('inf'))
        self.assertTrue(all(math.isnan(x) for x in result))
