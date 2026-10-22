import unittest
from reference.projected_speed import projected_speed


class ProjectedSpeedTests(unittest.TestCase):
    def test_normal_motion_does_not_increase_input_speed(self):
        r=projected_speed((3,4,100),(0,0,1))
        self.assertEqual(r,{'speed':5.,'projected_velocity':(3.,4.,0.),'normal_dot':100.})
        self.assertEqual(projected_speed((0,0,10),(0,0,1))['speed'],0)

    def test_does_not_silently_normalize_normal(self):
        self.assertEqual(projected_speed((0,0,5),(0,0,2))['speed'],15)
        self.assertEqual(projected_speed((3,4,0),(0,0,0))['speed'],5)

    def test_invalid_shapes_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError): projected_speed((1,2),(0,0,1))
        with self.assertRaises(ValueError): projected_speed((1,2,float('nan')),(0,0,1))
