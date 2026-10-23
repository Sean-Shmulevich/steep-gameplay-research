import unittest
from engine.examples.retirement_loading_probe import probe

class RetirementLoadingProbeTests(unittest.TestCase):
    def test_full_handoff_exposes_each_unpublished_boundary(self):
        result=probe();rows={r['boundary']:r for r in result['trace']}
        for boundary in ('holder_enqueued','retirement_item_consumed','staged_count_captured'):
            self.assertTrue(rows[boundary]['stop_poll_passes'])
        self.assertEqual(rows['retirement_item_consumed']['staged'],1)
        self.assertEqual(rows['staged_count_captured']['publication_captured'],1)
        self.assertFalse(rows['count_published']['stop_poll_passes'])
        self.assertEqual(rows['loading_batch_captured']['pending'],0)
        self.assertFalse(rows['loading_batch_captured']['stop_poll_passes'])
        self.assertTrue(rows['loading_busy_cleared']['stop_poll_passes'])
        self.assertFalse(result['callback_drain_proved'])
        self.assertFalse(result['disposal_proved'])

    def test_nonzero_count_consumes_retirement_without_loading_work(self):
        result=probe(reacquired_count=True)
        row=next(r for r in result['trace'] if r['boundary']=='retirement_item_consumed')
        self.assertEqual(row['retirement_count'],0)
        self.assertEqual(row['holder_status'],0x80000001)
        self.assertEqual(row['calls'],['clear_queued_bit'])
        self.assertTrue(all(r['loading_ring_count']==0 for r in result['trace']))
        self.assertNotIn('loading_item_consumed',[r['boundary'] for r in result['trace']])
