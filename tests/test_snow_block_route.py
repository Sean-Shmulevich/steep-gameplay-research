import unittest
from engine.snow_block_route import select_block_release_route as select

class SnowBlockRouteTests(unittest.TestCase):
    def test_nested_dispatch_and_variant_difference(self):
        self.assertEqual(select('A',0,1),dict(callback='outer_one_callback',receiver_depth=1))
        self.assertIsNone(select('B',0,1))
        self.assertIsNone(select('A',0,0,1))
        self.assertEqual(select('B',0,0,1),dict(callback='release_block_if_fc9',receiver_depth=2))
        for variant in ('A','B'):
            self.assertEqual(select(variant,0,0,5),dict(callback='release_block',receiver_depth=2))
            self.assertIsNone(select(variant,0,0,0xffffffff))
            self.assertIsNone(select(variant,1,0))
        self.assertEqual(select('B',0,0,0),dict(callback='inner_zero_callback',receiver_depth=2))

    def test_conditional_inner_dependency(self):
        self.assertIsNone(select('A',0,2))
        for value in (None,-1,True,2**32):
            with self.assertRaises(ValueError):select('B',0,0,value)
        with self.assertRaises(ValueError):select('C',0,0,5)
        with self.assertRaises(ValueError):select('A',True,0,5)
