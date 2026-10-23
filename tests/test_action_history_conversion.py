import math
import unittest
from engine.action_history_conversion import convert_history_mode3


class HistoryConversionTests(unittest.TestCase):
    def test_fourth_lane_is_not_preserved_by_xyz_rotation(self):
        result = convert_history_mode3([0,0,1,0], primary=[1,0,0,0], secondary=[0,1,0,0])
        for actual, expected in zip(result['output'], [0,0,1,0]):
            self.assertAlmostEqual(actual, expected, places=6)

    def test_input_normalization_includes_fourth_lane(self):
        result = convert_history_mode3([0,3,0,4], primary=[0,1,0,0], secondary=[1,0,0,0])
        self.assertAlmostEqual(result['output'][1], .6, places=6)
        self.assertEqual(result['output'][3], 0)
        self.assertAlmostEqual(sum(v*v for v in result['output']), .36, places=6)

    def test_vertical_fallback_and_zero_early_return(self):
        result = convert_history_mode3([0,2,0,0], primary=[0,0,-1,0], secondary=[-1,0,0,0])
        self.assertTrue(result['secondary_used'])
        self.assertAlmostEqual(result['output'][0], -1, places=6)
        zero = convert_history_mode3([-0.,0.,0.,0.], primary=None, secondary=None)
        self.assertLess(math.copysign(1, zero['output'][0]), 0)
        self.assertIsNone(zero['yaw'])
        with self.assertRaises(ValueError):
            convert_history_mode3([1,0,0,0], primary=[0,0,.5,0], secondary=[0,1,0,0])


if __name__ == '__main__': unittest.main()
