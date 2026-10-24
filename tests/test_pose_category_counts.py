import struct
import unittest
from engine.pose_category_counts import count_pose_categories

class PoseCategoryTests(unittest.TestCase):
    def count(self,kind,flags=0,storage=None):
        counts=[0]*25
        count_pose_categories(counts,[1],poses={1:dict(type=kind,second_body=2,storage70=storage)},bodies={2:dict(metadata_flags50=flags)})
        return counts

    def test_simple_types_and_metadata_pairing(self):
        for kind,index in ((1,10),(6,2)):
            for flags,b in ((0,0),(0x8000,1)):
                expected=[0]*25;expected[index+b]=1
                self.assertEqual(self.count(kind,flags),expected)

    def test_type4_and_unknown_do_not_require_body(self):
        for kind in (0,4,7,0xffffffff):
            counts=[0]*25;count_pose_categories(counts,[1],poses={1:dict(type=kind)},bodies={})
            self.assertEqual(sum(counts),int(kind==4))

    def test_type3_word_flag_differs_from_type5_byte_flag(self):
        storage=bytearray(288);storage[0x69]=1
        type3=self.count(3,storage=storage);type5=self.count(5,storage=storage)
        self.assertEqual((type3[22],type3[8],type3[14]),(1,2,1))
        self.assertEqual((type5[10],type5[8],type5[12]),(1,1,0))
        storage[0x68]=2;storage[0x70]=3
        type5=self.count(5,0x8000,storage)
        self.assertEqual((type5[11],type5[9],type5[13]),(1,5,1))

    def test_type2_uses_recovered_six_row_classifier(self):
        storage=bytearray(288)
        for offset in (0x80,0x94,0xa8):struct.pack_into('<f',storage,offset+12,1e14)
        counts=self.count(2,storage=storage)
        self.assertEqual(counts[10],1);self.assertEqual(counts[20],3)

    def test_uint32_accumulation(self):
        counts=[0xffffffff]*25
        count_pose_categories(counts,[1],poses={1:dict(type=4)},bodies={})
        self.assertEqual(counts[24],0);self.assertEqual(counts[0],0xffffffff)
