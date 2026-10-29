import struct
import unittest
from engine.pose_paired_shared_solver import iterate_pose_paired_shared_row
from test_pose_primary_solver import data


class PairedSharedSolverTests(unittest.TestCase):
    def fixture(self,same=False):
        row=bytearray(256);struct.pack_into('<HHI',row,0,0,0 if same else 1,0)
        for offset in (0x20,0xb0):
            for j in range(3):
                v=[0.]*4;v[j]=1.;struct.pack_into('<4f',row,offset+16*j,*v)
        struct.pack_into('<4f',row,0xe0,10,10,10,10)
        struct.pack_into('<4f',row,0xf0,1,1,1,1)
        args=dict(body_data={0:data(),1:data()},body_state={0:bytearray(32),1:bytearray(32)},results={0:bytearray(16)})
        return row,args

    def test_relative_linear_motion_and_opposite_updates(self):
        row,args=self.fixture()
        struct.pack_into('<f',args['body_state'][0],0,-2)
        iterate_pose_paired_shared_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(2,0,0,0))
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],0)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1])[0],-2)
        self.assertEqual(row[0xe0:0xf0],bytes(16))

    def test_coincident_body_updates_accumulate_sequentially(self):
        row,args=self.fixture(True)
        for offset in (0x50,0x80):
            for j in range(3):
                v=[0.]*4;v[j]=1.;struct.pack_into('<4f',row,offset+16*j,*v)
        struct.pack_into('<f',args['body_state'][0],16,-1)
        iterate_pose_paired_shared_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],2)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],3)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],0)

    def test_preparation_combines_both_bodies_and_applies_cached_result(self):
        from engine.pose_paired_shared_solver import prepare_pose_paired_shared_row
        for same in (False,True):
            row,args=self.fixture(same)
            for offset in (0x50,0x80):
                for j in range(3):
                    v=[0.]*4;v[j]=1.;struct.pack_into('<4f',row,offset+16*j,*v)
            args['results'][0][:]=struct.pack('<4f',1,2,3,0)
            prepare_pose_paired_shared_row(row,**args)
            for j in range(3):
                expected=[0.]*4;expected[j]=.25
                self.assertEqual(struct.unpack_from('<4f',row,0xb0+16*j),tuple(expected))
            self.assertEqual(row[0xe0:0xf0],bytes(16))
            if same:
                self.assertEqual(struct.unpack('<8f',args['body_state'][0]),(0,0,0,0,2,4,6,0))
            else:
                self.assertEqual(struct.unpack('<8f',args['body_state'][0]),(1,2,3,0,1,2,3,0))
                self.assertEqual(struct.unpack('<8f',args['body_state'][1]),(-1,-2,-3,0,1,2,3,0))
