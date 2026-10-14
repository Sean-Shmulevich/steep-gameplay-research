import math
import unittest
from engine.animation_endpoints import endpoint_delta


class EndpointTests(unittest.TestCase):
    def test_displacement_includes_fourth_lane(self):
        result = endpoint_delta((1,2,3,4), (4,0,5,9), (0,0,0,1), (0,0,0,1))
        self.assertEqual(result['displacement'], [3,-2,2,5])
        self.assertEqual(result['rotation'], [0,0,0,1])

    def test_rotation_order_noncommuting(self):
        h = math.sqrt(.5)
        result = endpoint_delta((0,)*4, (0,)*4, (h,0,0,h), (0,h,0,h))
        for actual, expected in zip(result['rotation'], (-.5,.5,-.5,.5)):
            self.assertAlmostEqual(actual, expected, places=6)

    def test_variant_and_explicit_seed(self):
        result = endpoint_delta((0,)*4, (1,2,3,4), (0,0,0,1), (0,0,1,0),
                                variant=True, rsqrt_estimate=1)
        self.assertEqual(result['displacement'], [-1,2,3,4])
        self.assertEqual(result['rotation'], [0,0,-1,0])
        self.assertEqual(result['seed_policy'], 'caller_supplied')

    def test_invalid_norm_and_variant(self):
        with self.assertRaises(ValueError):
            endpoint_delta((0,)*4, (0,)*4, (0,)*4, (0,)*4)
        with self.assertRaises(ValueError):
            endpoint_delta((0,)*4, (0,)*4, (0,0,0,1), (0,0,0,1), variant=1)
