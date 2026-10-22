import math
import unittest
from functools import partial
from engine.action_curve_roots import ordered_curve_roots

# Portable math fixture, not claimed as original CRT implementation.
solve = partial(ordered_curve_roots, sqrt=math.sqrt, acos=math.acos,
                cos=math.cos, power=math.pow)

class CurveRootTests(unittest.TestCase):
    def test_degree_fallback_and_order(self):
        self.assertEqual(solve(1, 0, 0, 0), ())
        self.assertEqual(solve(0, 0, 0, 0), ())
        self.assertEqual(solve(-4, 2, 0, 0), (2.,))
        self.assertEqual(solve(-1, 0, 1, 0), (1., -1.))
        self.assertEqual(solve(1, 0, 1, 0), ())
    def test_quadratic_tolerance(self):
        self.assertEqual(solve(.00005, 0, 1, 0), (-0.,))
        self.assertEqual(solve(-.00005, 0, 1, 0), (-0.,))
        self.assertEqual(solve(.0002, 0, 1, 0), ())
        self.assertEqual(len(solve(-.0002, 0, 1, 0)), 2)
    def test_cubic_root_order(self):
        roots = solve(0, -1, 0, 1)
        for actual, expected in zip(roots, (-1, 1, 0)):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertAlmostEqual(solve(-1, 0, 0, 1)[0], 1, places=6)
        with self.assertRaises(ValueError):
            solve(0, 0, 0, 1)

    def test_composed_key_curve(self):
        from engine.action_key_curve import CurveKey, evaluate_key_curve
        keys = (CurveKey(0, 0, (0, 0), (0, 0), 2),
                CurveKey(1, 1, (1, 1), (1, 1), 0))
        for x in (.1, .25, .5, .75, .9):
            self.assertAlmostEqual(evaluate_key_curve(keys, x, solve_roots=solve), x, places=5)
