import unittest
from engine.pose_grid_contact_frames import grid_contact_frames


class GridFramesTest(unittest.TestCase):
    def test_scaled_translated_inverse_and_relative_frame(self):
        terrain=[[2,0,0],[0,4,0],[0,0,-2],[10,20,30]]
        other=[[1,0,0],[0,1,0],[0,0,1],[12,28,24]]
        inverse,relative=grid_contact_frames(terrain,other)
        self.assertEqual(inverse,[[.5,0,0],[0,.25,0],[0,0,-.5],[-5,-5,15]])
        self.assertEqual(relative,[[.5,0,0],[0,.25,0],[0,0,-.5],[1,2,3]])

    def test_shear_inverse_and_singular_guard(self):
        terrain=[[1,0,0],[2,1,0],[0,0,1],[0,0,0]]
        inverse,relative=grid_contact_frames(terrain,terrain)
        self.assertEqual(inverse[:3],[[1,0,0],[-2,1,0],[0,0,1]])
        self.assertEqual(relative,[[1,0,0],[0,1,0],[0,0,1],[0,0,0]])
        terrain[1]=terrain[0]
        with self.assertRaises(ValueError):grid_contact_frames(terrain,terrain)
