import unittest
from engine.examples.allocation_lifecycle_probe import run_probe


class AllocationLifecycleProbeTests(unittest.TestCase):
    def test_region_retirement_and_metadata_removal_are_distinct(self):
        result=run_probe()
        self.assertTrue(result['registered'])
        self.assertEqual(result['before']['lookup'],'selected')
        self.assertEqual(result['after_retirement'],dict(lookup='fallback',index=1,accounting=0,tags=[255,255]))
        self.assertEqual(result['after_removal'],dict(lookup='fallback',index=255,entry_cleared=True))
        self.assertEqual(result['retirement']['spans_dispatched'],1)
        self.assertEqual((result['maximum_lock_depth'],result['final_lock_depth']),(2,0))

    def test_zero_and_one_target_returns_leave_same_bookkeeping(self):
        zero=run_probe(target_result=0);one=run_probe(target_result=1)
        for field in ('after_retirement','after_removal','retirement'):
            self.assertEqual(zero[field],one[field])
        for result,value in ((zero,0),(one,1)):
            calls=[e for e in result['events'] if e['event']=='external_target']
            self.assertEqual(len(calls),1)
            self.assertEqual((calls[0]['returned'],calls[0]['tags'],calls[0]['accounting']),
                             (value,[255,255],131072))
            self.assertEqual((calls[0]['size'],calls[0]['operation']),(0,0x8000))
            self.assertFalse(result['native_release_proved']);self.assertFalse(result['safe_unload_proved'])
