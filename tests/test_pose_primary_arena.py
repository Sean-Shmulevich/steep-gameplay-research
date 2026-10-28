import struct
import unittest
from engine.pose_primary_solver import prepare_pose_primary_row,iterate_pose_primary_row
from engine.pose_paired_primary_solver import prepare_pose_paired_primary_row,iterate_pose_paired_primary_row
from test_pose_primary_solver import data


class PrimaryArenaTests(unittest.TestCase):
    def test_negative_link_updates_preceding_storage_for_both_families(self):
        for paired in (False,True):
            arena=bytearray([0xa5]*512);row=memoryview(arena)[256:384];row[:]=bytes(128)
            struct.pack_into('<HHI',row,0,0,1,0)
            struct.pack_into('<4f',row,0x10,-2,-2,-2,-2)
            struct.pack_into('<4f',row,0x20,1,0,0,0)
            struct.pack_into('<q',row,0x50,-8)
            struct.pack_into('<4f',arena,128,5,5,5,5)
            args=dict(body_data={0:data(),1:data()},body_state={0:bytearray(32),1:bytearray(32)},results={0:bytearray(16)})
            prepare=prepare_pose_paired_primary_row if paired else prepare_pose_primary_row
            iterate=iterate_pose_paired_primary_row if paired else iterate_pose_primary_row
            prepare(row,**args)
            iterate(row,**args,arena=arena,row_offset=256)
            expected=1 if paired else 2
            self.assertEqual(struct.unpack_from('<4f',arena,128),(5+expected,)*4)
            self.assertEqual(arena[:128],bytes([0xa5]*128))
            self.assertEqual(arena[144:256],bytes([0xa5]*112))
            iterate(row,**args,arena=arena,row_offset=256)
            # Native accumulates the full projected value again, not only its delta.
            self.assertEqual(struct.unpack_from('<4f',arena,128),(5+2*expected,)*4)

    def test_negative_link_requires_available_storage(self):
        from engine.pose_primary_solver import _accumulate_primary_result
        row=bytearray(112);struct.pack_into('<q',row,0x50,-1)
        with self.assertRaises(ValueError):_accumulate_primary_result(row,[0]*4)
