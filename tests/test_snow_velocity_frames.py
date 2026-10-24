import unittest
from engine.snow_velocity_frames import physical_body_decay_frames,cached_decay_frames
from engine.snow_velocity_correction import directional_velocity_decay


class SnowVelocityFrameTests(unittest.TestCase):
    def test_scaled_body_uses_inverse_not_transpose(self):
        body=[[2,0,0,9],[0,4,0,8],[0,0,8,7],[10,20,30,6]]
        frames=physical_body_decay_frames(body,lambda x:1/x)
        self.assertEqual([v[3] for v in frames['forward_transform']],[0,0,0,1])
        result=directional_velocity_decay([2,4,8,0],[0]*3,0,
            frames['to_frame'],frames['from_frame'],lambda _:1)
        for actual,expected in zip(result['frame_velocity'],[1,1,1,0]):
            self.assertAlmostEqual(actual,expected,places=6)
        for actual,expected in zip(result['velocity'],[2,4,8,0]):
            self.assertAlmostEqual(actual,expected,places=6)
        self.assertEqual(body[0][3],9)

    def test_singular_body_does_not_get_identity_fallback(self):
        with self.assertRaises(ValueError):
            physical_body_decay_frames([[0]*4]*4,lambda x:1/x)

    def test_cached_axis_order_and_direction_offset_without_normalization(self):
        cache=[[0,1,0,0],[0,0,1,0],[1,0,0,0]]
        result=cached_decay_frames(cache,[10,20,30,9],[0,0,2,8],3,lambda x:1/x)
        self.assertEqual(result['forward_transform'],[
            [1,0,0,0],[0,1,0,0],[0,0,1,0],[10,20,24,1]])

    def test_cached_basis_w_is_preserved(self):
        result=cached_decay_frames([[0,1,0,.25],[0,0,1,.5],[1,0,0,.75]],
                                   [0]*4,[0]*4,0,lambda x:1/x)
        self.assertEqual([v[3] for v in result['from_frame']],[.75,.25,.5])
