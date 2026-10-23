import unittest
from engine.examples.holder_consumption_probe import run_probe


class HolderConsumptionProbeTests(unittest.TestCase):
    def test_zero_counts_detach_and_recycle(self):
        r=run_probe()
        self.assertTrue(r['payload_detached']);self.assertTrue(r['cleanup']['recycled'])
        self.assertEqual((r['holder_count_or_link'],r['pool_head']),(19,0))
        self.assertEqual(r['payload_flags'],0)
        self.assertFalse(r['disposal_completion_proved'])

    def test_restored_reference_and_separate_count_both_block_recycling(self):
        for kwargs in ({'callback_references':1},{'holder_count':1}):
            r=run_probe(**kwargs)
            self.assertEqual(r['remaining_queue_count'],0)
            self.assertTrue(r['step']['cleanup_called'])
            self.assertFalse(r['payload_detached']);self.assertFalse(r['cleanup']['recycled'])
            self.assertEqual(r['pool_head'],19)

    def test_initial_reference_skips_payload_and_cleanup(self):
        r=run_probe(initial_status=(1<<24)|1)
        self.assertEqual(r['events'],[]);self.assertIsNone(r['cleanup'])
