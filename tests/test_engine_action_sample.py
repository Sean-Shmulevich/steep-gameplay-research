import math
import unittest
from engine.action_sample import combine_directions,publish_vector,f32

class ActionSampleTests(unittest.TestCase):
    def test_opposites_cancel_and_alternate_queries_work(self):
        self.assertEqual(combine_directions(negative_x=(True,False),positive_x=(False,True),positive_y=(False,True),negative_y=(False,False)),[0.,1.,0.,0.])
    def test_diagonal_sample_is_not_silently_normalized(self):
        v=combine_directions(negative_x=(False,False),positive_x=(True,False),positive_y=(True,False),negative_y=(False,False))
        result=publish_vector(v)
        self.assertEqual(result['sampled_vector'],[1.,1.,0.,0.])
        self.assertAlmostEqual(result['magnitude'],math.sqrt(2),places=6)
        self.assertAlmostEqual(result['direction'][0],1/math.sqrt(2),places=6)
    def test_processed_magnitude_and_fourth_lane(self):
        result=publish_vector([0.,0.,0.,2.])
        self.assertEqual(result['magnitude'],2.)
        self.assertEqual(result['sampled_vector'][3],2.)
        self.assertEqual(result['direction'][3],1.)
    def test_small_vector_and_strict_status_boundary(self):
        for value in (0.,1e-6,1e-5):
            result=publish_vector([value,0.,0.,0.])
            self.assertEqual(result['direction'],result['sampled_vector'])
            self.assertFalse(result['status'])
        result=publish_vector([1.0001e-5,0.,0.,0.])
        self.assertTrue(result['status']);self.assertAlmostEqual(result['direction'][0],1.,places=6)
    def test_explicit_seed_branch(self):
        result=publish_vector([2.,0.,0.,0.],rsqrt_estimate=.5)
        self.assertEqual(result['direction'],[1.,0.,0.,0.])
        self.assertTrue(result['normalization_policy'].startswith('caller_supplied'))
        self.assertFalse(result['sample_generation_established'])
    def test_invalid_and_overflow_inputs(self):
        for vector in ([1.,2.],[float('inf'),0.,0.,0.],[1e30,0.,0.,0.]):
            with self.assertRaises(ValueError):publish_vector(vector)
