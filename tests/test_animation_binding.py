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


class TypedChannelLookupTests(unittest.TestCase):
    def test_duplicate_hashes_and_first_matching_type(self):
        from engine.animation_binding import find_typed_channel as find
        hashes = [0, 0, 0, 7, 7, 0xffffffff]
        raw = [0, 4, 1, 0, 2, 255]
        self.assertEqual(find(hashes, raw, 0, 5), 2)
        self.assertEqual(find(hashes, raw, 7, 5), 4)
        self.assertEqual(find(hashes, raw, 0xffffffff, 8), 5)
        self.assertEqual(find([0, 0], [1, 2], 0, 5), 0)

    def test_absence_and_hash_group_boundary(self):
        from engine.animation_binding import find_typed_channel as find
        self.assertEqual(find([], [], 0, 5), 65535)
        self.assertEqual(find([0, 1], [0, 1], 0, 5), 65535)
        self.assertEqual(find([0, 9], [1, 1], 8, 5), 65535)
        self.assertEqual(find([0], [1], 0, 9), 65535)

    def test_binding_absence_differs_from_missing_binding_channel(self):
        from engine.animation_binding import select_endpoint_channels as select
        data = {'hashes': [0, 0], 'descriptor_types': [1, 0]}
        self.assertEqual(select(**data), (0, 1))
        self.assertEqual(select((0xffff, 0xa123), **data), (None, 0x123))
        self.assertEqual(select((0xfff, 0xfff), **data), (None, None))

    def test_api_rejects_invalid_resource_contract(self):
        from engine.animation_binding import find_typed_channel as find
        for hashes, raw in [([7, 0], [1, 0]), ([0], []), ([True], [1]),
                            ([0], [256])]:
            with self.assertRaises(ValueError):
                find(hashes, raw, 0, 5)


class ChannelRoutingTests(unittest.TestCase):
    def test_special_hashes_and_wrapping_range(self):
        from engine.animation_binding import alternate_channel_candidate as candidate
        from engine.animation_binding import ORDINARY_CHANNEL_HASHES
        for value in ORDINARY_CHANNEL_HASHES:
            self.assertFalse(candidate(0, 1, [value]))
        for value in (0xffffffda, 0xffffffe3):
            self.assertFalse(candidate(0, 1, [value]))
        for value in (0xffffffd9, 0xffffffe4, 0xffffffff, 1):
            self.assertTrue(candidate(0, 1, [value]))

    def test_missing_metadata_is_not_a_validity_check(self):
        from engine.animation_binding import alternate_channel_candidate as candidate
        self.assertTrue(candidate(0, 1, None))
        self.assertTrue(candidate(1, 1, []))
        with self.assertRaises(ValueError):
            candidate(0, 1, [])

    def test_route_requires_both_gates_and_hash_zero_stays_ordinary(self):
        from engine.animation_binding import channel_sample_route as route
        for flags, present, expected in ((0, True, 'ordinary'),
                                        (8, False, 'ordinary'),
                                        (8, True, 'alternate')):
            self.assertEqual(route(0, 1, resource_flags=flags,
                                   alternate_present=present, hashes=[1]), expected)
        self.assertEqual(route(0, 1, resource_flags=8,
                               alternate_present=True, hashes=[0]), 'ordinary')
