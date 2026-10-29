import struct
import unittest
from engine.pose_angular_solver import prepare_pose_angular_row,iterate_pose_angular_row
from engine.pose_link_solve import solve_pose_link_rows


class AngularTests(unittest.TestCase):
    def fixture(self):
        row=bytearray(80);struct.pack_into('<HHI',row,0,0,65535,0)
        struct.pack_into('<4f',row,16,10,0,0,.25)
        data=bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        return row,dict(body_data=[data],body_state=[bytearray(32)],results=[bytearray(16)])

    def test_accumulation_and_unused_second_index(self):
        row,args=self.fixture();prepare_pose_angular_row(row,**args)
        for _ in range(4):iterate_pose_angular_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],-1)
        self.assertEqual(args['body_state'][0][:16],bytes(16))

    def test_trace_zero_rejected(self):
        row,args=self.fixture();args['body_data'][0][:]=bytes(64)
        with self.assertRaises(ValueError):prepare_pose_angular_row(row,**args)

    def test_traversal_normal_and_special(self):
        for flags,expected in [(4,-.25),(0x10010000,0.)]:
            row,args=self.fixture();c=bytearray(0x190)
            struct.pack_into('<I',c,0x138,1);struct.pack_into('<I',c,0x38,flags)
            before=bytes(row)
            solve_pose_link_rows(c,base_token=0,primary_rows=[],secondary_rows=[],angular_rows=[row],**args)
            self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],expected)
            if flags==0x10010000:self.assertEqual(bytes(row),before)
