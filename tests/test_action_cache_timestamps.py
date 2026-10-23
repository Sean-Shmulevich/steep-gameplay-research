import struct
import unittest
from engine.action_cache_exchange import CACHE_SPAN
from engine.action_cache_publication import publish_selected_cache
from engine.action_cache_timestamps import stamp_input_cache


class CacheTimestampTests(unittest.TestCase):
    def test_edges_and_preservation_in_both_arrays(self):
        raw = bytearray([73])*CACHE_SPAN
        for current, previous, stamps in ((0x30,0x10,0x60),(0x7c8,0x7d0,0x7d8)):
            raw[current:current+4] = bytes((1,255,0,2))
            raw[previous:previous+4] = bytes((0,1,1,0))
        result = stamp_input_cache(bytes(raw), 123)
        expected = bytearray(raw)
        expected[0x50:0x58] = raw[0x58:0x60]
        struct.pack_into('<Q', expected, 0x58, 123)
        for stamps in (0x60,0x7d8):
            for index in (0,3):struct.pack_into('<Q', expected, stamps+8*index,123)
        self.assertEqual(result, bytes(expected))

    def test_publication_press_hold_release_repress(self):
        root = bytes(CACHE_SPAN)
        for now, value, expected_stamp in ((10,1,10),(20,255,10),(30,0,10),(40,2,40)):
            device = bytearray(CACHE_SPAN);device[0x30]=value
            previous_clock = struct.unpack_from('<Q', root, 0x58)[0]
            root = stamp_input_cache(publish_selected_cache(root,bytes(device)), now)
            self.assertEqual(struct.unpack_from('<Q',root,0x60)[0],expected_stamp)
            self.assertEqual(struct.unpack_from('<Q',root,0x50)[0],previous_clock)

    def test_clock_can_decrease_and_use_full_uint64(self):
        root = bytearray(CACHE_SPAN);root[0x30]=1
        struct.pack_into('<Q',root,0x58,0xffffffffffffffff)
        stamped=stamp_input_cache(bytes(root),0)
        self.assertEqual(struct.unpack_from('<Q',stamped,0x50)[0],0xffffffffffffffff)
        self.assertEqual(struct.unpack_from('<Q',stamped,0x60)[0],0)

    def test_invalid(self):
        with self.assertRaises(ValueError):stamp_input_cache(b'',0)
        with self.assertRaises(ValueError):stamp_input_cache(bytes(CACHE_SPAN),-1)
