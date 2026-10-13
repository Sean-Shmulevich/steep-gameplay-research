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


class ComposedActionTests(unittest.TestCase):
    def setUp(self):
        self.queries=dict(negative_x=(False,False),positive_x=(True,False),positive_y=(True,False),negative_y=(False,False))
    def test_default_preserves_diagonal_and_updates_only_processor_marker(self):
        from engine.action_sample import evaluate_two_axis
        state={'flag':0,'stored':[0.,0.,0.,0.]}
        result=evaluate_two_axis(self.queries,processor_policy='default',processor_state=state)
        self.assertEqual(result['sampled_vector'],[1.,1.,0.,0.])
        self.assertEqual(result['processor_state']['flag'],1)
        self.assertEqual(state['flag'],0)
    def test_bypass_does_not_run_first_use_callback(self):
        from engine.action_sample import evaluate_two_axis
        state={'flag':0,'stored':[2.,0.,0.,0.]}
        result=evaluate_two_axis(self.queries,processor_policy='bypass',processor_state=state)
        self.assertEqual(result['processor_state'],state)
        self.assertEqual(result['sampled_vector'],[1.,1.,0.,0.])
    def test_supplied_processor_is_not_replaced_with_default(self):
        from engine.action_sample import evaluate_two_axis
        result=evaluate_two_axis(self.queries,processor_policy='supplied',processed_vector=[.25,0.,0.,0.])
        self.assertEqual(result['sampled_vector'],[.25,0.,0.,0.])
        self.assertEqual(result['raw_vector'],[1.,1.,0.,0.])
        self.assertEqual(result['magnitude'],.25)
    def test_unknown_or_missing_processor_fails(self):
        from engine.action_sample import evaluate_two_axis
        for policy in ('guess','supplied'):
            with self.assertRaises(ValueError):evaluate_two_axis(self.queries,processor_policy=policy)
