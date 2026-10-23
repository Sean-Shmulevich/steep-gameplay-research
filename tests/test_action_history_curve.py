import math
import unittest
from engine.action_history_curve import history_curve_config, evaluate_history_curve
from engine.action_sample import f32


class HistoryCurveTests(unittest.TestCase):
    def test_two_channels_have_different_angle_response(self):
        first = history_curve_config(0)
        second = history_curve_config(1)
        self.assertLess(evaluate_history_curve(1/6, first['points']), math.pi/6)
        self.assertAlmostEqual(evaluate_history_curve(1/6, second['points']), math.pi/6, places=6)
        self.assertLess(first['threshold'], second['threshold'])

    def test_center_flag_adds_dead_region_only_to_first_channel(self):
        normal = history_curve_config(0)
        alternate = history_curve_config(0, alternate_center=True)
        self.assertGreater(evaluate_history_curve(.005, normal['points']), 0)
        self.assertEqual(evaluate_history_curve(.005, alternate['points']), 0)
        self.assertEqual(history_curve_config(1), history_curve_config(1, alternate_center=True))
        self.assertEqual(normal['points'][2:], alternate['points'][3:])

    def test_range_and_knot_boundaries(self):
        points = ((0., 2.), (.5, 4.), (1., 9.))
        self.assertEqual(evaluate_history_curve(-.001, points), 0)
        self.assertEqual(evaluate_history_curve(1.001, points), 0)
        self.assertEqual(evaluate_history_curve(.5, points), 4)
        self.assertEqual(evaluate_history_curve(1., points), 9)
        self.assertEqual(evaluate_history_curve(.25, points), 3)
        with self.assertRaises(ValueError): evaluate_history_curve(0, ((0,0),(0,1)))
        with self.assertRaises(ValueError): evaluate_history_curve(float('nan'), points)
        with self.assertRaises(ValueError): history_curve_config(True)
