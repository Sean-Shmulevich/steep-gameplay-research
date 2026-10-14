import unittest
from engine.animation_binding import swap_binding_indices


class BindingIndexSwapTests(unittest.TestCase):
    def test_indices_exchange_but_flags_stay_with_slots(self):
        original = [0xa123, 0xb456]
        swapped = swap_binding_indices(original, [(0, 1)])
        self.assertEqual(swapped, [0xa456, 0xb123])
        self.assertEqual(original, [0xa123, 0xb456])
        self.assertEqual(swap_binding_indices(swapped, [(0, 1)]), original)

    def test_sentinel_alias_and_ordered_overlapping_pairs(self):
        words = [0xa001, 0xb002, 0xc003]
        self.assertEqual(swap_binding_indices(words, [(0xffff, 2), (1, 1)]), words)
        self.assertEqual(swap_binding_indices(words, [(0, 1), (1, 2)]),
                         [0xa002, 0xb003, 0xc001])
        self.assertNotEqual(swap_binding_indices(words, [(1, 2), (0, 1)]),
                            swap_binding_indices(words, [(0, 1), (1, 2)]))

    def test_adapter_rejects_invalid_native_memory_requests(self):
        for words, pairs in [([0x10000], []), ([0], [(0, 1)]),
                             ([0], [(-1, 0)]), ([True], [])]:
            with self.assertRaises(ValueError):
                swap_binding_indices(words, pairs)
