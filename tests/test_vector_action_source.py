import unittest
from engine.vector_action_source import priority_blocks,cached_value,select_vector_source

class VectorSourceTests(unittest.TestCase):
    def test_highest_nonnull_owner_wins(self):
        self.assertFalse(priority_blocks(9,[0]*7))
        self.assertFalse(priority_blocks(9,[0,9,8,0,0,0,0]))
        self.assertTrue(priority_blocks(9,[0,8,9,0,0,0,0]))
    def test_only_last_mask_entry_matters(self):
        raw=bytes(range(16))
        self.assertEqual(cached_value(raw,[]),raw)
        self.assertEqual(cached_value(raw,[4,0]),raw)
        self.assertEqual(cached_value(raw,[0,4]),bytes(16))
    def test_axis_selection_retains_z_w_raw_bits(self):
        raw=bytes(range(16))
        for mode,expected in ((0,raw),(1,raw[:4]+bytes(4)+raw[8:]),(2,raw[4:8]+bytes(4)+raw[8:])):
            self.assertEqual(select_vector_source(1,mode,lambda *a:False,lambda i:raw,None),expected)
    def test_blocking_skips_cache_read_and_unknown_skips_all(self):
        def fail(*args):raise AssertionError('unexpected source read')
        self.assertEqual(select_vector_source(0,0,lambda *a:True,fail,fail),bytes(16))
        self.assertEqual(select_vector_source(0xffffffff,2,fail,fail,fail),bytes(16))
    def test_scalar_channels_and_lazy_order(self):
        for kind,channel in ((2,10),(3,12)):
            calls=[]
            def blocked(family,index):calls.append(('gate',family,index));return False
            def scalar(index):calls.append(('read',index));return b'\xff'*4
            self.assertEqual(select_vector_source(kind,2,blocked,None,scalar),b'\xff'*4+bytes(12))
            self.assertEqual(calls,[('gate','scalar',channel),('read',channel)])
