import struct
import unittest
from engine.pose_link_update import update_pose_link_payload

FRAME=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[1,2,3])


class PayloadUpdateTests(unittest.TestCase):
    def record(self,key=7):
        r=bytearray(48);struct.pack_into('<3fI3fI',r,16,4,6,8,key,9,10,11,123)
        return bytes(r)

    def update(self,p,records):
        return update_pose_link_payload(p,records,first_frame=FRAME,second_frame=FRAME,
                                        first_index=0x10002,second_index=3)

    def test_local_points_cache_match_and_tail(self):
        p=bytearray([0xa5])*288;struct.pack_into('<I',p,0x110,1)
        struct.pack_into('<I',p,0x2c,7);struct.pack_into('<I',p,0x40,0x12345678)
        r=self.update(p,[self.record()])
        self.assertEqual(struct.unpack_from('<3f',r,0x20),(3,4,5))
        self.assertEqual(struct.unpack_from('<3f',r,0x30),(8,8,8))
        self.assertEqual(struct.unpack_from('<IIHH',r,0x40),(0x12345678,0,2,3))
        self.assertEqual(r[0x4c:0x50],p[0x4c:0x50])
        self.assertEqual(r[0x50:0x110],p[0x50:0x110])

    def test_first_duplicate_wins_using_preupdate_snapshot(self):
        p=bytearray(288);struct.pack_into('<I',p,0x110,4)
        for i in range(4):
            struct.pack_into('<I',p,0x2c+64*i,7)
            struct.pack_into('<I',p,0x40+64*i,i+10)
        r=self.update(p,[self.record(99),self.record(7)])
        self.assertEqual(struct.unpack_from('<I',r,0x40)[0],0)
        self.assertEqual(struct.unpack_from('<I',r,0x80)[0],10)

    def test_empty_update_only_clears_count(self):
        p=bytearray([0xa5])*288;r=self.update(p,[])
        p[0x110:0x114]=bytes(4)
        self.assertEqual(r,bytes(p))

    def test_inactive_cached_word_does_not_survive(self):
        p=bytearray(288);struct.pack_into('<I',p,0x2c,7);struct.pack_into('<I',p,0x40,99)
        self.assertEqual(struct.unpack_from('<I',self.update(p,[self.record()]),0x40)[0],0)
