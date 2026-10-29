import struct
import unittest
from engine.pose_bounded_scalar_solver import prepare_pose_bounded_scalar_row,iterate_pose_bounded_scalar_row


class BoundedScalarTests(unittest.TestCase):
    def fixture(self,paired=False):
        row=bytearray(112 if paired else 96);struct.pack_into('<HHI',row,0,0,0,0)
        struct.pack_into('<4f',row,16,1,1,1,1)
        struct.pack_into('<4f',row,32,1,0,0,0)
        struct.pack_into('<4f',row,0x60 if paired else 0x50,1,1,1,1)
        d=bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        return row,dict(body_data=[d],body_state=[bytearray(32)],results=[bytearray(16)],paired=paired)

    def test_single_retains_add_subtract_rounding(self):
        row,args=self.fixture();prepare_pose_bounded_scalar_row(row,**args)
        struct.pack_into('<4f',args['results'][0],0,*([2**26]*4))
        iterate_pose_bounded_scalar_row(row,**args)
        self.assertEqual(args['body_state'][0],bytes(32))
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],2**26)

    def test_paired_coincident_indices_keep_second_snapshot_update(self):
        row,args=self.fixture(True);struct.pack_into('<4f',args['results'][0],0,1,1,1,1)
        prepare_pose_bounded_scalar_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],-1)
        self.assertEqual(struct.unpack_from('<f',row,64)[0],struct.unpack('<f',struct.pack('<f',-1/3))[0])

    def test_single_increment_is_bounded_not_projected_nonnegative(self):
        row,args=self.fixture();prepare_pose_bounded_scalar_row(row,**args)
        iterate_pose_bounded_scalar_row(row,**args)
        self.assertEqual(struct.unpack_from('<f',args['results'][0])[0],-.5)
        self.assertEqual(struct.unpack_from('<f',args['body_state'][0])[0],-.5)

    def test_mixed_traversal_phase_gate(self):
        from engine.pose_link_solve import solve_pose_link_rows
        for paired in (False,True):
            for special in (False,True):
                row,args=self.fixture(paired)
                c=bytearray(0x190);struct.pack_into('<I',c,0x14c if paired else 0x148,1)
                struct.pack_into('<I',c,0x38,0x10010000 if special else 4)
                args.pop('paired');before=bytes(row)
                rows={'paired_bounded_rows' if paired else 'bounded_rows':[row]}
                solve_pose_link_rows(c,base_token=0,primary_rows=[],secondary_rows=[],**rows,**args)
                value=struct.unpack_from('<f',args['results'][0])[0]
                if special:
                    self.assertEqual(value,0);self.assertEqual(bytes(row),before)
                else:self.assertLess(value,0)

    def test_missing_bounded_storage_rejected(self):
        from engine.pose_link_solve import solve_pose_link_rows
        row,args=self.fixture();args.pop('paired');c=bytearray(0x190)
        struct.pack_into('<I',c,0x148,1)
        with self.assertRaisesRegex(ValueError,'bounded scalar'):
            solve_pose_link_rows(c,base_token=0,primary_rows=[],secondary_rows=[],**args)
