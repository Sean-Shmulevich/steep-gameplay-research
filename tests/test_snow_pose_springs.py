import unittest
from engine.snow_pose_springs import pose_spring_coefficients
from reference.central_impulse import f32


class PoseSpringTests(unittest.TestCase):
    def test_axis_order_floor_ceiling_and_signed_ratio(self):
        r=pose_spring_coefficients([1,0,10],[1e8,0,-2],[1,1,-.5])
        self.assertEqual([x['source_axis'] for x in r],[1,2,0])
        self.assertEqual(r[0]['stiffness'],f32(1e-7))
        self.assertEqual(r[0]['damping'],0)
        self.assertLess(r[1]['damping'],0)
        self.assertEqual(r[2]['stiffness'],f32(1e12))
        self.assertTrue(all(x['disabled']==0 for x in r))

    def test_mass_and_frequency_change_both_coefficients(self):
        a=pose_spring_coefficients([1]*3,[2]*3,[.5]*3)
        b=pose_spring_coefficients([2]*3,[2]*3,[.5]*3)
        self.assertAlmostEqual(b[0]['stiffness'],2*a[0]['stiffness'],places=4)
        self.assertAlmostEqual(b[0]['damping'],2*a[0]['damping'],places=5)
