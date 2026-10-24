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
