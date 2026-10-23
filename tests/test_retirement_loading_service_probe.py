import unittest
from engine.examples.retirement_loading_service_probe import run_probe


class RetirementLoadingServiceTests(unittest.TestCase):
    def test_mode_zero_separates_holder_recycling_from_destruction(self):
        result = run_probe()
        self.assertEqual(result['before_batch'], dict(staged=0,pending=1,count=1,
                                                     detached=True,destruction_calls=0))
        self.assertEqual(result['batch']['destruction_calls'], 1)
        self.assertEqual(result['service']['payloads_destroyed'], 0)
        self.assertEqual(result['max_lock_depths']['global_1d8'], 3)
        self.assertTrue(all(v == 0 for v in result['lock_depths'].values()))
        events = result['events']
        self.assertLess(events.index(['signal']), events.index(['batch_start']))
        self.assertLess(events.index(['batch_start']), events.index(['destroy','payload',0]))
        self.assertFalse(result['native_completion_proved'])

    def test_refused_growth_can_finish_counters_without_destroying_payload(self):
        result = run_probe(capacity=0)
        self.assertTrue(result['payload_detached'])
        self.assertEqual(result['before_batch']['pending'], 1)
        self.assertEqual(result['before_batch']['count'], 0)
        self.assertEqual(result['insertions'], [dict(inserted=False,growth_requested=True)])
        self.assertEqual(result['batch']['iterations'], 1)
        self.assertEqual(result['batch']['destruction_calls'], 0)
        self.assertEqual(result['loading'],dict(staged=0,pending=0,busy=0,count=0,head=0))
        self.assertFalse(any(e[0]=='destroy' for e in result['events']))

    def test_mode_one_destroys_in_wrapper_without_loading_publication(self):
        result = run_probe(mode=1)
        self.assertEqual(result['before_batch']['destruction_calls'], 1)
        self.assertEqual(result['service']['payloads_destroyed'], 1)
        self.assertEqual(result['batch']['iterations'], 0)
        self.assertEqual(result['insertions'], [])

    def test_retained_or_reentrant_holder_does_not_enter_loading_pipeline(self):
        for args in ({'references':1},{'processing':1}):
            result = run_probe(**args)
            self.assertFalse(result['payload_detached'])
            self.assertEqual(result['insertions'], [])
            self.assertEqual(result['batch']['iterations'], 0)
