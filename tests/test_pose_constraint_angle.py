import struct
import unittest
from reference.central_impulse import f32
from engine.pose_constraint_angle import select_pose_angle_interval,pose_constraint_drive_sample,TAU


class AngleInputTests(unittest.TestCase):
    def test_boundary_equality_is_unchanged(self):
        for angle in (-1.,1.):
            self.assertEqual(select_pose_angle_interval([angle]*4,[-1]*4,[1]*4), [angle]*4)

    def test_adjacent_revolution_not_clamp_or_modulo(self):
        self.assertEqual(select_pose_angle_interval([6.]*4,[-1]*4,[1]*4), [f32(6.-TAU)]*4)
        self.assertEqual(select_pose_angle_interval([-6.]*4,[-1]*4,[1]*4), [f32(-6.+TAU)]*4)
        self.assertEqual(select_pose_angle_interval([20.]*4,[-1]*4,[1]*4), [f32(20.-TAU)]*4)

    def test_nonuniform_xyz_prevents_selection(self):
        angle = [6.,0.,6.,20.]
        self.assertEqual(select_pose_angle_interval(angle,[-1]*4,[1]*4), angle)

    def test_w_does_not_gate_but_is_selected(self):
        angle = [6.,6.,6.,20.]
        self.assertEqual(select_pose_angle_interval(angle,[-1]*4,[1]*4),
                         [f32(6.-TAU)]*3+[f32(20.-TAU)])

    def test_sample_bounds_not_sorted(self):
        c = bytearray(0xe0)
        struct.pack_into('<2f',c,0xd0,4,2)
        struct.pack_into('<f',c,0xdc,3)
        self.assertEqual(pose_constraint_drive_sample(c),2)
        struct.pack_into('<2f',c,0xd0,-1,1)
        for current,expected in ((-3,-1),(0,0),(3,1)):
            struct.pack_into('<f',c,0xdc,current)
            self.assertEqual(pose_constraint_drive_sample(c),expected)

    def test_equal_sample_preserves_selected_lower_zero(self):
        c = bytearray(0xe0)
        struct.pack_into('<2f',c,0xd0,-0.,1.)
        self.assertEqual(struct.pack('<f',pose_constraint_drive_sample(c)),bytes.fromhex('00000080'))
