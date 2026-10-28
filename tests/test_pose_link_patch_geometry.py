import unittest
from reference.central_impulse import f32
from engine.pose_link_patch_geometry import contact_patch_geometry


class ContactPatchGeometryTest(unittest.TestCase):
    basis=[[1,0,0],[0,1,0],[0,0,1]]

    def test_centroid_and_mean_distance(self):
        result=contact_patch_geometry(self.basis,[10,20,30],[[-2,0,0],[2,0,0]])
        self.assertEqual(result['world_points'],[[8,20,30],[12,20,30]])
        self.assertEqual(result['centroid_arm'],[0,0,0])
        self.assertEqual(result['distance_sum'],4)
        self.assertEqual(result['spread'],2)

    def test_floor_applies_before_division(self):
        for count in (1,2,4):
            result=contact_patch_geometry(self.basis,[0,0,0],[[0,0,0]]*count)
            self.assertEqual(result['distance_sum'],0)
            self.assertEqual(result['spread'],f32(f32(.001)*f32(1/count)))

    def test_basis_scaling_affects_spread(self):
        result=contact_patch_geometry([[2,0,0],[0,1,0],[0,0,1]],[0,0,0],[[-1,0,0],[1,0,0]])
        self.assertEqual(result['spread'],2)
        with self.assertRaises(ValueError):contact_patch_geometry(self.basis,[0,0,0],[])
