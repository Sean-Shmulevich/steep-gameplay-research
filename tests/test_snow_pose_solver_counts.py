import struct
import unittest
from engine.snow_pose_solver_counts import pose_solver_counts,HARD_THRESHOLD


class SolverCountTests(unittest.TestCase):
    def test_hard_triple_is_one_block_and_other_rows_remain_counted(self):
        data=bytearray(288)
        for off in (0x8c,0xa0,0xb4):struct.pack_into('<f',data,off,HARD_THRESHOLD)
        result=pose_solver_counts(data,0x8000)
        self.assertTrue(result['metadata_bit15_set'])
        self.assertEqual(result['hard_triple_blocks'],1)
        self.assertEqual(result['flagged_or_hard_rows'],0)
        self.assertEqual(result['second_soft_rows'],3)

    def test_state_two_and_flags_are_distinct_from_disabled_boolean(self):
        data=bytearray(288)
        struct.pack_into('<I',data,0x80,2)
        struct.pack_into('<I',data,0xbc,1);data[0xf8]=255
        struct.pack_into('<I',data,0xd0,2);data[0x104]=1
        r=pose_solver_counts(data,0)
        self.assertEqual(r['doubled_rows'],4)
        self.assertEqual(r['first_soft_rows'],3)
        self.assertEqual(r['flagged_or_hard_rows'],2)
        self.assertEqual(r['second_soft_rows'],1)
