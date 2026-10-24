import math
import unittest
from engine.snow_pose_angle import pose_row_angle
from engine.snow_pose_soft_row import soft_pose_row_response
from reference.central_impulse import f32


class PoseAngleTests(unittest.TestCase):
    def test_sign_and_w_mask(self):
        r=pose_row_angle([0,0,1,8],[1,0,0,9],[0,1,0,10],math.atan2)
        self.assertEqual(r['numerator'],-1)
        self.assertEqual(r['denominator'],0)
        self.assertEqual(r['angle'],f32(-math.pi/2))

    def test_degenerate_arguments_reach_explicit_service(self):
        calls=[]
        r=pose_row_angle([0]*4,[0]*4,[0]*4,lambda y,x:calls.append((y,x)) or .75)
        self.assertEqual(calls,[(0.,0.)]);self.assertEqual(r['angle'],.75)

    def test_zero_scalar_response(self):
        r=soft_pose_row_response([3]*4,[2]*4,0.,0,[0,0,1,0],[1,0,0,0],[0,1,0,0],atan2=math.atan2)
        self.assertEqual(r['coefficient'],[3]*4)
        self.assertEqual(r['angle_term'],[0]*4)
