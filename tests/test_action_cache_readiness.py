import unittest
from engine.action_cache_readiness import queried_cache_ready, linked_cache_ready, extended_cache_ready
from engine.action_cache_preference import preferred_input_cache


class CacheReadinessTests(unittest.TestCase):
    def test_query_buffer_and_status(self):
        calls = []
        def query(slot, scratch):
            calls.append((slot, bytes(scratch)))
            scratch[:] = b'x' * 16
            return 0
        self.assertTrue(queried_cache_ready(0xffffffff, query))
        self.assertEqual(calls, [(0xffffffff, bytes(16))])
        for status in (1, 256, 0xffffffff):
            self.assertFalse(queried_cache_ready(0, lambda slot, scratch: status))

    def test_override_bypasses_identity(self):
        self.assertTrue(linked_cache_ready(255, None))
        self.assertFalse(linked_cache_ready(0, 0))
        self.assertTrue(linked_cache_ready(0, 1 << 63))
        self.assertFalse(extended_cache_ready(0))
        self.assertTrue(extended_cache_ready(0xffffffffffffffff))

    def test_preference_composition(self):
        saved = b'P\0\0\0'
        def readiness(index):
            return int(queried_cache_ready(index, lambda slot, scratch: 1 if slot == 0 else 0))
        self.assertEqual(preferred_input_cache(saved, [saved, saved], readiness), 1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            queried_cache_ready(-1, None)
        with self.assertRaises(ValueError):
            queried_cache_ready(0, lambda slot, scratch: -1)
        with self.assertRaises(ValueError):
            linked_cache_ready(256, 0)
