import struct
import unittest
from engine.pose_paired_primary_solver import prepare_pose_paired_primary_row,iterate_pose_paired_primary_row
from engine.pose_link_solve import solve_pose_link_rows


def fixture(second=1):
    row=bytearray(144);struct.pack_into('<HHI',row,0,0,second,0)
    struct.pack_into('<4f',row,0x10,-2,-2,-2,-2)
    struct.pack_into('<4f',row,0x20,1,0,0,0)
    data=[bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1)) for _ in range(2)]
    state=[bytearray(32) for _ in range(2)];results=[bytearray(16)]
    return row,dict(body_data=data,body_state=state,results=results)


class PairedPrimaryTests(unittest.TestCase):
    def test_opposed_linear_updates_and_nonnegative_result(self):
        row,args=fixture();prepare_pose_paired_primary_row(row,**args)
        self.assertEqual(struct.unpack_from('<4f',row,0x40),(-.5,)*4)
        iterate_pose_paired_primary_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(1,)*4)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],1)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1])[0],-1)
        iterate_pose_paired_primary_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(1,)*4)

    def test_coincident_index_second_write_wins(self):
        row,args=fixture(0);struct.pack_into('<4f',args['results'][0],0,2,2,2,2)
        prepare_pose_paired_primary_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],-2)

    def test_optional_accumulator_and_singular_rejection(self):
        row,args=fixture();struct.pack_into('<Q',row,0x50,8)
        prepare_pose_paired_primary_row(row,**args);iterate_pose_paired_primary_row(row,**args)
        self.assertEqual(struct.unpack_from('<4f',row,128),(1,)*4)
        row,args=fixture();row[0x20:0x30]=bytes(16)
        with self.assertRaises(ValueError):prepare_pose_paired_primary_row(row,**args)

    def test_secondary_phase_runs_paired_rows(self):
        row,args=fixture();context=bytearray(0x190)
        struct.pack_into('<I',context,0x38,0x10010000)
        struct.pack_into('<I',context,0x10c,1)
        solve_pose_link_rows(context,base_token=0,primary_rows=[],secondary_rows=[],paired_primary_rows=[row],**args)
        self.assertEqual(struct.unpack('<4f',args['results'][0]),(1,)*4)
