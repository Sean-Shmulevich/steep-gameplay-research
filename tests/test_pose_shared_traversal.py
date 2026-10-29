import struct
import unittest
from engine.pose_link_solve import solve_pose_link_rows
from test_pose_primary_solver import data


class SharedTraversalTests(unittest.TestCase):
    def fixture(self,special=False):
        c=bytearray(0x190);arena=bytearray(1024)
        struct.pack_into('<I',c,0x38,0x10010000 if special else 4)
        for offset,value in ((0x108,1),(0x118,1),(0x16c,256),(0x50,16)):
            struct.pack_into('<I',c,offset,value)
        primary=memoryview(arena)[256:368];shared=memoryview(arena)[512:720]
        struct.pack_into('<4f',primary,0x10,-2,-2,-2,-2)
        struct.pack_into('<4f',primary,0x20,0,0,1,0)
        struct.pack_into('<q',primary,0x50,(512+0xb0-256)//16)
        struct.pack_into('<I',shared,4,1)
        struct.pack_into('<4f',shared,0x20,1,0,0,0)
        struct.pack_into('<4f',shared,0x30,0,1,0,0)
        struct.pack_into('<4f',shared,0x70,0,0,1,0)
        struct.pack_into('<4f',shared,0xc0,1,1,1,1)
        state=bytearray(32);struct.pack_into('<f',state,0,-3)
        args=dict(base_token=0,primary_rows=[primary],secondary_rows=[],shared_rows=[shared],
                  arena=arena,body_data={0:data()},body_state={0:state},results=[bytearray(16),bytearray(16)])
        return c,args

    def test_primary_accumulation_precedes_shared_projection(self):
        c,args=self.fixture();solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][0]),(-1,0,2))
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(2,0,0,0))
        self.assertEqual(args['shared_rows'][0][0xb0:0xc0],bytes(16))

    def test_special_phase_skips_shared_but_retains_primary_accumulation(self):
        c,args=self.fixture(True);solve_pose_link_rows(c,**args)
        self.assertEqual(struct.unpack_from('<3f',args['body_state'][0]),(-3,0,2))
        self.assertEqual(args['results'][1],bytes(16))
        self.assertEqual(struct.unpack_from('<4f',args['shared_rows'][0],0xb0),(2,)*4)
