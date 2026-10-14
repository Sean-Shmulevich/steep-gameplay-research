import unittest
from engine.animation_resource_index import (
    decode_record_index, publish_in_key_map, needs_release_call)


class AnimationResourceIndexTests(unittest.TestCase):
    def test_index_zero_high_flags_and_block_boundary(self):
        self.assertIsNone(decode_record_index(0xfff80000))
        self.assertEqual(decode_record_index(0xfff80001),
                         {'index': 0, 'block': 0, 'slot': 0,
                          'descriptor_offset': 0, 'entry_offset': 0})
        end = decode_record_index(0x4000)
        start = decode_record_index(0x4001)
        self.assertEqual((end['block'], end['slot'], end['entry_offset']),
                         (0, 16383, 393192))
        self.assertEqual((start['block'], start['slot'], start['descriptor_offset']),
                         (1, 0, 16))
        self.assertEqual(decode_record_index(0x7ffff)['index'], 0x7fffe)

    def test_reserved_range_is_inclusive_and_64_bit(self):
        for key, expected in ((0, True), (0xefffffff, True),
                              (0xf0000000, False), (0xf7ffffff, False),
                              (0xf8000000, True), (0x1f0000000, True),
                              (0xffffffffffffffff, True)):
            with self.subTest(key=key):
                self.assertEqual(publish_in_key_map(key), expected)

    def test_release_ignores_high_flag_byte_but_requires_last_reference(self):
        self.assertTrue(needs_release_call(1, 0xff000000))
        self.assertFalse(needs_release_call(1, 0xff000001))
        for count in (0, 2, 0xffffffff):
            self.assertFalse(needs_release_call(count, 0))

    def test_invalid_integer_domains(self):
        for fn, bad in ((decode_record_index, -1),
                        (decode_record_index, 1 << 32),
                        (decode_record_index, True),
                        (publish_in_key_map, 1 << 64),
                        (publish_in_key_map, 1.0)):
            with self.assertRaises(ValueError):
                fn(bad)


class AnimationResourceLifetimeTests(unittest.TestCase):
    def test_inner_release_rechecks_count_and_blocking_flags(self):
        from engine.animation_resource_index import release_entry_eligible
        self.assertTrue(needs_release_call(1, 0x04000000))
        self.assertFalse(release_entry_eligible(0, 0x04000000))
        self.assertFalse(release_entry_eligible(0, 0x01000000))
        self.assertFalse(release_entry_eligible(1, 0))
        self.assertFalse(release_entry_eligible(0, 1))
        self.assertTrue(release_entry_eligible(0, 0xfa000000))

    def test_index_write_preserves_flags_and_round_trips(self):
        from engine.animation_resource_index import encode_record_index
        for index in (0, 16383, 16384, 0x7fffe):
            word = encode_record_index(0xa5f80000, index)
            self.assertEqual(word & 0xfff80000, 0xa5f80000)
            self.assertEqual(decode_record_index(word)['index'], index)

    def test_index_write_wraps_without_claiming_validity(self):
        from engine.animation_resource_index import encode_record_index
        self.assertIsNone(decode_record_index(encode_record_index(0, 0x7ffff)))
        self.assertEqual(decode_record_index(encode_record_index(0, 0x80000))['index'], 0)
        with self.assertRaises(ValueError):
            encode_record_index(0, -1)


class DeferredAnimationDecisionTests(unittest.TestCase):
    def test_stale_key_does_not_mark_or_dispatch(self):
        from engine.animation_resource_index import deferred_entry_decision
        self.assertEqual(deferred_entry_decision(8, 9, 0x10, has_current_record=True),
                         {'action': 'skip', 'flags': 0x10})

    def test_matching_key_marks_even_without_current_record(self):
        from engine.animation_resource_index import deferred_entry_decision
        self.assertEqual(deferred_entry_decision(8, 8, 0x10, has_current_record=False),
                         {'action': 'mark_only', 'flags': 0x80000010})

    def test_matching_key_dispatches_current_record_without_generation_guard(self):
        from engine.animation_resource_index import deferred_entry_decision
        self.assertEqual(deferred_entry_decision(8, 8, 0x04000000, has_current_record=True),
                         {'action': 'dispatch_current_record', 'flags': 0x84000000})


class ResourcePublicationTests(unittest.TestCase):
    def test_arrival_between_exchange_and_add_stays_staged(self):
        from engine.animation_resource_index import capture_resource_count, publish_resource_count
        taken = capture_resource_count(2)
        staged_after_arrival = taken['remaining_word'] + 1
        published = publish_resource_count(3, taken['captured'])
        self.assertEqual((staged_after_arrival, published['published']), (1, 5))

    def test_publication_after_consumer_capture_waits_for_next_batch(self):
        from engine.animation_resource_index import capture_resource_count, publish_resource_count
        batch = capture_resource_count(2)
        later = publish_resource_count(batch['remaining_word'], 3)
        self.assertEqual(batch['captured'], 2)
        self.assertEqual(later['published'], 3)

    def test_zero_wrap_and_unsigned_capture(self):
        from engine.animation_resource_index import capture_resource_count, publish_resource_count
        self.assertFalse(publish_resource_count(5, 0)['atomic_add_executed'])
        self.assertEqual(publish_resource_count(0xffffffff, 1)['published'], 0)
        self.assertEqual(capture_resource_count(0x80000000)['captured'], 0x80000000)
