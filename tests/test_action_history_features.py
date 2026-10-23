import math
import struct
import unittest
from engine.action_history_features import update_history_features, update_mode3_history
from engine.action_vector_history import update_vector_history


class HistoryFeatureTests(unittest.TestCase):
    def state(self, threshold=1):
        state = bytearray(0x3c0)
        struct.pack_into('<f', state, 0x50, threshold)
        return bytes(state)

    def test_curve_output_is_radians_not_pi_scaled(self):
        result = update_history_features(self.state(), struct.pack('<4f', 0,-1,0,0),
            convert=lambda v:v, curve=lambda x:x)
        self.assertEqual(result['curve_input'], 1)
        mapped = struct.unpack_from('<4f', result['snapshot'], 0x240)
        self.assertAlmostEqual(mapped[0], math.sin(1), places=6)
        self.assertAlmostEqual(mapped[1], math.cos(1), places=6)

    def test_zero_route_converts_second_result_again(self):
        calls=[]
        def convert(value):
            calls.append(value)
            return [value[0]+1, *value[1:]]
        result = update_history_features(self.state(), bytes(16), convert=convert,
            curve=lambda _:self.fail('zero route called curve'))
        self.assertEqual(calls, [[0]*4, [0]*4, [1,0,0,0]])
        self.assertEqual(struct.unpack_from('<f', result['snapshot'], 0x240)[0], 2)

    def test_conversion_does_not_replace_threshold_input(self):
        result = update_history_features(self.state(.5), struct.pack('<4f', 1,0,0,0),
            convert=lambda _: [0,1,0,0], curve=lambda x:x)
        self.assertAlmostEqual(result['curve_input'], .5, places=6)

    def test_complete_mode3_composition_rotates_features_but_not_raw_history(self):
        result = update_mode3_history(self.state(), struct.pack('<4f', 0,2,0,0),
            now=45, primary=[1,0,0,0], secondary=[0,1,0,0], curve=lambda x:x)
        state = result['snapshot']
        self.assertEqual(struct.unpack_from('<4f', state, 0x60), (0,2,0,0))
        self.assertAlmostEqual(struct.unpack_from('<f', state, 0x100)[0], 1, places=6)
        self.assertAlmostEqual(struct.unpack_from('<f', state, 0x240)[0], 1, places=6)
        self.assertEqual(struct.unpack_from('<Q', state)[0], 45)
        self.assertEqual(struct.unpack_from('<f', state, 0x2e0)[0], 1)
        self.assertEqual(result['conversion_mode'], 3)

    def test_composes_with_outer_history_and_preserves_unrelated_fields(self):
        initial = self.state()
        def features(state, raw):
            return update_history_features(state, raw, convert=lambda v:v, curve=lambda x:x)['snapshot']
        result = update_vector_history(initial, struct.pack('<4f', 3,4,0,0), now=77, update_features=features)
        self.assertEqual(struct.unpack_from('<Q', result)[0], 77)
        self.assertEqual(struct.unpack_from('<4f', result, 0x60), (3,4,0,0))
        self.assertEqual(struct.unpack_from('<f', result, 0x2e0)[0], 1)
        self.assertEqual(result[0x308:], initial[0x308:])
        second = update_vector_history(result, bytes(16), now=78, update_features=features)
        self.assertEqual(second[0x110:0x120], result[0x100:0x110])


if __name__ == '__main__': unittest.main()
