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


class BindingMaskTests(unittest.TestCase):
    def test_only_class_labels_change(self):
        from engine.animation_binding import resolve_binding_masks as masks
        self.assertEqual(masks([0, 1, 2, 3, 4, 65535], [0, 3, 15]),
                         [0, 1, 8, 32768, 4, 65535])

    def test_native_shift_count_and_word_truncation(self):
        from engine.animation_binding import resolve_binding_masks as masks
        self.assertEqual(masks([1, 2, 3], [16, 31, 32]), [0, 0, 1])
        self.assertEqual(masks([1, 2, 3], [65535, 33, 47]), [0, 2, 32768])

    def test_not_an_idempotent_general_mask_normalizer(self):
        from engine.animation_binding import resolve_binding_masks as masks
        first = masks([1], [1, 3, 5])
        self.assertEqual(first, [2])
        self.assertEqual(masks(first, [1, 3, 5]), [8])
        with self.assertRaises(ValueError):
            masks([1], [0, 1])


class ChannelBindingEncodingTests(unittest.TestCase):
    def test_type_groups_and_default_do_not_truncate(self):
        from engine.animation_binding import matching_channel_type as convert
        self.assertEqual([convert(i) for i in range(8)], [6, 5, 5, 5, 0, 2, 3, 1])
        self.assertEqual(convert(8), 8)
        self.assertEqual(convert(255), 8)

    def test_remap_splits_target_and_flags_without_changing_source(self):
        from engine.animation_binding import encode_channel_binding, inspect_channel_binding
        encoded = encode_channel_binding(0x1234, 9, 0x2c52cbb0, True,
                                         remap_word=(37 << 3) | 5)
        self.assertEqual(encoded, {'target_index': 37, 'source_word': 0xd234})
        self.assertEqual(inspect_channel_binding(**encoded),
                         {'target_index': 37, 'source_index': 0x234,
                          'remap_bits': 5, 'special_bit': True})

    def test_second_variant_is_reference_channel_specific(self):
        from engine.animation_binding import encode_channel_binding as encode
        self.assertEqual(encode(7, 65535, 0x58988870, True),
                         {'target_index': 65535, 'source_word': 7})
        self.assertEqual(encode(7, 9, 0x2c52cbb0, False, 65535),
                         {'target_index': 8191, 'source_word': 0x7007})
        with self.assertRaises(ValueError):
            encode(7, 9, 0x2c52cbb0, 1)
