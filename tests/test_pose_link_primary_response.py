import unittest
from engine.pose_link_primary_response import link_primary_response
from engine.pose_link_coefficients import link_response_coefficients

class PrimaryResponseTests(unittest.TestCase):
    def compute(self,q=-4,threshold=0,delta=2,factor=2,gain=-1):
        return link_primary_response((0,0,delta),(0,0,1),
            opposite_motion_projection=q,response=gain,combined40=factor,
            offset1c=0,threshold20=threshold)

    def test_larger_magnitude_candidate_retains_its_sign(self):
        r=self.compute()
        self.assertEqual(r['position_candidate'],2)
        self.assertEqual(r['response'],-8)
        self.assertTrue(r['motion_selected'])

    def test_threshold_equality_rejects_motion(self):
        r=self.compute(q=-4,threshold=-4)
        self.assertFalse(r['motion_admitted'])
        self.assertEqual(r['response'],2)

    def test_equal_magnitudes_keep_position_sign(self):
        r=self.compute(delta=8)
        self.assertEqual(r['response'],8)
        self.assertFalse(r['motion_selected'])

    def test_profile_response_feeds_primary_row(self):
        p=dict(field30=1,field40=2,field60=4,field64=2)
        c=link_response_coefficients(p,p,{k:0 for k in p},
            context_scalar=2,default_factor=9,context_flags=12)
        r=self.compute(q=1,delta=6,factor=c['combined40'],gain=c['response'])
        self.assertEqual(r['response'],3)
