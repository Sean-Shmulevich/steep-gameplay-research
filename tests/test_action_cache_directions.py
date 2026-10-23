import struct
import unittest
from engine.action_cache_directions import derive_input_directions, publish_derived_and_stamp, DIRECTION_THRESHOLD
from engine.action_cache_exchange import CACHE_SPAN


def cache(x,y,z=0,w=0):
    data=bytearray(CACHE_SPAN)
    struct.pack_into('<4f',data,0x1f0,x,y,z,w)
    return bytes(data)


class CacheDirectionsTests(unittest.TestCase):
    def test_threshold_ties_axes_and_unused_lanes(self):
        for x,y,slot in ((0,-1,0),(-1,0,1),(0,1,2),(1,0,3),(1,1,2),(-1,-1,0)):
            expected=bytearray(8);expected[slot]=1
            self.assertEqual(derive_input_directions(cache(x,y))[0x7c8:0x7d0],bytes(expected))
        self.assertEqual(derive_input_directions(cache(DIRECTION_THRESHOLD,0,99,99))[0x7c8:0x7d0],bytes(8))

    def test_history_and_two_vectors(self):
        raw=bytearray(cache(1,0));raw[0x7c8:0x7d0]=bytes(range(8))
        struct.pack_into('<2f',raw,0x200,0,-1)
        result=derive_input_directions(bytes(raw))
        self.assertEqual(result[0x7d0:0x7d8],bytes(range(8)))
        self.assertEqual(result[0x7c8:0x7d0],bytes((0,0,0,1,1,0,0,0)))
        self.assertEqual(result[:0x7c8],raw[:0x7c8])

    def test_nan_branch_outcomes(self):
        # Strong X enters, unordered X/Y comparison chooses Y, NaN sign test false.
        self.assertEqual(derive_input_directions(cache(1,float('nan')))[0x7c8],1)
        self.assertEqual(derive_input_directions(cache(float('nan'),0))[0x7c8:0x7d0],bytes(8))

    def test_composed_direction_switch_and_hold(self):
        root=bytes(CACHE_SPAN)
        for now,x,y in ((10,1,0),(20,1,0),(30,0,1),(40,1,0)):
            root=publish_derived_and_stamp(root,cache(x,y),now)
            stamp=struct.unpack_from('<Q',root,0x7d8+8*3)[0]
            self.assertEqual(stamp,40 if now==40 else 10)
        self.assertEqual(struct.unpack_from('<Q',root,0x7d8+8*2)[0],30)

    def test_invalid_span(self):
        with self.assertRaises(ValueError):derive_input_directions(b'')
