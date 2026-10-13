import copy
import math
import struct
import unittest
from engine.action_processor import initial_state, process_default


class DefaultActionProcessorTests(unittest.TestCase):
    def test_diagonal_and_fourth_lane_are_not_normalized_or_discarded(self):
        result = process_default([1, 1, 0, .25])
        self.assertEqual(result['output'], [1, 1, 0, .25])
        self.assertGreater(math.hypot(*result['output']), 1)
        self.assertEqual(result['state']['flag'], 1)

    def test_signed_zero_and_tiny_input_survive(self):
        result = process_default([-0., 1e-9, 0., -1e-9])['output']
        self.assertEqual(struct.pack('<f', result[0]), bytes.fromhex('00000080'))
        self.assertGreater(result[1], 0)
        self.assertLess(result[3], 0)

    def test_nonzero_flag_preserved_and_state_not_mutated(self):
        state = {'flag': 7, 'stored': [9, 9, 9, 9], 'annotation': {'value': 1}}
        before = copy.deepcopy(state)
        result = process_default([.1, -.2, .3, -.4], state)
        self.assertEqual(result['state']['flag'], 7)
        result['state']['annotation']['value'] = 2
        self.assertEqual(state, before)
        result['output'][0] = 88
        self.assertNotEqual(result['state']['stored'][0], 88)

    def test_repeat_call_replaces_storage_without_filter_history(self):
        first = process_default([1, 0, 0, 0])
        second = process_default([-1, 0, 0, 0], first['state'])
        self.assertEqual(second['output'], [-1, 0, 0, 0])
        self.assertEqual(second['state']['flag'], 1)
        self.assertEqual(initial_state(), {'flag': 0, 'stored': [0., 0., 0., 0.]})

    def test_float32_domain_policy(self):
        for value in ([1, 2, 3], [True, 0, 0, 0], [math.nan, 0, 0, 0], [1e100, 0, 0, 0]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                process_default(value)
        for flag in (True, -1, 256):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                process_default([0, 0, 0, 0], {'flag': flag})


if __name__ == '__main__':
    unittest.main()
