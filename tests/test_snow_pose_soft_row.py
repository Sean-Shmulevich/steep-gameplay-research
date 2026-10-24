import unittest
from engine.snow_pose_soft_row import soft_pose_row_parameters
from reference.central_impulse import f32


class SoftRowTests(unittest.TestCase):
    def test_zero_branch_preserves_stiffness_without_count_division(self):
        r=soft_pose_row_parameters([1,2,3,4],[0]*4,1e-6,0)
        self.assertTrue(r['near_zero']);self.assertEqual(r['coefficient'],[1,2,3,4])
        self.assertEqual(r['angle_gain'],[f32(.4)]*4)

    def test_count_mask_and_equation(self):
        r=soft_pose_row_parameters([8]*4,[2]*4,.5,(2<<2)|0x80000003)
        self.assertEqual(r['extracted_count'],2)
        self.assertEqual(r['coefficient'],[f32(.05)]*4)
        self.assertEqual(r['angle_gain'],[f32(.8)]*4)
        with self.assertRaises(ValueError):soft_pose_row_parameters([8]*4,[2]*4,.5,0)
