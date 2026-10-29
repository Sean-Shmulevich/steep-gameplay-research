import unittest
from engine.pose_constraint_limit_geometry import pose_angular_limit_geometry
from engine.pose_ellipse import EPSILON


def geometry(radius=1.,angle=0.,a=0.,b=2.,axis=None):
    return pose_angular_limit_geometry([radius]*4,[angle]*4,[a]*4,[b]*4,
                                      axis or [1,0,0,7],[0,0,1,0])


class LimitGeometryTests(unittest.TestCase):
    def test_equal_extents_shortcut_preserves_all_lanes(self):
        axis,error=pose_angular_limit_geometry([1,2,3,4],[0]*4,[2]*4,[2]*4,[1,0,0,7],[0,0,1,0])
        self.assertEqual(axis,[1,0,0,7])
        self.assertEqual(error,[1,0,-1,-2])

    def test_radius_skip_preserves_axis(self):
        self.assertEqual(geometry(radius=0.),([1,0,0,7],[0]*4))

    def test_equal_extent_gate_includes_w(self):
        axis,error=pose_angular_limit_geometry([0]*4,[0]*4,[2]*4,[2,2,2,3],[1,0,0,7],[0,0,1,0])
        self.assertEqual(error,[0]*4)

    def test_degenerate_extent_projection(self):
        axis,error=geometry()
        self.assertEqual(axis,[1,0,0,0])
        self.assertEqual(error,[-1]*4)

    def test_negligible_residual_uses_squared_length_threshold(self):
        axis,error=geometry(radius=.001)
        self.assertEqual(axis,[1,0,0,7])
        self.assertEqual(error,[0]*4)

    def test_elliptical_branch_and_rotation(self):
        axis,error=geometry(radius=3.,angle=.7,a=1.,b=2.)
        self.assertEqual(axis[3],0.)
        self.assertLess(error[0],0)
        self.assertTrue(all(v==error[0] for v in error))
        self.assertNotEqual(axis[1],0)
        self.assertAlmostEqual(sum(v*v for v in axis[:3]),1.,places=6)
