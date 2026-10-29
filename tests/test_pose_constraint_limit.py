import struct
import unittest
from engine.pose_constraint_limit import build_pose_angular_limit_row, THRESHOLD, EPSILON


class AngularLimitBuilderTests(unittest.TestCase):
    def fixture(self, scalar=2., phase=0x08000000, iterations=2):
        c = bytearray(b'\xa5'*0x1000)
        for off,value in ((0x16c,0x400),(0x60,0),(0x64,16),(0xc4,0),(0xc8,0),(0x180,0),(0x38,phase|(iterations<<2))):
            struct.pack_into('<I', c, off, value)
        struct.pack_into('<f', c, 0xc, scalar)
        args = dict(single=True,axis=[1,2,3,4],coordinate=[-1]*4,
                    sign=[1]*4,offset=[0]*4,response_term=[THRESHOLD]*4,response_mix=[1]*4)
        return c,args

    def test_hard_response_phase_and_fourth_lane(self):
        for phase,expected in ((0x08000000,-.8),(0,0)):
            c,args = self.fixture(phase=phase)
            args['coordinate'] = [1,1,1,-1]
            row = build_pose_angular_limit_row(c, **args)
            response = struct.unpack_from('<4f', c, row+0x10)
            self.assertAlmostEqual(response[3], expected)
            self.assertAlmostEqual(response[0], -expected)
            self.assertEqual(struct.unpack_from('<4f', c, row+0x60), (0,0,0,0))

    def test_nonnegative_hard_response_is_not_phase_suppressed(self):
        c,args = self.fixture(phase=0)
        args['coordinate'] = [1]*4
        row = build_pose_angular_limit_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x10), (2,2,2,2))

    def test_finite_response_uses_iteration_count(self):
        for iterations,term,gain in ((2,1.,.5),(4,4./3.,1./3.)):
            c,args = self.fixture(phase=0,iterations=iterations)
            args['response_term'] = [4]*4
            row = build_pose_angular_limit_row(c, **args)
            self.assertAlmostEqual(struct.unpack_from('<f', c, row+0x60)[0], term)
            self.assertAlmostEqual(struct.unpack_from('<f', c, row+0x10)[0], -2*gain)

    def test_nonnegative_finite_response_disables_added_term(self):
        c,args = self.fixture()
        args['coordinate'] = [0]*4
        args['response_term'] = [4]*4
        row = build_pose_angular_limit_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x10), (THRESHOLD,)*4)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x60), (0,)*4)

    def test_epsilon_path_preserves_supplied_response(self):
        for scalar in (0.,EPSILON,-EPSILON):
            c,args = self.fixture(scalar=scalar,iterations=0)
            args['response_term'] = [1,2,3,4]
            row = build_pose_angular_limit_row(c, **args)
            self.assertEqual(struct.unpack_from('<4f', c, row+0x60), (1,2,3,4))
            self.assertAlmostEqual(struct.unpack_from('<f', c, row+0x10)[0], -.4*scalar)

    def test_strict_xyz_threshold_excludes_w(self):
        c,args = self.fixture(scalar=0,iterations=0)
        args['response_term'] = [1,2,3,THRESHOLD*2]
        row = build_pose_angular_limit_row(c, **args)
        self.assertEqual(struct.unpack_from('<f', c, row+0x60)[0], 1.)
        c,args = self.fixture(scalar=0,iterations=0)
        args['response_term'] = [1,THRESHOLD,3,4]
        row = build_pose_angular_limit_row(c, **args)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x60), (0,)*4)

    def test_paired_sign_and_preserved_indices(self):
        c,args = self.fixture()
        args['single'] = False
        args['sign'] = [1,-1,2,-2]
        row = build_pose_angular_limit_row(c, **args)
        self.assertEqual(c[row:row+4], b'\xa5'*4)
        self.assertEqual(struct.unpack_from('<4f', c, row+0x30), (1,-2,6,-8))
        self.assertEqual(struct.unpack_from('<4f', c, row+0x70), (-1,2,-6,8))
        self.assertEqual(struct.unpack_from('<Q', c, row+0x50)[0], 0)
        self.assertEqual(struct.unpack_from('<I', c, 0xc8)[0], 1)

    def test_zero_iteration_divisor_rejected(self):
        c,args = self.fixture(iterations=0)
        args['response_term'] = [1]*4
        before = bytes(c)
        with self.assertRaises(ValueError):
            build_pose_angular_limit_row(c, **args)
        self.assertEqual(bytes(c), before)
