import struct
import unittest
from engine.pose_paired_two_stage_solver import (
    prepare_pose_paired_two_stage_row, iterate_pose_paired_two_stage_row)
from engine.pose_link_solve import solve_pose_link_rows


class PairedTwoStageTests(unittest.TestCase):
    def fixture(self, alias=False):
        row = bytearray(352)
        struct.pack_into('<HHI', row, 0, 0, 0 if alias else 1, 0)
        for start in (0x20, 0x80, 0x100, 0x130):
            for i in range(3):
                struct.pack_into('<4f', row, start+i*16,
                                 *[float(i == j) for j in range(4)])
        data = bytearray(struct.pack('<16f', 1,0,0,0, 0,1,0,0, 0,0,1,0, 1,1,1,1))
        return row, dict(body_data=[data, bytearray(data)],
                         body_state=[bytearray(32), bytearray(32)], results=[bytearray(16)])

    def test_coupled_then_angular_updates_both_endpoints(self):
        row, args = self.fixture()
        struct.pack_into('<4f', row, 16, 4,8,12,16)
        prepare_pose_paired_two_stage_row(row, **args)
        iterate_pose_paired_two_stage_row(row, **args)
        self.assertEqual(struct.unpack_from('<8f', args['body_state'][0]), (-1,-2,-3,0,-1,0,0,0))
        self.assertEqual(struct.unpack_from('<8f', args['body_state'][1]), (1,2,3,0,-1,0,0,0))
        self.assertEqual(struct.unpack_from('<4f', row, 0xf0), (0,2,3,0))
        self.assertEqual(struct.unpack_from('<4f', args['results'][0]), (-1,-2,-3,0))

    def test_aliases_accumulate_sequentially(self):
        row, args = self.fixture(alias=True)
        struct.pack_into('<4f', args['results'][0], 0, 1,2,3,4)
        struct.pack_into('<4f', row, 0xf0, 5,6,7,8)
        prepare_pose_paired_two_stage_row(row, **args)
        self.assertEqual(struct.unpack_from('<8f', args['body_state'][0]), (0,0,0,0,12,16,20,0))
        self.assertEqual(bytes(args['body_state'][1]), bytes(32))
        self.assertEqual(struct.unpack_from('<12f', row, 0xb0), (0,0,0,0,0,.5,0,0,0,0,.5,0))

    def test_angular_denominator_sums_endpoints(self):
        row, args = self.fixture()
        struct.pack_into('<f', args['body_data'][1], 0x14, 3.)
        struct.pack_into('<f', args['body_data'][1], 0x28, 7.)
        prepare_pose_paired_two_stage_row(row, **args)
        self.assertEqual(struct.unpack_from('<f', row, 0xc4)[0], .25)
        self.assertEqual(struct.unpack_from('<f', row, 0xd8)[0], .125)

    def test_zero_denominator_rejected(self):
        row, args = self.fixture()
        row[0x80:0xb0] = bytes(48)
        row[0x130:0x160] = bytes(48)
        with self.assertRaises(ValueError):
            prepare_pose_paired_two_stage_row(row, **args)

    def test_normal_and_special_traversal(self):
        for flags, expected in [(4, -1.), (0x10010000, 0.)]:
            row, args = self.fixture()
            struct.pack_into('<4f', row, 16, 4,8,12,16)
            context = bytearray(0x190)
            struct.pack_into('<I', context, 0x38, flags)
            struct.pack_into('<I', context, 0x164, 1)
            before = bytes(row)
            solve_pose_link_rows(context, base_token=0, primary_rows=[], secondary_rows=[],
                                 paired_two_stage_rows=[row], **args)
            self.assertEqual(struct.unpack_from('<f', args['body_state'][0])[0], expected)
            if flags == 0x10010000:
                self.assertEqual(bytes(row), before)

    def test_populated_pool_requires_storage(self):
        row, args = self.fixture()
        context = bytearray(0x190)
        struct.pack_into('<I', context, 0x164, 1)
        with self.assertRaisesRegex(ValueError, 'paired two-stage'):
            solve_pose_link_rows(context, base_token=0, primary_rows=[], secondary_rows=[], **args)
