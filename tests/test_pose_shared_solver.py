import struct
import unittest
from engine.pose_shared_solver import iterate_pose_shared_row
from test_pose_primary_solver import data


class SharedSolverTests(unittest.TestCase):
    def fixture(self,limits):
        row=bytearray(208)
        for offset in (0x20,0x80):
            for j in range(3):
                v=[0.]*4;v[j]=1.;struct.pack_into('<4f',row,offset+16*j,*v)
        struct.pack_into('<4f',row,0xb0,1,1,1,1)
        struct.pack_into('<4f',row,0xc0,*limits)
        state=bytearray(32);struct.pack_into('<4f',state,0,-3,-4,0,0)
        args=dict(body_data={0:data()},body_state={0:state},results={0:bytearray(16)})
        return row,args

    def test_vector_projection_and_accumulator_consumption(self):
        row,args=self.fixture([2.5]*4)
        iterate_pose_shared_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(1.5,2,0,0))
        self.assertEqual(struct.unpack_from('<4f',args['body_state'][0]),(-1.5,-2,0,0))
        self.assertEqual(row[0xb0:0xc0],bytes(16))
        iterate_pose_shared_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(0,0,0,0))
        self.assertEqual(struct.unpack_from('<4f',args['body_state'][0]),(-3,-4,0,0))

    def test_all_three_limits_must_be_strictly_below_length(self):
        for limits in ([2,5,2,2],[2,6,2,2]):
            row,args=self.fixture(limits)
            iterate_pose_shared_row(row,**args)
            self.assertEqual(struct.unpack('<4f',args['results'][0]),(3,4,0,0))

    def test_prepare_builds_response_and_applies_cached_result(self):
        from engine.pose_shared_solver import prepare_pose_shared_row
        row,args=self.fixture([1]*4)
        args['body_state'][0][:]=bytes(32)
        args['results'][0][:]=struct.pack('<4f',1,2,3,0)
        for j in range(3):
            axis=[0.]*4;axis[j]=1;struct.pack_into('<4f',row,0x50+16*j,*axis)
        prepare_pose_shared_row(row,**args)
        for j in range(3):
            expected=[0.]*4;expected[j]=.5
            self.assertEqual(struct.unpack_from('<4f',row,0x80+16*j),tuple(expected))
        self.assertEqual(struct.unpack('<8f',args['body_state'][0]),(1,2,3,0,1,2,3,0))
        self.assertEqual(row[0xb0:0xc0],bytes(16))

    def test_prepare_rejects_unresolved_singular_response(self):
        from engine.pose_shared_solver import prepare_pose_shared_row
        row,args=self.fixture([1]*4)
        row[0x20:0x80]=bytes(96)
        with self.assertRaises(ValueError):prepare_pose_shared_row(row,**args)
