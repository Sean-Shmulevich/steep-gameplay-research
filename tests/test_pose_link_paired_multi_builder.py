import struct
import unittest
import test_pose_link_builder as fixtures
from engine.pose_link_paired_multi_builder import build_paired_multi_pose_link_rows


class PairedMultiBuilderTests(unittest.TestCase):
    def fixture(self,soft=False):
        c,b,p,args=fixtures.BuilderTests().fixture(2,soft)
        c['primary_rows']=[bytearray([0xa5]*128) for _ in range(5)]
        c.update(shared_count=1,shared_rows=[bytearray([0x5a]*256) for _ in range(3)],
                 primary_base=0x4000,shared_base=0x1000)
        for i,value in enumerate((2.,3.)):struct.pack_into('<f',p,0x40+64*i,value)
        return c,b,p,args

    def test_shared_result_reserved_before_contacts_and_relative_links(self):
        c,b,p,args=self.fixture()
        build_paired_multi_pose_link_rows(c,b,b,p,**args)
        self.assertEqual((c['primary_count'],c['shared_count'],c['result_count']),(3,2,5))
        self.assertEqual(struct.unpack_from('<I',c['shared_rows'][1],4)[0],2)
        self.assertEqual(c['result_rows'][2],bytes([0xcc]*16))
        self.assertEqual(struct.unpack_from('<4f',c['shared_rows'][1],0xe0),(5,)*4)
        for i,value in enumerate((2.,3.)):
            row=c['primary_rows'][1+i]
            self.assertEqual(struct.unpack_from('<I',p,0x44+64*i)[0],3+i)
            self.assertEqual(c['result_rows'][3+i],struct.pack('<4f',*([value]*4)))
            relative=struct.unpack_from('<q',row,0x50)[0]
            self.assertLess(relative,0)
            self.assertEqual(c['primary_base']+128*(1+i)+16*relative,c['shared_base']+256+0xe0)
        self.assertEqual(c['shared_rows'][1][0xb0:0xe0],bytes([0x5a]*48))
        self.assertEqual(c['shared_rows'][2],bytes([0x5a]*256))

    def test_soft_contacts_still_accumulate_but_do_not_seed_results(self):
        c,b,p,args=self.fixture(True)
        build_paired_multi_pose_link_rows(c,b,b,p,**args)
        self.assertEqual(c['result_rows'][3],bytes([0xcc]*16))
        self.assertEqual(c['result_rows'][4],bytes([0xcc]*16))
        self.assertEqual(struct.unpack_from('<4f',c['shared_rows'][1],0xe0),(5,)*4)
        self.assertEqual(struct.unpack_from('<4f',c['primary_rows'][1],0x60),(.75,)*4)

    def test_second_body_motion_changes_patch_orientation(self):
        import copy
        c,b,p,args=self.fixture()
        other=copy.deepcopy(b);other['motion1a0']=(0,1,0)
        build_paired_multi_pose_link_rows(c,b,other,p,**args)
        first=[struct.unpack_from('<f',c['shared_rows'][1],0x20+16*j)[0] for j in range(3)]
        self.assertLess(first[0],0)
        self.assertLess(first[1],0)
        self.assertAlmostEqual(first[0],first[1])
        self.assertEqual(c['primary_rows'][1][0x40:0x50],bytes([0xa5]*16))
