import struct
import unittest
from engine.pose_paired_point_solver import prepare_pose_paired_point_row,iterate_pose_paired_point_row


class PairedPointTests(unittest.TestCase):
    def fixture(self):
        row=bytearray(176);struct.pack_into('<HHI',row,0,0,1,0)
        struct.pack_into('<4f',row,16,10,0,0,.25)
        for base in (0x20,0x80):
            for i in range(3):struct.pack_into('<4f',row,base+i*16,*[float(i==j) for j in range(4)])
        d=struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1)
        return row,dict(body_data=[bytearray(d),bytearray(d)],body_state=[bytearray(32),bytearray(32)],results=[bytearray(16)])

    def test_coupled_updates_have_opposite_linear_but_coefficient_angular_signs(self):
        row,args=self.fixture();prepare_pose_paired_point_row(row,**args)
        iterate_pose_paired_point_row(row,**args)
        first,second=args['body_state']
        self.assertEqual(struct.unpack_from('<f',first)[0],-.25)
        self.assertEqual(struct.unpack_from('<f',second)[0],.25)
        self.assertEqual(struct.unpack_from('<f',first,16)[0],-.25)
        self.assertEqual(struct.unpack_from('<f',second,16)[0],-.25)

    def test_cached_impulse_applied_at_preparation(self):
        row,args=self.fixture();struct.pack_into('<4f',args['results'][0],0,1,0,0,0)
        prepare_pose_paired_point_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1])[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1],16)[0],1)

    def test_singular_matrix_rejected(self):
        row,args=self.fixture()
        for d in args['body_data']:d[:]=bytes(64)
        with self.assertRaises(ValueError):prepare_pose_paired_point_row(row,**args)
