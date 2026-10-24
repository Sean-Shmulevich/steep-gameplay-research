import unittest
from engine.snow_pose_inertia import composite_pose_coefficients


class PoseInertiaTests(unittest.TestCase):
    def test_separation_terms_and_native_axis_order(self):
        r=composite_pose_coefficients([1,2,3],[4,5,6],[0,0,0,1],[2,0,0,1],4,2,True)
        self.assertEqual(r,[9,11,9])
        r=composite_pose_coefficients([1,2,3],[4,5,6],[0,0,0,1],[0,0,2,1],4,2,True)
        self.assertEqual(r,[9,7,13])

    def test_nonpaired_copies_primary_without_secondary_dependencies(self):
        self.assertEqual(composite_pose_coefficients([1,2,3],None,None,None,None,None,False),[1,2,3])

    def test_zero_separation_adds_only_base_vectors(self):
        self.assertEqual(composite_pose_coefficients([1,2,3],[4,5,6],[1,2,3,0],[1,2,3,0],4,2,True),[5,7,9])
