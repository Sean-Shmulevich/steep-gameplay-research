import struct
import unittest
from engine.pose_constraint_drive import build_pose_angular_drive_row
from engine.pose_bounded_scalar_solver import prepare_pose_bounded_scalar_row, iterate_pose_bounded_scalar_row


class DriveBuilderTests(unittest.TestCase):
    def fixture(self):
        c = bytearray(b'\xa5'*0x1000)
        for off,value in ((0x16c,0x400),(0x78,0),(0x7c,16),(0xdc,0),(0xe0,0),(0x180,0)):
            struct.pack_into('<I', c, off, value)
        struct.pack_into('<2f', c, 0xc, 2.,.25)
        return c,dict(single=True,mode=1,axis=[1,0,0,0],sample=[3,-3,1,9],
                      reference=[1,1,0,0],rate_bound=[2,3,4,5],impulse_bound=[8,99,99,99])

    def test_error_scaled_clamped_then_negated(self):
        c,args = self.fixture()
        row = build_pose_angular_drive_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+16), (-2,3,-2,2))
        self.assertEqual(c[row:row+4], b'\xa5'*4)
        self.assertEqual(c[row+0x40:row+0x50], b'\xa5'*16)

    def test_mode_two_does_not_require_reference_or_rate_bound(self):
        c,args = self.fixture()
        args.update(mode=2,reference=None,rate_bound=None)
        row = build_pose_angular_drive_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+16), (-3,3,-1,2))

    def test_paired_angular_axis_is_opposite(self):
        c,args = self.fixture()
        args.update(single=False,axis=[1,-2,3,-4])
        row = build_pose_angular_drive_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x30), (1,-2,3,-4))
        self.assertEqual(struct.unpack_from('<4f', c, row+0x50), (-1,2,-3,4))
        self.assertEqual(struct.unpack_from('<I', c, 0xe0)[0], 1)

    def test_signed_zero_clamp_tie_uses_second_operand(self):
        c,args = self.fixture()
        args.update(sample=[0]*4,reference=[0]*4,rate_bound=[0.]*4)
        row = build_pose_angular_drive_row(c, **args)
        self.assertEqual(c[row+16:row+28], bytes.fromhex('00000080')*3)

    def test_composed_drive_is_bounded_per_iteration(self):
        c,args = self.fixture()
        args.update(mode=2,sample=[10,10,10,0],impulse_bound=[1]*4)
        offset = build_pose_angular_drive_row(c, **args)
        struct.pack_into('<HH', c, offset, 0,65535)
        row = memoryview(c)[offset:offset+80]
        data = bytearray(struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        solver = dict(body_data=[data],body_state=[bytearray(32)],results=[bytearray(16)],added_response=False)
        prepare_pose_bounded_scalar_row(row, **solver)
        for _ in range(3):
            iterate_pose_bounded_scalar_row(row, **solver)
        self.assertEqual(struct.unpack_from('<f', solver['body_state'][0],16)[0], .75)
        self.assertEqual(struct.unpack_from('<4f', solver['body_state'][0]), (0,0,0,0))

    def test_capacity_guard_preserves_context(self):
        c,args = self.fixture()
        struct.pack_into('<I', c, 0x16c, len(c)-16)
        before = bytes(c)
        with self.assertRaises(ValueError):
            build_pose_angular_drive_row(c, **args)
        self.assertEqual(bytes(c), before)
