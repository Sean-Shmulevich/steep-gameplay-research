import unittest
from engine.pose_box_resource_bounds import box_resource_bounds
from engine.pose_grid_contact_frames import grid_contact_frames


class BoxBoundsTest(unittest.TestCase):
    def test_absolute_basis_extent_sum_with_shear_and_reflection(self):
        frame=[[2,0,0],[-1,3,0],[0,0,-4],[10,20,30]]
        self.assertEqual(box_resource_bounds([1,2,3],frame),[6,14,18,14,26,42])

    def test_relative_frame_bounds_for_translated_scaled_terrain(self):
        terrain=[[2,0,0],[0,4,0],[0,0,2],[10,20,30]]
        box=[[1,0,0],[0,1,0],[0,0,1],[12,28,36]]
        _,relative=grid_contact_frames(terrain,box)
        self.assertEqual(box_resource_bounds([2,4,2],relative),[0,1,2,2,3,4])
