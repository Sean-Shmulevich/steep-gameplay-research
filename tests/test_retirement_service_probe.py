import unittest
from engine.examples.retirement_service_probe import run_probe


class RetirementServiceProbeTests(unittest.TestCase):
    def test_normal_service_recycles_then_destroys_after_all_guards(self):
        r=run_probe()
        self.assertTrue(r['cleanup'][0]['recycled']);self.assertEqual(r['service']['payloads_destroyed'],1)
        self.assertTrue(all(v==0 for v in r['lock_depths'].values()))
        self.assertEqual(r['max_lock_depths']['registry_b8'],2)
        self.assertEqual(r['max_lock_depths']['global_1d8'],2)
        e=r['events'];self.assertLess(max(i for i,x in enumerate(e) if x[0]=='unlock'),next(i for i,x in enumerate(e) if x[0]=='destroy'))

    def test_mode_zero_dispatches_without_wrapper_destruction(self):
        r=run_probe(mode=0)
        self.assertIn(['dispatch'],r['events']);self.assertEqual(r['service']['payloads_destroyed'],0)
        self.assertTrue(r['payload_detached']);self.assertFalse(r['native_completion_proved'])

    def test_retained_and_reentrant_paths_do_not_destroy(self):
        for args in ({'references':1},{'processing':1}):
            r=run_probe(**args)
            self.assertFalse(r['payload_detached']);self.assertEqual(r['service']['payloads_destroyed'],0)
            self.assertTrue(all(v==0 for v in r['lock_depths'].values()))
