import struct
import unittest
from engine.pose_link_record import decode_payload_row,pack_link_key,remove_link_key


class LinkRecordTests(unittest.TestCase):
    def test_row_lane_order_and_retained_tail(self):
        src=bytes(range(60));out=decode_payload_row(src,bytes([255])*64)
        self.assertEqual(out[:16],src[24:40])
        self.assertEqual(out[0x10:0x1c],src[:12])
        self.assertEqual(out[0x1c:0x20],src[56:60])
        self.assertEqual(out[0x20:0x2c],src[12:24])
        self.assertEqual(out[0x2c:0x30],src[52:56])
        self.assertEqual(out[0x30:0x38],src[40:48])
        self.assertEqual(out[0x38:0x3c],src[48:52])
        self.assertEqual(out[0x3c:],bytes([255])*4)

    def test_last_duplicate_removed_and_tail_retained(self):
        a=struct.pack('<QQ',pack_link_key(1,2,3),10)
        b=struct.pack('<QQ',pack_link_key(1,2,3),20)
        c=struct.pack('<QQ',pack_link_key(4,5,6),30)
        d=dict(count=3,slots=[a,b,c])
        self.assertTrue(remove_link_key(d,1,2,3))
        self.assertEqual(d,dict(count=2,slots=[a,c,c]))
        self.assertFalse(remove_link_key(d,7,8,9))

    def test_native_width_truncation(self):
        self.assertEqual(pack_link_key(0x10001,0x20002,0x100000003),pack_link_key(1,2,3))
        self.assertEqual(pack_link_key(-1,-1,-1),0xffffffffffffffff)
