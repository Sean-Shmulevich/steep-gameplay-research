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

    def test_cosine_regression_and_domain(self):
        from engine.action_curve_math import curve_cos
        self.assertEqual(struct.pack('<f', curve_cos(2.3673617839813232)).hex(), '8d0737bf')
        self.assertEqual(curve_cos(0), 1)
        for x in (.1, .7853982, 1.5707964, 3.1415927, 4.712389, 6.):
            self.assertEqual(curve_cos(x), curve_cos(-x))
            self.assertAlmostEqual(curve_cos(x), math.cos(struct.unpack('<f', struct.pack('<f', x))[0]), places=6)
        with self.assertRaises(ValueError):curve_cos(7)

    def test_composed_reconstructed_trig(self):
        from functools import partial
        from engine.action_curve_roots import ordered_curve_roots
        from engine.action_curve_math import curve_cos
        solve = partial(ordered_curve_roots, sqrt=math.sqrt, acos=curve_acos,
                        cos=curve_cos, power=math.pow)
        roots = solve(-9.999999747378752e-05, -1., -1., 1.)
        self.assertEqual(roots, (-0.6179615259170532, 1.6180616617202759, -0.00010040402412414551))
