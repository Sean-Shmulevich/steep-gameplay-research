import struct
import unittest
from engine.action_slot_packet import decode_slot_axes,map_slot_buttons
from engine.action_cache_exchange import CACHE_SPAN


class SlotPacketTests(unittest.TestCase):
    def test_axis_extrema_and_unwritten_lanes(self):
        raw=bytes([17])*CACHE_SPAN;packet=bytearray(16)
        struct.pack_into('<4h',packet,8,-32768,32767,0,-1)
        out=decode_slot_axes(raw,bytes(packet))
        self.assertLess(struct.unpack_from('<f',out,0x1f0)[0],-1)
        self.assertEqual(struct.unpack_from('<f',out,0x1f4)[0],1)
        self.assertEqual(out[0x1f8:0x200],raw[0x1f8:0x200])
        self.assertEqual(out[0x208:0x210],raw[0x208:0x210])

    def test_trigger_threshold_and_shift_wrap(self):
        packet=bytearray(16);packet[4]=1;packet[6]=30;packet[7]=31
        bindings=[(1,11),(1,12),(1,33),(1,17),(0,1)]+[(0,0)]*27
        out=map_slot_buttons(bytes([255])*CACHE_SPAN,bytes(packet),bindings)
        self.assertEqual(out[0x30:0x35],bytes((0,1,1,0,0)))
        self.assertGreater(struct.unpack_from('<f',out,0x168)[0],0)
        self.assertEqual(struct.unpack_from('<f',out,0x170)[0],1)
        self.assertEqual(out[0x35:0x50],bytes(27))

    def test_invalid_packet_and_binding(self):
        with self.assertRaises(ValueError):decode_slot_axes(bytes(CACHE_SPAN),b'')
        with self.assertRaises(ValueError):map_slot_buttons(bytes(CACHE_SPAN),bytes(16),[])
