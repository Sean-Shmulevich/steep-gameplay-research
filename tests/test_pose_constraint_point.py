import struct
import unittest
from engine.pose_constraint_point import build_pose_point_constraint
from engine.pose_point_solver import prepare_pose_point_row, iterate_pose_point_row


class PointConstraintTests(unittest.TestCase):
    def fixture(self, paired=False, phase=0x08000000):
        context = bytearray(b'\xa5'*0x1000)
        struct.pack_into('<I', context, 0x38, phase)
        struct.pack_into('<f', context, 0xc, 2.5)
        for offset, value in ((0x16c,0x400),(0x68,0),(0x6c,16),(0xcc,0),(0xd0,0),(0x180,0)):
            struct.pack_into('<I', context, offset, value)
        constraint = bytearray(0x90)
        struct.pack_into('<2Q', constraint, 8, 1,2)
        bodies = {1:bytearray(0x140), 2:bytearray(0x140)}
        for token, body in bodies.items():
            struct.pack_into('<H', body, 0x1c, token-1)
            struct.pack_into('<Q', body, 0x30, 10)
            for i in range(3):
                struct.pack_into('<4f', body, 0x40+i*16, *[float(i==j) for j in range(4)])
        metadata = {10:bytearray(0x60)}
        struct.pack_into('<H', metadata[10], 0x50, 0x8000 if paired else 0)
        return context, constraint, dict(bodies=bodies, metadata=metadata)

    def test_phase_gate_and_unused_result_storage(self):
        for phase, expected in ((0,0),(0x08000000,2),(0x10000000,0),(0x18000000,0)):
            c, constraint, args = self.fixture(phase=phase)
            struct.pack_into('<f', args['bodies'][1], 0x70, 2)
            untouched = bytes(c[0x480:])
            self.assertEqual(build_pose_point_constraint(c, constraint, **args), 1)
            self.assertEqual(struct.unpack_from('<4f', c, 0x410)[:3], (expected,0,0))
            self.assertEqual(c[0x41c:0x420], bytes.fromhex('ffff7f7f'))
            self.assertEqual(c[0x450:0x480], b'\xa5'*48)
            self.assertEqual(bytes(c[0x480:]), untouched)

    def test_paired_selection_and_cross_product_signs(self):
        c, constraint, args = self.fixture(paired=True)
        struct.pack_into('<4f', constraint, 0x70, 1,2,3,99)
        struct.pack_into('<4f', constraint, 0x80, 4,5,6,99)
        build_pose_point_constraint(c, constraint, **args)
        self.assertEqual(struct.unpack_from('<3f', c, 0x520), (0,-3,2))
        self.assertEqual(struct.unpack_from('<3f', c, 0x580), (0,6,-5))
        self.assertEqual(struct.unpack_from('<HHI', c, 0x500), (0,1,0))
        self.assertEqual(struct.unpack_from('<I', c, 0xd0)[0], 1)
        self.assertEqual(struct.unpack_from('<I', c, 0xcc)[0], 0)
        self.assertEqual(struct.unpack_from('<I', c, 0x180)[0], 1)

    def test_center_offset_changes_arm_not_world_anchor(self):
        c, constraint, args = self.fixture()
        struct.pack_into('<3f', constraint, 0x70, 1,2,3)
        struct.pack_into('<3f', args['bodies'][1], 0x128, 1,2,3)
        build_pose_point_constraint(c, constraint, **args)
        self.assertEqual(struct.unpack_from('<3f', c, 0x410), (1,2,3))
        self.assertTrue(all(x == 0 for x in struct.unpack_from('<12f', c, 0x420)))

    def test_built_single_row_drives_existing_solver(self):
        c, constraint, args = self.fixture()
        struct.pack_into('<f', args['bodies'][1], 0x70, 2)
        build_pose_point_constraint(c, constraint, **args)
        data = bytearray(struct.pack('<16f', 1,0,0,0,0,1,0,0,0,0,1,0,1,1,1,1))
        row = memoryview(c)[0x400:0x480]
        solver = dict(body_data=[data], body_state=[bytearray(32)], results=[bytearray(16)])
        prepare_pose_point_row(row, **solver)
        iterate_pose_point_row(row, **solver)
        state = struct.unpack_from('<8f', solver['body_state'][0])
        # The single-body solver normalizes before inversion, retaining float32 error.
        self.assertAlmostEqual(state[0], -2., delta=1e-6)
        self.assertEqual(state[1:], (0,0,0,0,0,0,0))

    def test_capacity_guard_precedes_counter_changes(self):
        c, constraint, args = self.fixture()
        struct.pack_into('<I', c, 0x16c, len(c)-16)
        before = bytes(c)
        with self.assertRaises(ValueError):
            build_pose_point_constraint(c, constraint, **args)
        self.assertEqual(bytes(c), before)
