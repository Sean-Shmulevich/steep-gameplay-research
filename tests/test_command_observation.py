import unittest
from engine.command_observation import summarize_deliveries


def sample(rid, tick=1, storage=123, thread=7):
    return dict(result=rid, function_storage=storage, thread=thread, caller=456,
                entry_tick=tick, exit_tick=tick+1)


class CommandObservationTests(unittest.TestCase):
    def test_overflow_pattern_does_not_conflate_ids_with_shared_storage(self):
        report = summarize_deliveries([1, 2, 3, 4],
            [sample(1, 1), sample(2, 3), sample(2, 5), sample(2, 7)])
        self.assertEqual([r['observed_deliveries'] for r in report['requests']], [1, 3, 0, 0])
        self.assertTrue(report['shared_storage_between_request_ids'])
        self.assertTrue(report['requests'][1]['repeated_delivery_observed'])
        self.assertEqual(report['requests'][2]['status'], 'not_observed')
        self.assertFalse(report['admission_proved'])
        self.assertNotIn('function_storage', repr(report))
        self.assertNotIn('caller', repr(report))

    def test_missing_record_is_not_rejection_or_complete_capture(self):
        for lost in (0, 5):
            report = summarize_deliveries([1], [], dropped_records=lost)
            self.assertEqual(report['requests'][0]['status'], 'not_observed')
            self.assertEqual(report['capture_loss_observed'], bool(lost))
            self.assertFalse(report['drain_or_unload_proved'])

    def test_unlisted_delivery_and_multiple_threads_remain_visible(self):
        report = summarize_deliveries([1], [sample(2, thread=10), sample(2, thread=11)])
        self.assertEqual(report['unknown_request_ids'], [2])
        self.assertFalse(report['requests'][1]['submitted_in_this_manifest'])
        self.assertEqual(report['requests'][1]['observed_threads'], [10, 11])
        self.assertFalse(report['engine_phase_proved'])

    def test_reject_ambiguous_ids_and_bad_clock(self):
        for ids in ([1, 1], [0], [True], [2**64]):
            with self.assertRaises(ValueError):
                summarize_deliveries(ids, [])
        bad = sample(1)
        bad['exit_tick'] = 0
        with self.assertRaises(ValueError):
            summarize_deliveries([1], [bad])
        with self.assertRaises(ValueError):
            summarize_deliveries([], [], dropped_records=-1)
