import math
import struct
import unittest
from engine.pose_ellipse import pose_ellipse_project,pose_ellipse_normal


class PoseEllipseTests(unittest.TestCase):
    def test_origin_selects_positive_short_axis(self):
        self.assertEqual(pose_ellipse_project(0,0,1,2),[1,0])
        self.assertEqual(pose_ellipse_project(0,0,2,1),[0,1])
        self.assertEqual(pose_ellipse_project(0,0,1,1),[0,1])

    def test_interior_axis_branch_not_interior_identity(self):
        x,y=pose_ellipse_project(0,.5,1,2)
        self.assertAlmostEqual(y,2/3,places=6)
        self.assertAlmostEqual(x*x+(y/2)**2,1,places=6)
        self.assertGreater(x,0)

    def test_axis_endpoint_sign(self):
        self.assertEqual(pose_ellipse_project(-4,0,2,1),[-2,0])
        self.assertEqual(pose_ellipse_project(0,-4,1,2),[0,-2])

    def test_circle_radial_projection(self):
        x,y=pose_ellipse_project(3,4,2,2)
        self.assertAlmostEqual(x,1.2,places=6)
        self.assertAlmostEqual(y,1.6,places=6)

    def test_normal_gradient_direction(self):
        nx,ny=pose_ellipse_normal(2,1,1,1)
        self.assertAlmostEqual(ny/nx,4,places=6)
        self.assertAlmostEqual(nx*nx+ny*ny,1,places=6)

    def test_native_iteration_cap_fixture(self):
        value=pose_ellipse_project(-3.876117706298828,1.4940327405929565,2.1804399490356445,2.4682557582855225)
        self.assertEqual(struct.pack("<2f",*value).hex(),"a27102c06b7e603f")

    def test_invalid_domains(self):
        for radii in ((0,1),(1,-1),(math.inf,1)):
            with self.assertRaises(ValueError):pose_ellipse_project(1,1,*radii)
        with self.assertRaises(ValueError):pose_ellipse_normal(1,1,0,0)
