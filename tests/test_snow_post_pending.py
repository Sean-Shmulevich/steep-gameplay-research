import unittest
from engine.snow_post_pending import directional_submissions, summed_submissions


class PostPendingTests(unittest.TestCase):
    def record(self, kind=1, enabled=True):
        return dict(kind=kind,enabled=enabled,a=[1,2,3,0],b=[-1,2,-1,0],
                    direction=[1,-2,3,0],point=[4,5,6,0])

    def test_gate_magnitude_is_not_impulse_scale(self):
        records=[self.record(1),self.record(255)]
        self.assertEqual(summed_submissions(records,1,1,.5),
                         summed_submissions(records,100,7,.5))
        result=summed_submissions(records,0,7,.5)
        self.assertEqual([r['index'] for r in result],[1])
        self.assertEqual(result[0]['impulse'],[0,2,1,0])

    def test_enabled_order_and_zero_scale_submission(self):
        records=[self.record(enabled=False),self.record(),self.record()]
        result=directional_submissions(records,0)
        self.assertEqual([r['index'] for r in result],[1,2])
        self.assertTrue(all(r['force'] for r in result))
        self.assertEqual(result[0]['impulse'],[0,0,0,0])
        self.assertEqual(result[0]['point'],[4,5,6,0])

    def test_negative_scale_and_no_input_mutation(self):
        record=self.record()
        result=summed_submissions([record],1,0,-.5)
        self.assertEqual(result[0]['impulse'],[0,-2,-1,0])
        self.assertEqual(record['a'],[1,2,3,0])
        self.assertEqual(summed_submissions([record],-1,0,1),[])


class GateAttenuationTests(unittest.TestCase):
    def test_squared_and_linear_lanes_differ(self):
        from engine.snow_post_pending import attenuate_point_gates
        self.assertEqual(attenuate_point_gates(1,1,1,2,0,0,1),(.25,.5))
        self.assertEqual(attenuate_point_gates(2,3,2,2,.5,.25,1),(.5,.75))

    def test_no_hidden_clamp_and_zero_denominator_rejected(self):
        from engine.snow_post_pending import attenuate_point_gates
        self.assertEqual(attenuate_point_gates(1,1,4,2,0,0,1),(1,-1))
        with self.assertRaises(ValueError):
            attenuate_point_gates(1,1,0,0,0,0,1)
