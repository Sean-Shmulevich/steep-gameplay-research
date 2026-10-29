import struct
import unittest
from engine.pose_point_solver import prepare_pose_point_row,iterate_pose_point_row
from engine.pose_link_solve import solve_pose_link_rows


class PointTests(unittest.TestCase):
    def fixture(self):
        row=bytearray(128);struct.pack_into('<HHI',row,0,0,65535,0)
        struct.pack_into('<4f',row,16,10,0,0,.25)
        for i in range(3):struct.pack_into('<4f',row,0x20+i*16,*[float(i==j) for j in range(4)])
        d=bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        return row,dict(body_data=[d],body_state=[bytearray(32)],results=[bytearray(16)])

    def test_linear_and_angular_updates_accumulate(self):
        row,args=self.fixture();prepare_pose_point_row(row,**args)
        for _ in range(4):iterate_pose_point_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],-1)

    def test_normal_traversal_runs_and_special_preserves(self):
        for flags,value in [(4,-.25),(0x10010000,0.)]:
            row,args=self.fixture();c=bytearray(0x190);before=bytes(row)
            struct.pack_into('<I',c,0x130,1);struct.pack_into('<I',c,0x38,flags)
            solve_pose_link_rows(c,base_token=0,primary_rows=[],secondary_rows=[],point_rows=[row],**args)
            self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],value)
            if flags==0x10010000:self.assertEqual(bytes(row),before)

    def test_zero_trace_rejected(self):
        row,args=self.fixture();args['body_data'][0][:]=bytes(64)
        with self.assertRaises(ValueError):prepare_pose_point_row(row,**args)
