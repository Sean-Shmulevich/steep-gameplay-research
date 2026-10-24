import struct
import unittest
from engine.pose_solver_layout import plan_pose_solver_layout,initialize_pose_solver_storage

class LayoutTests(unittest.TestCase):
    def counts(self):
        counts=[0]*25;counts[0]=1;counts[6]=2;return counts

    def test_triplet_ranges_and_distinct_counter_blocks(self):
        counts=self.counts();plan=plan_pose_solver_layout(counts,1)
        self.assertEqual(plan['category_starts'][6],7)
        self.assertEqual([plan[k] for k in ('body_data_offset','body_state_offset','results_offset','size')],[0x2e0,0x320,0x340,0x370])
        storage=bytearray([0xa5]*0x400);initialize_pose_solver_storage(storage,counts,1)
        self.assertEqual(struct.unpack_from('<I',storage,0x108)[0],1)
        self.assertEqual(struct.unpack_from('<I',storage,0x120)[0],2)
        self.assertEqual(storage[0xa4:0x108],bytes(100))
        self.assertEqual(storage[0x340:0x370],bytes(48))
        self.assertEqual(storage[0x190:0x340],bytes([0xa5])*(0x340-0x190))
        self.assertEqual(storage[0x370:],bytes([0xa5])*0x90)

    def test_body_count_truncation(self):
        self.assertEqual(plan_pose_solver_layout(self.counts(),0x10001),plan_pose_solver_layout(self.counts(),1))

    def test_phase_flags_and_only_named_header_fields_reset(self):
        storage=bytearray([0xff]*0x190)
        initialize_pose_solver_storage(storage,[0]*25,0)
        self.assertEqual(struct.unpack_from('<I',storage,0x38)[0],0x98000003)
        self.assertEqual(storage[0xc:0x14],bytes(8));self.assertEqual(storage[0x30:0x38],bytes(8))
        self.assertEqual(storage[:0xc],bytes([0xff])*12)
        self.assertEqual(storage[0x184:],bytes([0xff])*12)

    def test_plan_retains_wrapping_but_initializer_rejects_unsafe_storage(self):
        counts=[0]*25;counts[0]=0x10000000
        self.assertEqual(plan_pose_solver_layout(counts,0)['body_data_offset'],0x190)
        with self.assertRaises(ValueError):initialize_pose_solver_storage(bytearray(0x190),counts,0)
        with self.assertRaises(ValueError):initialize_pose_solver_storage(bytearray(0x190),self.counts(),1)
