import unittest
from engine.snow_velocity_correction import preserve_speed_floor


class VelocityCorrectionTests(unittest.TestCase):
    def test_floor_restores_original_direction_not_candidate(self):
        r=preserve_speed_floor([10,0,0,8],[0,1,0,9],5,False)
        self.assertEqual(r,dict(velocity=[5,0,0,0],speed=5,action='original_direction_at_floor'))

    def test_never_accelerates_original_below_floor(self):
        self.assertEqual(preserve_speed_floor([2,0,0,0],[1,0,0,0],5,False)['velocity'],[2,0,0,0])
        self.assertEqual(preserve_speed_floor([0]*4,[0]*4,5,False)['velocity'],[0]*4)

    def test_equality_and_bypass_keep_candidate(self):
        for floor,bypass in [(1,False),(5,True)]:
            self.assertEqual(preserve_speed_floor([10,0,0,0],[0,1,0,0],floor,bypass)['action'],'candidate')


class DirectionalDecayTests(unittest.TestCase):
    def test_axis_order_and_transforms(self):
        from engine.snow_velocity_correction import directional_velocity_decay
        identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
        seen=[]
        def sample(x):seen.append(x);return 1/(1-x)
        r=directional_velocity_decay([4,6,8,99],[1,2,3],1,identity,identity,sample)
        self.assertEqual(seen,[-3,-2,-1])
        self.assertEqual(r['velocity'],[2,2,2,0])

    def test_frames_are_supplied_not_assumed_identity(self):
        from engine.snow_velocity_correction import directional_velocity_decay
        swap=[[0,1,0,0],[1,0,0,0],[0,0,1,0]]
        r=directional_velocity_decay([1,2,3,0],[0,0,0],1,swap,swap,lambda _:1)
        self.assertEqual(r['frame_velocity'],[2,1,3,0])
        self.assertEqual(r['velocity'],[1,2,3,0])


class ContactReturnTests(unittest.TestCase):
    def run_case(self,**kw):
        from engine.snow_velocity_correction import contact_return_candidate
        args=dict(velocity=[0,0,-2,0],direction=[0,0,1,0],duration=0,strength=1,
                  disabled=False,lower=[-100]*3,upper=[100]*3)
        args.update(kw);return contact_return_candidate(**args)

    def test_half_second_window_and_inward_only(self):
        self.assertEqual(self.run_case()['velocity'],[0,0,0,0])
        self.assertEqual(self.run_case(duration=.25)['velocity'],[0,0,-1,0])
        self.assertFalse(self.run_case(duration=.5)['correction_applied'])
        self.assertFalse(self.run_case(velocity=[0,0,2,0])['correction_applied'])

    def test_disabled_still_clamps_and_no_normalization(self):
        self.assertEqual(self.run_case(disabled=True,lower=[-1]*3)['velocity'],[0,0,-1,0])
        self.assertEqual(self.run_case(direction=[0,0,2,0])['velocity'],[0,0,6,0])


class ConnectedCorrectionTests(unittest.TestCase):
    def test_floor_can_override_complete_inward_removal(self):
        from engine.snow_velocity_correction import correct_linear_velocity
        identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
        args=dict(original=[0,0,-4,0],rates=[1]*3,elapsed=.1,to_frame=identity,
                  from_frame=identity,sample_decay=lambda _: .5,direction=[0,0,1,0],
                  duration=0,strength=1,disabled=False,lower=[-100]*3,upper=[100]*3,
                  floor=2,bypass=False)
        r=correct_linear_velocity(**args)
        self.assertEqual(r['decay']['velocity'],[0,0,-2,0])
        self.assertEqual(r['contact']['velocity'],[0,0,0,0])
        self.assertEqual(r['selected']['velocity'],[0,0,-2,0])
        args['bypass']=True
        self.assertEqual(correct_linear_velocity(**args)['selected']['velocity'],[0,0,0,0])

    def test_floor_is_not_followed_by_an_invented_second_clamp(self):
        from engine.snow_velocity_correction import correct_linear_velocity
        identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
        r=correct_linear_velocity([10,0,0,0],[1]*3,1,identity,identity,lambda _:0,
                                  [0,0,1,0],1,1,True,[-5]*3,[5]*3,8,False)
        self.assertEqual(r['contact']['velocity'],[0,0,0,0])
        self.assertEqual(r['selected']['velocity'],[8,0,0,0])
