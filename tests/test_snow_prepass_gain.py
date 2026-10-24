import unittest
from engine.snow_prepass_gain import prepass_direction_gain


class PrepassGainTests(unittest.TestCase):
    def run_gain(self,x,flag):
        calls=[]
        def control(v):calls.append(('control',v));return .25+v
        def speed(v):calls.append(('speed',v));return .5
        return prepass_direction_gain(x,flag,7,control,speed),calls

    def test_ordinary_uses_absolute_control_and_no_speed_curve(self):
        self.assertEqual(self.run_gain(-.75,0),(1.,[('control',0.),('control',.75)]))

    def test_special_negative_half_boundary_changes_speed_sampling(self):
        self.assertEqual(self.run_gain(-1,255),(1.,[('control',0.)]))
        self.assertEqual(self.run_gain(-.5,1),(.5,[('control',0.),('speed',7.)]))
        self.assertEqual(self.run_gain(-.25,1)[0],.3125)

    def test_zero_special_uses_origin_once_but_positive_resamples(self):
        self.assertEqual(self.run_gain(-0.,1),(.125,[('control',0.),('speed',7.)]))
        self.assertEqual(self.run_gain(.25,1),(.25,[('control',0.),('control',.25),('speed',7.)]))
