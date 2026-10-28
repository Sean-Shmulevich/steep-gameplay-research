import struct
import unittest
from engine.pose_link_paired_builder import build_paired_pose_link_rows
from engine.pose_link_feedback import write_pose_link_feedback


class PairedBuilderTests(unittest.TestCase):
    def fixture(self,count=1,soft=False):
        context=dict(primary_count=1,secondary_count=1,result_count=2,
            primary_rows=[bytearray([0xa5]*128) for _ in range(5)],
            secondary_rows=[bytearray([0x5a]*128) for _ in range(9)],
            result_rows=[bytearray([0xcc]*16) for _ in range(16)],
            flags38=0x2000000c,scalar_c=2,factor14=9,field1c=0,field20=0)
        body=dict(frame=dict(basis=((1,0,0),(0,1,0),(0,0,1)),translation=(0,0,0)),
                  offset128=(0,0,0),motion1a0=(1,0,0),motion1ac=(0,0,0),index1c=7,entries=[10])
        payload=bytearray(288);struct.pack_into('<I',payload,0x110,count);payload[0x114]=1
        for i in range(count):
            struct.pack_into('<3f',payload,0x10+i*64,0,0,1)
            struct.pack_into('<3f',payload,0x30+i*64,0,0,2)
            struct.pack_into('<I',payload,0x40+i*64,0x7fc12345+i)
        profile=dict(field30=1,field40=2,field60=4 if soft else 1e14,field64=2)
        args=dict(resources={10:dict(kind28=0,default20=20)},profiles={20:profile},modes={k:0 for k in profile})
        return context,body,payload,args

    def test_row_counts_cache_binding_and_untouched_storage(self):
        c,b,p,args=self.fixture(2)
        build_paired_pose_link_rows(c,b,b,p,**args)
        self.assertEqual((c['primary_count'],c['secondary_count'],c['result_count']),(3,5,8))
        self.assertEqual(c['primary_rows'][0],bytes([0xa5])*128)
        self.assertEqual(c['secondary_rows'][5],bytes([0x5a])*128)
        for i,index in enumerate((2,5)):
            self.assertEqual(struct.unpack_from('<I',p,0x44+i*64)[0],index)
            self.assertEqual(c['result_rows'][index],struct.pack('<I',0x7fc12345+i)*4)
            self.assertEqual(c['primary_rows'][1+i][0x40:0x50],bytes([0xa5])*16)
        self.assertEqual(c['secondary_rows'][1][0x64:0x70],bytes([0x5a])*12)

    def test_soft_gate_leaves_existing_result_storage(self):
        c,b,p,args=self.fixture(soft=True)
        build_paired_pose_link_rows(c,b,b,p,**args)
        self.assertEqual(c['result_rows'][2],bytes([0xcc])*16)
        self.assertEqual(struct.unpack_from('<4f',c['primary_rows'][1],0x60),(.75,)*4)

    def test_builder_to_supplied_result_to_feedback(self):
        c,b,p,args=self.fixture()
        build_paired_pose_link_rows(c,b,b,p,**args)
        # External result, not an invented solver iteration.
        c['result_rows'][2][:]=struct.pack('<4f',3,4,5,6)
        write_pose_link_feedback(c,[1],links={1:dict(flags84=1,payload_count=1,payload_slots=[2])},payloads={2:p})
        self.assertEqual(struct.unpack_from('<f',p,0x40)[0],3)

    def test_zero_count_allocates_no_rows(self):
        c,b,p,args=self.fixture(0)
        build_paired_pose_link_rows(c,b,b,p,**args)
        self.assertEqual((c['primary_count'],c['secondary_count'],c['result_count']),(1,1,2))

    def test_second_body_angular_term_has_secondary_layout(self):
        c,b,p,args=self.fixture()
        build_paired_pose_link_rows(c,b,b,p,**args)
        self.assertEqual(struct.unpack_from('<3f',c['secondary_rows'][1],0x50),(2,0,0))
        self.assertEqual(struct.unpack_from('<I',c['secondary_rows'][1],0x60)[0],2)
        self.assertEqual(struct.unpack_from('<4f',c['secondary_rows'][1],0x70),(1,)*4)
        self.assertEqual(c['primary_rows'][1][0x50:0x58],bytes(8))
        self.assertEqual(c['primary_rows'][1][0x58:0x60],bytes([0xa5])*8)
