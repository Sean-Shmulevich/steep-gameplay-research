import unittest
from engine.snow_pose_damping import prepare_pose_damping


class PoseDampingTests(unittest.TestCase):
    def test_axis_profiles_and_curve_endpoint_clamping(self):
        speed={'start':0,'index_scale':.5,'segments':[[1,1]]}
        immersion={'start':0,'index_scale':1,'segments':[[2,0]]}
        profiles=[dict(scale=s,speed_curve=speed,immersion_curve=immersion) for s in (1,2,-1)]
        self.assertEqual(prepare_pose_damping(10,.5,profiles),[3,6,-3])
        self.assertEqual(prepare_pose_damping(-1,2,profiles),[2,4,-2])

    def test_missing_axis_profile_does_not_fall_back(self):
        with self.assertRaises(ValueError):prepare_pose_damping(0,0,[])
