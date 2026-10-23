import unittest
from engine.examples.command_retirement_probe import run_probe


class RetirementProbeTests(unittest.TestCase):
    def test_full_wrapped_queue_preserved_before_two_new_holders(self):
        r=run_probe()
        self.assertEqual(r['queued'],['prior-3','prior-0','prior-1','prior-2','holder-10','holder-08'])
        self.assertEqual(r['header']['capacity'],16388)
        self.assertTrue(all(x['enqueued'] for x in r['receipts']))
        self.assertFalse(r['disposal_completion_proved'])

    def test_aliased_holders_only_release_after_second_decrement(self):
        r=run_probe(alias=True)
        self.assertEqual(len(r['receipts']),1)
        self.assertEqual(r['queued'][-1],'holder-10')

    def test_empty_failed_growth_sets_both_flags_without_insertion(self):
        r=run_probe(capacity=0,count=0,head=0,allocation_fails=True)
        self.assertEqual(r['queued'],[])
        self.assertEqual(r['statuses'],[1<<24,1<<24])
        self.assertTrue(all(not x['enqueued'] for x in r['receipts']))
