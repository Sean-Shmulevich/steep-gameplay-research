import math
import struct
import unittest
from engine.action_curve_math import curve_acos

class CurveMathTests(unittest.TestCase):
    def test_endpoints_and_symmetry(self):
        self.assertEqual(curve_acos(1), 0)
        self.assertAlmostEqual(curve_acos(-1), math.pi, places=6)
        self.assertEqual(curve_acos(-0.), curve_acos(0.))
        for x in (.1, .499999, .5, .500001, .99):
            self.assertAlmostEqual(curve_acos(x) + curve_acos(-x), math.pi, places=6)
    def test_original_math_regression(self):
        # Synthetic argument from offline solver comparison, not a game asset.
        self.assertEqual(struct.pack('<f', curve_acos(-.6876687407493591)).hex(), '7a0f1540')
        self.assertNotEqual(struct.pack('<f', math.acos(-.6876687407493591)).hex(), '7a0f1540')
    def test_domain(self):
        for x in (2., -2., math.inf, math.nan):
            with self.assertRaises(ValueError):curve_acos(x)
