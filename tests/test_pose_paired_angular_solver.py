import struct
import unittest
from engine.pose_paired_angular_solver import prepare_pose_paired_angular_row,iterate_pose_paired_angular_row


class PairedAngularTests(unittest.TestCase):
    def fixture(self,same=False):
        row=bytearray(80);struct.pack_into('<HHI',row,0,0,0 if same else 1,0)
        struct.pack_into('<4f',row,16,10,0,0,.25)
        data=[bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1)) for _ in range(2)]
        return row,dict(body_data=data,body_state=[bytearray(32),bytearray(32)],results=[bytearray(16)])

    def test_increment_cap_does_not_cap_accumulated_result(self):
        row,args=self.fixture();prepare_pose_paired_angular_row(row,**args)
        for _ in range(4):iterate_pose_paired_angular_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],-1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1],16)[0],1)
        self.assertEqual(args['body_state'][0][:16],bytes(16))

    def test_coincident_endpoints_apply_opposite_updates_sequentially(self):
        row,args=self.fixture(True)
        struct.pack_into('<4f',args['results'][0],0,1,2,3,0)
        prepare_pose_paired_angular_row(row,**args)
        self.assertEqual(args['body_state'][0],bytes(32))
        iterate_pose_paired_angular_row(row,**args)
        self.assertEqual(args['body_state'][0],bytes(32))
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],.75)

    def test_singular_response_is_explicit(self):
        row,args=self.fixture()
        for d in args['body_data']:d[:]=bytes(64)
        with self.assertRaises(ValueError):prepare_pose_paired_angular_row(row,**args)
