import unittest
from engine.pose_link_tangents import link_tangent_basis

IDENTITY=((1,0,0),(0,1,0),(0,0,1))

class TangentTests(unittest.TestCase):
    def test_point_rotation_can_drive_tangent_without_linear_motion(self):
        r=link_tangent_basis(IDENTITY,(1,0,0),(0,0,0),(0,0,0),(0,0,2),(0,0,1))
        self.assertEqual(r['first'],[0,-1,0])
        self.assertEqual(r['second'],[1,0,0])
        self.assertFalse(r['fallback'])

    def test_translation_parallel_to_normal_uses_fallback(self):
        r=link_tangent_basis(IDENTITY,(0,0,0),(0,0,0),(0,0,2),(0,0,0),(0,0,1))
        self.assertEqual(r['first'],[0,1,0])
        self.assertEqual(r['second'],[-1,0,0])
        self.assertTrue(r['fallback'])

    def test_center_subtraction_precedes_basis_transform(self):
        r=link_tangent_basis(IDENTITY,(9,4,3),(9,4,3),(2,0,0),(0,0,20),(0,0,1))
        self.assertEqual(r['first'],[-1,0,0])

    def test_normal_is_not_silently_normalized(self):
        r=link_tangent_basis(IDENTITY,(0,0,0),(0,0,0),(1,0,0),(0,0,0),(0,0,2))
        self.assertEqual(r['second'],[0,-2,0])

    def test_zero_normal_and_zero_motion_has_no_invented_basis(self):
        with self.assertRaises(ValueError):
            link_tangent_basis(IDENTITY,(0,0,0),(0,0,0),(0,0,0),(0,0,0),(0,0,0))
