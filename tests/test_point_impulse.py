import unittest
from engine.point_impulse import apply_point_impulse
from engine.snow_post_pending import summed_submissions

I=[[1,0,0],[0,1,0],[0,0,1]]


class PointImpulseTests(unittest.TestCase):
    def apply(self, **overrides):
        values=dict(linear=[0,0,0],angular=[0,0,0],impulse=[0,2,0],point=[1,0,0],
                    inverse_mass=.5,local_center=[0,0,0],translation=[0,0,0],
                    basis=I,inverse_world_inertia=I)
        values.update(overrides)
        return apply_point_impulse(**values)

    def test_off_center_impulse_changes_rotation(self):
        result=self.apply()
        self.assertEqual(result['linear'],(0,1,0))
        self.assertEqual(result['angular'],(0,0,2))

    def test_transformed_center_and_no_torque_at_center(self):
        result=self.apply(local_center=[1,0,0],translation=[1,0,0],
                          basis=[[0,-1,0],[1,0,0],[0,0,1]],point=[1,1,0])
        self.assertEqual(result['center'],[1,1,0])
        self.assertEqual(result['angular'],(0,0,0))

    def test_forced_type_and_suppression(self):
        self.assertFalse(self.apply(kind=18)['inner_entered'])
        result=self.apply(kind=18,force=True,flags=8)
        self.assertTrue(result['post_dispatch_requested'])
        self.assertEqual(result['linear'],(0,0,0))
        self.assertEqual(result['angular'],(0,0,0))

    def test_zero_inverse_mass_does_not_suppress_angular_arithmetic(self):
        result=self.apply(inverse_mass=0)
        self.assertEqual(result['linear'],(0,0,0))
        self.assertEqual(result['angular'],(0,0,2))

    def test_post_pending_submission_composes(self):
        r=dict(kind=1,enabled=True,a=[0,1,0,0],b=[0,3,0,0],point=[1,0,0,0])
        submission=summed_submissions([r],3,0,.5)[0]
        result=self.apply(impulse=submission['impulse'][:3],point=submission['point'][:3],force=submission['force'])
        self.assertEqual(result['angular'],(0,0,2))
