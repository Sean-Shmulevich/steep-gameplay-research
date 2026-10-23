import unittest
from engine.action_cache_publication import publish_selected_cache, reset_input_cache
from engine.action_cache_exchange import CACHE_SPAN


class CachePublicationTests(unittest.TestCase):
    def test_history_before_copy_and_untouched_fields(self):
        root = bytes([17]) * CACHE_SPAN
        source = bytes([93]) * CACHE_SPAN
        result = publish_selected_cache(root, source)
        self.assertEqual(result[0x10:0x30], root[0x30:0x50])
        for a,b in ((0x30,0x50),(0x168,0x1e8),(0x1f0,0x210)):
            self.assertEqual(result[a:b], source[a:b])
        for a,b in ((0,0x10),(0x50,0x168),(0x1e8,0x1f0),(0x210,CACHE_SPAN)):
            self.assertEqual(result[a:b], root[a:b])

    def test_successive_history_and_self_source(self):
        root = bytes([1]) * CACHE_SPAN
        first = publish_selected_cache(root, bytes([2]) * CACHE_SPAN)
        second = publish_selected_cache(first, bytes([3]) * CACHE_SPAN)
        self.assertEqual(second[0x10:0x30], bytes([2])*32)
        self.assertEqual(second[0x30:0x50], bytes([3])*32)
        same = publish_selected_cache(second, second)
        self.assertEqual(same[0x10:0x30], bytes([3])*32)

    def test_reset_preserves_padding_and_is_idempotent(self):
        original = bytes([255]) * CACHE_SPAN
        reset = reset_input_cache(original)
        self.assertEqual(reset[0x1e8:0x1f0], bytes([255])*8)
        self.assertEqual(reset[0x210:0x7c8], original[0x210:0x7c8])
        self.assertEqual(reset[0x10:0x1e8], bytes(0x1d8))
        self.assertEqual(reset_input_cache(reset), reset)
        self.assertEqual(reset[0x7c8:], bytes(0x50))

    def test_invalid_span(self):
        with self.assertRaises(ValueError): reset_input_cache(b'')
        with self.assertRaises(ValueError): publish_selected_cache(bytes(CACHE_SPAN), b'')
