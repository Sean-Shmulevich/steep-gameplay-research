import unittest
from engine.snow_pose_controls import prepare_pose_controls


class PoseControlTests(unittest.TestCase):
    def run_controls(self,preferred):
        curve={'start':0,'index_scale':1,'segments':[[0,1]]}
        profile={'scale':2,'speed_curve':curve,'immersion_curve':curve}
        coefficients=[1,2,3]
        result=prepare_pose_controls(config_valid_byte=1,immersion_selector_byte=2,
          primary_immersion=.5,alternate_immersion=.75,speed_argument=5,depth=1,
          override=0,preferred_byte=preferred,defaults=[1,1,1],
          frequency_profiles=[profile]*3,override_profile=None,
          damping_profiles=[profile]*3,frame_coefficients=coefficients)
        self.assertEqual(coefficients,[1,2,3])
        return result

    def test_preferred_scales_third_coefficient_before_yzx_record_conversion(self):
        ordinary=self.run_controls(0);preferred=self.run_controls(255)
        self.assertEqual(preferred['selected_immersion'],.75)
        self.assertEqual(preferred['spring_coefficients'],[1,2,300])
        self.assertEqual(ordinary['records'][0],preferred['records'][0])
        self.assertEqual(ordinary['records'][2],preferred['records'][2])
        self.assertAlmostEqual(preferred['records'][1]['stiffness']/ordinary['records'][1]['stiffness'],100,places=4)
