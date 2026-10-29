import struct
import unittest
from engine.pose_two_stage_solver import prepare_pose_two_stage_row, iterate_pose_two_stage_row
from engine.pose_link_solve import solve_pose_link_rows


class TwoStageTests(unittest.TestCase):
    def fixture(self):
        row = bytearray(256)
        struct.pack_into('<HHI', row, 0, 0, 65535, 0)
        for start in (0x20, 0x80):
            for i in range(3):
                struct.pack_into('<4f', row, start+i*16,
                                 *[float(i == j) for j in range(4)])
        data = bytearray(struct.pack('<16f', 1,0,0,0, 0,1,0,0, 0,0,1,0, 1,1,1,1))
        return row, dict(body_data=[data], body_state=[bytearray(32)], results=[bytearray(16)])

    def test_second_stage_reads_corrected_angular_state(self):
        row, args = self.fixture()
        struct.pack_into('<4f', row, 16, 2,4,6,8)
        prepare_pose_two_stage_row(row, **args)
        iterate_pose_two_stage_row(row, **args)
        self.assertEqual(struct.unpack_from('<4f', args['body_state'][0]), (-1,-2,-3,0))
        self.assertEqual(struct.unpack_from('<4f', args['body_state'][0], 16), (-1,0,0,0))
        self.assertEqual(struct.unpack_from('<4f', args['results'][0]), (-1,-2,-3,0))
        self.assertEqual(struct.unpack_from('<4f', row, 0xf0), (0,2,3,0))

    def test_preparation_applies_both_caches_without_clearing(self):
        row, args = self.fixture()
        struct.pack_into('<4f', args['results'][0], 0, 1,2,3,4)
        struct.pack_into('<4f', row, 0xf0, 5,6,7,8)
        prepare_pose_two_stage_row(row, **args)
        self.assertEqual(struct.unpack_from('<8f', args['body_state'][0]), (1,2,3,4,6,8,10,0))
        self.assertEqual(struct.unpack_from('<4f', row, 0xf0), (5,6,7,8))
        self.assertEqual(struct.unpack_from('<12f', row, 0xb0), (0,0,0,0,0,1,0,0,0,0,1,0))

    def test_zero_angular_response_rejected(self):
        row, args = self.fixture()
        row[0x80:0xb0] = bytes(48)
        with self.assertRaises(ValueError):
            prepare_pose_two_stage_row(row, **args)

    def test_traversal_normal_only(self):
        for flags, expected in [(4, -1), (0x10010000, 0)]:
            row, args = self.fixture()
            struct.pack_into('<4f', row, 16, 2,4,6,8)
            context = bytearray(0x190)
            struct.pack_into('<I', context, 0x38, flags)
            struct.pack_into('<I', context, 0x160, 1)
            before = bytes(row)
            solve_pose_link_rows(context, base_token=0, primary_rows=[], secondary_rows=[],
                                 two_stage_rows=[row], **args)
            self.assertEqual(struct.unpack_from('<f', args['body_state'][0])[0], expected)
            if flags == 0x10010000:
                self.assertEqual(bytes(row), before)

    def test_populated_pool_requires_storage(self):
        row, args = self.fixture()
        context = bytearray(0x190)
        struct.pack_into('<I', context, 0x160, 1)
        with self.assertRaisesRegex(ValueError, 'two-stage'):
            solve_pose_link_rows(context, base_token=0, primary_rows=[], secondary_rows=[], **args)
