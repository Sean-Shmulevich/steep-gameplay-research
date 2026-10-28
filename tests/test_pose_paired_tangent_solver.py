import struct
import unittest
from engine.pose_paired_tangent_solver import prepare_pose_paired_tangent_row,iterate_pose_paired_tangent_row
from engine.pose_link_solve import solve_pose_link_rows


def fixture():
    row=bytearray(128);struct.pack_into('<HHI',row,0,0,1,1)
    struct.pack_into('<4f',row,0x20,1,0,0,0)
    struct.pack_into('<I',row,0x60,0);struct.pack_into('<4f',row,0x70,.5,.5,.5,.5)
    data=[bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1)) for _ in range(2)]
    states=[bytearray(struct.pack('<8f',4,0,0,0,0,0,0,0)),bytearray(32)]
    results=[bytearray(struct.pack('<4f',1,1,1,1)),bytearray(16)]
    return row,dict(body_data=data,body_state=states,results=results)


class PairedTangentTests(unittest.TestCase):
    def test_primary_bound_and_opposed_motion_updates(self):
        row,args=fixture();prepare_pose_paired_tangent_row(row,**args)
        self.assertEqual(struct.unpack_from('<4f',row,0x40),(-.5,)*4)
        iterate_pose_paired_tangent_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(.5,)*4)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],3.5)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][1])[0],.5)

    def test_response_is_unused_and_inverted_bounds_preserve_order(self):
        row,args=fixture();row[0x10:0x20]=bytes([0xff]*16)
        struct.pack_into('<4f',row,0x70,-.5,-.5,-.5,-.5)
        prepare_pose_paired_tangent_row(row,**args);iterate_pose_paired_tangent_row(row,**args)
        self.assertEqual(struct.unpack('<4f',args['results'][1]),(.5,)*4)
        self.assertEqual(row[0x10:0x20],bytes([0xff]*16))

    def test_special_phase_skips_paired_tangent(self):
        row,args=fixture();before=bytes(row);states=list(map(bytes,args['body_state']))
        context=bytearray(0x190);struct.pack_into('<I',context,0x38,0x10010000)
        struct.pack_into('<I',context,0x124,1)
        solve_pose_link_rows(context,base_token=0,primary_rows=[],secondary_rows=[],paired_tangent_rows=[row],**args)
        self.assertEqual(row,before);self.assertEqual(args['body_state'],states)
