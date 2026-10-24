import unittest
from engine.snow_pose_frequency import prepare_pose_frequencies


class PoseFrequencyTests(unittest.TestCase):
    def run_frequency(self,depth=.03,override=0,scales=(2,3,4),override_scale=5):
        curve={'start':0,'index_scale':1,'segments':[[1,1]]}
        profiles=[dict(scale=s,speed_curve=curve,immersion_curve=curve) for s in scales]
        return prepare_pose_frequencies([7,8,9],.5,.5,depth,override,profiles,
                                        dict(scale=override_scale,curve=curve))

    def test_shallow_override_requires_positive_axis_scale(self):
        r=self.run_frequency()
        self.assertEqual(r['frequencies'],[20,6.75,9])
        self.assertEqual(self.run_frequency(scales=(0,0,0))['frequencies'],[7,8,9])

    def test_override_replaces_z_and_nonpositive_override_scale_falls_back(self):
        r=self.run_frequency(depth=1,override=.5)
        self.assertEqual(r['frequencies'],[4.5,6.75,7.5])
        self.assertEqual(r['branches'][2],'override')
        self.assertEqual(self.run_frequency(override=.5,override_scale=0)['branches'][2],'profile')
