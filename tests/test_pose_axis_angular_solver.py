import struct
import unittest
from engine.pose_axis_angular_solver import prepare_pose_axis_angular_row,iterate_pose_axis_angular_row
from engine.pose_link_solve import solve_pose_link_rows


class AxisAngularTests(unittest.TestCase):
    def fixture(self,paired=False):
        row=bytearray(80 if paired else 64);struct.pack_into('<HHI',row,0,0,0,0)
        struct.pack_into('<4f',row,16,10,10,10,0)
        struct.pack_into('<4f',row,32,1,0,0,0)
        if paired:struct.pack_into('<4f',row,64,1,0,0,0)
        data=bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        return row,dict(body_data=[data],body_state=[bytearray(32)],results=[bytearray(16)],paired=paired)

    def test_no_cap_and_linear_state_unchanged(self):
        row,args=self.fixture();prepare_pose_axis_angular_row(row,**args);iterate_pose_axis_angular_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],-10)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],-10)
        self.assertEqual(args['body_state'][0][:16],bytes(16))

    def test_paired_cached_update_accumulates_on_same_body(self):
        row,args=self.fixture(True);struct.pack_into('<4f',args['results'][0],0,1,1,1,1)
        prepare_pose_axis_angular_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0],16)[0],2)

    def test_special_phase_skips_both_families(self):
        for paired in (False,True):
            row,args=self.fixture(paired);args.pop('paired');c=bytearray(0x190)
            struct.pack_into('<I',c,0x154 if paired else 0x150,1);struct.pack_into('<I',c,0x38,0x10010000)
            before=bytes(row);rows={'paired_axis_angular_rows' if paired else 'axis_angular_rows':[row]}
            solve_pose_link_rows(c,base_token=0,primary_rows=[],secondary_rows=[],**args,**rows)
            self.assertEqual(bytes(row),before);self.assertEqual(args['body_state'][0],bytes(32))
