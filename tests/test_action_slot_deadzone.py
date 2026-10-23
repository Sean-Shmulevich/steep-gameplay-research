import unittest
from engine.action_slot_deadzone import shape_slot_vector


class SlotDeadzoneTests(unittest.TestCase):
    def test_deadzone_remap_and_equality(self):
        self.assertEqual(shape_slot_vector((0.1,0,0,0),0.25),(0,0,0,0))
        self.assertEqual(shape_slot_vector((0.25,0,0,0),0.25),(0,0,0,0))
        self.assertEqual(shape_slot_vector((0.625,0,0,0),0.25),(0.5,0,0,0))
        self.assertEqual(shape_slot_vector((1,0,0,0),0.25),(1,0,0,0))

    def test_all_lanes_and_seed_branch(self):
        seen=[]
        def seed(q):seen.append(q);return 0.5
        self.assertEqual(shape_slot_vector((0,0,0,2),0,rsqrt_estimate=seed),(0,0,0,1))
        self.assertEqual(seen,[4])

    def test_unusual_deadzone_is_not_silently_clamped(self):
        self.assertEqual(shape_slot_vector((0.5,0,0,0),-0.25),(0.5,0,0,0))
        self.assertEqual(shape_slot_vector((1.5,0,0,0),2),(0,0,0,0))
        self.assertEqual(shape_slot_vector((0,0,0,0),0),(0,0,0,0))

    def test_nonfinite_boundary(self):
        with self.assertRaises(ValueError):shape_slot_vector((float('nan'),0,0,0),0)

    def test_underflow_boundary_is_explicit(self):
        with self.assertRaisesRegex(ValueError, 'zero divisor'):
            shape_slot_vector((0,0,0,0),1e-30)

    def test_raw_setter_preserves_nan_payload_and_other_fields(self):
        from engine.action_slot_deadzone import set_cache_deadzone_bits, DEFAULT_DEADZONE_BITS
        raw = bytes([93])*0x818
        bits = bytes.fromhex('0100c07f')
        result = set_cache_deadzone_bits(raw,bits)
        self.assertEqual(result[:0x210],raw[:0x210])
        self.assertEqual(result[0x210:0x214],bits)
        self.assertEqual(result[0x214:],raw[0x214:])
        self.assertEqual(DEFAULT_DEADZONE_BITS,bytes.fromhex('9a99993e'))
