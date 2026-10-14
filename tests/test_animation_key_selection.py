import bisect
import unittest
from engine.animation_key_selection import select_byte_key as select


class ByteKeySelectionTests(unittest.TestCase):
    def test_forward_exact_boundary_and_terminal(self):
        self.assertEqual(select(3, [10,20], 9, 0),
                         {'cursor':0, 'packed_ticks':10<<16, 'path':'forward'})
        self.assertEqual(select(3, [10,20], 10, 0)['packed_ticks'], 10 | 20<<16)
        self.assertEqual(select(3, [10,20], 20, 1),
                         {'cursor':2, 'packed_ticks':20, 'path':'forward'})

    def test_rewind_and_invalid_cursor_use_binary_search(self):
        for cursor in (2, 3, 0xffffffff):
            self.assertEqual(select(3, [10,20], 5, cursor),
                             {'cursor':0, 'packed_ticks':10<<16, 'path':'binary'})

    def test_duplicates_zero_short_counts_and_unsigned_hint(self):
        self.assertEqual(select(4, [0,10,10], 10)['cursor'], 3)
        self.assertEqual(select(4, [0,10,10], 0)['cursor'], 1)
        for count in (0,1):
            self.assertEqual(select(count, [], 0xffffffff),
                             {'cursor':0, 'packed_ticks':0, 'path':'short'})
        self.assertEqual(select(3, [10,20], 0xffffffff)['cursor'], 2)

    def test_cached_and_reset_paths_agree_with_upper_bound(self):
        times = [0,0,1,1,17,128,255]
        for hint in range(257):
            expected = bisect.bisect_right(times, hint)-1
            for cursor in range(len(times)+2):
                self.assertEqual(select(len(times), times[1:], hint, cursor)['cursor'], expected)

    def test_invalid_adapter_inputs(self):
        for args in ((3,[20,10],0), (2,[],0), (2,[256],0), (1,[],-1)):
            with self.assertRaises(ValueError):
                select(*args)


class MaskKeySelectionTests(unittest.TestCase):
    def test_gaps_equality_and_last_key(self):
        from engine.animation_key_selection import select_mask_key as mask
        self.assertEqual(mask(1,bytes([0b00101001]),2),
                         {'cursor':0,'packed_ticks':3<<16,'path':'mask_scan'})
        self.assertEqual(mask(1,bytes([0b00101001]),3)['packed_ticks'],3|(5<<16))
        self.assertEqual(mask(1,bytes([0b00101001]),0xffffffff)['packed_ticks'],5)

    def test_shift_and_byte_boundary_rank(self):
        from engine.animation_key_selection import select_mask_key as mask
        result=mask(0xc2,bytes([1,5]),64)
        self.assertEqual(result['cursor'],1)
        self.assertEqual(result['packed_ticks'],64|(80<<16))

    def test_all_hints_match_expanded_key_oracle(self):
        from engine.animation_key_selection import select_mask_key as mask
        raw=bytes([0b00101001,0b10000001])
        for shift in range(4):
            times=[i<<shift for i in range(16) if (int.from_bytes(raw,'little')>>i)&1]
            for hint in range(130):
                selected=bisect.bisect_right(times,hint)-1
                expected=times[selected]
                if selected+1<len(times):expected|=times[selected+1]<<16
                result=mask((shift<<6)|2,raw,hint)
                self.assertEqual((result['cursor'],result['packed_ticks']),(selected,expected))

    def test_bad_mask_contract(self):
        from engine.animation_key_selection import select_mask_key as mask
        for mode,data in ((0,b''),(1,b'\x02'),(2,b'\x01')):
            with self.assertRaises(ValueError):mask(mode,data,0)
