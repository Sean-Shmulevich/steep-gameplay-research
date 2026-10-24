import math
import unittest
from engine.snow_basis_publication import publish_basis_pose


class BasisPublicationTests(unittest.TestCase):
    def test_four_lane_normalization_then_xyz_storage_without_cache_mutation(self):
        cache=[[3,0,0,4],[0,2,0,0],[0,0,7,0]];calls=[]
        def seed(n):calls.append(n);return 1/math.sqrt(n)
        r=publish_basis_pose(cache,[1,2,3,4],[5,6,7,8],[9,10,11,12],seed)
        self.assertEqual(calls,[49,4,25])
        self.assertAlmostEqual(r['pose_basis_xyz'][0][0],.6,places=6)
        self.assertEqual(cache[0],[3,0,0,4])
        self.assertEqual(r['auxiliary_direction'],[1,2,3,4])
        self.assertEqual(r['frame_vector70_xyz'],[5,6,7])
        self.assertEqual(r['runtime_vector940_xyz'],[9,10,11])

    def test_w_only_axis_is_valid_here_and_publishes_zero_xyz(self):
        r=publish_basis_pose([[0,0,0,1]]*3,[0]*4,[0]*4,[0]*4,lambda n:1/math.sqrt(n))
        self.assertEqual(r['pose_basis_xyz'],[[0,0,0]]*3)
