import unittest
from engine.action_cache_selection import select_input_cache

class CacheSelectorTests(unittest.TestCase):
    def test_zero_bypasses_ring_even_if_empty(self):
        self.assertEqual(select_input_cache(0,root=42,current_index=None,record_caches=None),dict(cache=42,record_index=None))
    def test_wrap_before_remainder(self):
        self.assertEqual(select_input_cache(2,root=42,current_index=0xffffffff,record_caches=(10,20,30)),dict(cache=20,record_index=1))
        self.assertEqual(select_input_cache(0xffffffff,root=42,current_index=1,record_caches=(10,20,30))['cache'],10)
    def test_identical_cache_and_zero_pointer_preserved(self):
        self.assertEqual(select_input_cache(1,root=42,current_index=0,record_caches=(42,42))['cache'],42)
        self.assertEqual(select_input_cache(1,root=42,current_index=0,record_caches=(0,))['cache'],0)
        with self.assertRaises(ValueError):select_input_cache(1,root=42,current_index=0,record_caches=())
