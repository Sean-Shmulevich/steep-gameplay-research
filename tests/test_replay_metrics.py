import unittest
from engine.replay_metrics import update_metrics

class ReplayMetricsTests(unittest.TestCase):
    def test_count_gate(self):
        for count,expected in [(0,0),(1,0),(2,5)]:
            r=update_metrics([3,4,0,0],existing_count=count,previous_point=[0]*4,lower=[0]*4,upper=[0]*4)
            self.assertEqual(r['distance'],expected)
            self.assertEqual(r['lower'],[3,4,0,0])
    def test_zero_sentinel_and_four_lanes(self):
        r=update_metrics([0,0,0,12],existing_count=2,previous_point=[0,0,5,0],lower=[0]*4,upper=[1]*4)
        self.assertEqual(r['distance'],13)
        self.assertEqual(r['lower'],[0]*4)
        self.assertEqual(r['upper'],[1,1,1,12])
    def test_origin_does_not_disarm_sentinel(self):
        a=update_metrics([0]*4,existing_count=0,previous_point=None,lower=[0]*4,upper=[0]*4)
        b=update_metrics([2,3,4,0],existing_count=1,previous_point=None,lower=a['lower'],upper=a['upper'])
        self.assertEqual(b['lower'],[2,3,4,0])
