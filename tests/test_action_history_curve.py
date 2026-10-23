import math
import struct
import unittest
from engine.action_history_curve import history_curve_config, evaluate_history_curve, initial_history_snapshot
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


class ConfiguredHistoryCompositionTests(unittest.TestCase):
    def test_defaults_drive_history_and_release_without_changing_raw_input(self):
        from engine.action_history_features import update_mode3_history
        for channel in (0, 1):
            config = history_curve_config(channel)
            state = initial_history_snapshot(channel)
            angle = math.pi / 6
            raw = struct.pack('<4f', math.sin(angle), math.cos(angle), 0, 0)
            outputs = []
            for now, payload in ((50, raw), (51, bytes(16)), (52, raw)):
                result = update_mode3_history(state, payload, now=now,
                    primary=(0,1,0,0), secondary=(1,0,0,0),
                    curve=lambda x: evaluate_history_curve(x, config['points']))
                state = result['snapshot']
                outputs.append(struct.unpack_from('<4f', state, 0x240))
                self.assertEqual(state[0x60:0x70], payload)
                self.assertEqual(struct.unpack_from('<Q', state)[0], now)
                self.assertEqual(state[0x308:], bytes(0x3c0-0x308))
            expected_angle = math.pi / (9 if channel == 0 else 6)
            self.assertAlmostEqual(outputs[0][0], math.sin(expected_angle), places=6)
            self.assertEqual(outputs[1], (0,0,0,0))
            self.assertEqual(outputs[0], outputs[2])
            self.assertEqual(struct.unpack_from('<3Q', state), (52,51,50))
            self.assertEqual(struct.unpack_from('<4f', state, 0x260), outputs[0])
