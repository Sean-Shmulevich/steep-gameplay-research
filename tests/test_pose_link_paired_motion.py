import copy
import unittest
from engine.pose_link_paired_motion import paired_link_point_motion


def body():
    return dict(frame=dict(basis=[[1,0,0],[0,1,0],[0,0,1]],translation=[10,20,30]),
                offset128=[1,0,0],motion1a0=[3,4,5],motion1ac=[0,0,2])


class PairedPointMotionTest(unittest.TestCase):
    def test_both_arms_are_offset_relative(self):
        first=body();second=body();second['offset128']=[0,1,0]
        result=paired_link_point_motion(first,second,[2,0,0],[0,2,0])
        self.assertEqual(result['first']['arm'],[1,0,0])
        self.assertEqual(result['second']['arm'],[0,1,0])
        self.assertEqual(result['first']['point_motion'],[3,6,5])
        self.assertEqual(result['second']['point_motion'],[1,4,5])
        self.assertEqual(result['relative_motion'],[-2,-2,0])
        self.assertEqual(result['second']['center_world'],[10,21,30])

    def test_common_translation_motion_cancels(self):
        first=body();second=copy.deepcopy(first)
        first['motion1ac']=second['motion1ac']=[0,0,0]
        result=paired_link_point_motion(first,second,[2,0,0],[0,5,0])
        self.assertEqual(result['relative_motion'],[0,0,0])

    def test_inputs_are_unchanged_and_nonfinite_is_rejected(self):
        first=body();before=copy.deepcopy(first)
        paired_link_point_motion(first,first,[2,0,0],[2,0,0])
        self.assertEqual(first,before)
        first['motion1ac'][0]=float('nan')
        with self.assertRaises(ValueError):paired_link_point_motion(first,body(),[0,0,0],[0,0,0])
