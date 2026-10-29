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
