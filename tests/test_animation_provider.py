import unittest
from engine.animation_provider import (
    Handle, Row, Provider, Wrapper, Outputs, select_replacement)


class ProviderLookupTests(unittest.TestCase):
    def test_primary_wins_without_calling_availability(self):
        original, replacement = Handle(7), Handle(8)
        outputs = Outputs()
        def forbidden(_):
            self.fail('primary must bypass wrapper availability')
        selected = select_replacement(
            Provider([Row(7, 0x7fc01234, 9, True, replacement)]),
            [Wrapper(None)], original, outputs, forbidden)
        self.assertIs(selected, replacement)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (0x7fc01234, 9))

    def test_failed_matching_rows_keep_outputs_and_original_identity(self):
        original = Handle(7)
        outputs = Outputs(1, 2)
        selected = select_replacement(
            Provider([Row(7, 3, 4, False, Handle(8))]),
            [None, Wrapper(Provider([Row(9, 5, 6, True, Handle(10))])),
             Wrapper(Provider([Row(7, 11, 12, False, Handle(13))]))],
            original, outputs, lambda _: True)
        self.assertIs(selected, original)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (11, 12))

    def test_duplicate_keys_continue_and_first_available_wins(self):
        original, replacement = Handle(7), Handle(8)
        outputs = Outputs()
        provider = Provider([Row(7, 1, 2, False, Handle(9)),
                             Row(7, 3, 4, True, replacement),
                             Row(7, 5, 6, True, Handle(10))])
        self.assertIs(select_replacement(None, [Wrapper(provider)], original,
                                         outputs, lambda _: True), replacement)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (3, 4))

    def test_rejected_and_null_wrappers_do_not_reset_outputs(self):
        original = Handle(7)
        outputs = Outputs(0x80000000, 255)
        provider = Provider([Row(7, 1, 2, True, Handle(8))])
        calls = []
        def reject(pointer):
            calls.append(pointer)
            return False
        self.assertIs(select_replacement(None, [None, Wrapper(provider),
                           Wrapper(None, 0x80000000)], original, outputs, reject),
                      original)
        self.assertEqual(calls, [provider])
        self.assertEqual((outputs.scalar_bits, outputs.flag), (0x80000000, 255))

    def test_callback_pointer_replacement_is_observed(self):
        original, replacement = Handle(7), Handle(8)
        old = Provider([])
        new = Provider([Row(7, 1, 2, True, replacement)])
        wrapper = Wrapper(old)
        def swap(pointer):
            self.assertIs(pointer, old)
            wrapper.pointer = new
            return True
        self.assertIs(select_replacement(None, [wrapper], original, Outputs(),
                                         swap), replacement)
        wrapper.control_word = 0x80000000
        self.assertIs(select_replacement(None, [wrapper], original, Outputs(),
                            lambda _: self.fail('sign bit bypasses callback')),
                      replacement)


class TaggedEndpointTests(unittest.TestCase):
    def test_first_duplicate_and_missing_tag(self):
        from engine.animation_provider import tagged_endpoint
        records = [(2, 240), (2, 480), (3, 120)]
        self.assertEqual(tagged_endpoint(records, 2, 10.0), (True, 2.0))
        self.assertEqual(tagged_endpoint(records, 4, 10.0), (False, 0.0))

    def test_limit_and_unsigned_encoding_boundaries(self):
        from engine.animation_provider import tagged_endpoint
        import struct
        f32 = lambda x: struct.unpack('<f', struct.pack('<f', x))[0]
        self.assertEqual(tagged_endpoint([(255, 65535)], 255, 1000.0),
                         (True, f32(65535 / 120)))
        self.assertEqual(tagged_endpoint([(1, 121)], 1, 1.0), (True, 1.0))
        self.assertEqual(tagged_endpoint([(1, 0)], 1, -1.0), (True, -1.0))

    def test_minss_nan_and_equal_zero_choose_decoded_source(self):
        from engine.animation_provider import tagged_endpoint
        import math
        self.assertEqual(tagged_endpoint([(1, 120)], 1, float('nan')), (True, 1.0))
        found, value = tagged_endpoint([(1, 0)], 1, -0.0)
        self.assertTrue(found)
        self.assertEqual(math.copysign(1, value), 1)


class PlaybackRangeTests(unittest.TestCase):
    def test_equal_backoff_and_invalid_range_reset(self):
        from engine.animation_provider import resolve_playback_range as resolve
        result = resolve(10, 2, 2, True, 0.25)
        self.assertEqual(result, {'start': 1.75, 'end': 2.0,
                                 'start_tick': 210, 'end_tick': 240})
        self.assertEqual(resolve(10, 3, 2, True), resolve(10, 0, 0, False))
        self.assertEqual(resolve(10, 2, 2, True, 0)['end'], 10)

    def test_near_zero_end_and_equal_branch_precedence(self):
        from engine.animation_provider import resolve_playback_range as resolve
        self.assertEqual(resolve(10, 1, 0.000001, True)['end'], 10)
        # Equal-range branch wins over near-zero-end substitution.
        result = resolve(10, 0.000001, 0.000001, True, 0.000001)
        self.assertLess(result['end'], 0.00001)
        self.assertEqual(result['start'], 0.0)

    def test_tick_rounding_wrapping_and_finite_contract(self):
        from engine.animation_provider import resolve_playback_range as resolve
        self.assertEqual(resolve(1000, 0, 1000, True)['end_tick'], 120000 & 65535)
        self.assertEqual(resolve(10, 0.006, 1, True)['start_tick'], 1)
        with self.assertRaises(ValueError):
            resolve(float('nan'), 0, 0, False)


class TimestampCursorTests(unittest.TestCase):
    def test_reset_and_advance_at_duplicate_boundary(self):
        from engine.animation_provider import timestamp_cursor as cursor
        times = [0, 120, 120, 240]
        self.assertEqual(cursor(times, 1.0), 0)
        self.assertEqual(cursor(times, 1.0, previous=0), 2)
        self.assertEqual(cursor(times, 0.0), -1)
        self.assertEqual(cursor(times, 0.0, previous=-1), 0)

    def test_reset_exhaustion_and_empty_are_not_last_index(self):
        from engine.animation_provider import timestamp_cursor as cursor
        self.assertEqual(cursor([0, 120], 2.0), 2)
        self.assertEqual(cursor([], 0.0), 0)
        self.assertEqual(cursor([], 0.0, previous=-1), -1)

    def test_forward_path_does_not_rewind(self):
        from engine.animation_provider import timestamp_cursor as cursor
        self.assertEqual(cursor([0, 120, 240], 0.0, previous=1), 1)
        self.assertEqual(cursor([0, 120], 1.0, previous=0xffffffff), 1)


class TimestampDispatchGateTests(unittest.TestCase):
    def test_boundary_shift_and_independent_permission_bits(self):
        from engine.animation_provider import event_dispatch_allowed as gate
        self.assertFalse(gate(241, 120, 200, 2, 0))
        self.assertTrue(gate(241, 120, 200, 2, 4))
        self.assertFalse(gate(241, 120, 120, 2, 4))
        self.assertTrue(gate(241, 120, 120, 2, 6))

    def test_metadata_absence_and_exact_mode_one(self):
        from engine.animation_provider import event_dispatch_allowed as gate
        self.assertTrue(gate(240, 120, 120, 1, None))
        self.assertFalse(gate(100, 0, 120, 1, 0))
        self.assertTrue(gate(100, 0, 120, 1, 1))
        self.assertTrue(gate(100, 0, 120, 2, 0))

    def test_payload_and_recipient_gates(self):
        from engine.animation_provider import event_dispatch_allowed as gate
        self.assertFalse(gate(100, 0, 120, 0))
        for option in ({'payload_present': False},
                       {'payload_resource_present': False},
                       {'recipient_present': False}, {'blocked': True}):
            self.assertFalse(gate(100, 0, 120, 2, 7, **option))
