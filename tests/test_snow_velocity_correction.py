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
