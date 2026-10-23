import unittest
from engine.action_event_analysis import analyze_action_events


def event(action, thread, start, end):
    return dict(action=action, thread=thread, entry_qpc=start, exit_qpc=end)


class ActionEventAnalysisTests(unittest.TestCase):
    def analyze(self, rows, **kwargs):
        return analyze_action_events(rows, batch_size=2, frequency=1000, **kwargs)

    def test_serial_motif_migrates_and_retains_partial_tail(self):
        rows = [event(1, 7, 0, 1), event(2, 7, 2, 3),
                event(1, 8, 10, 11), event(2, 8, 12, 13), event(1, 9, 20, 21)]
        r = self.analyze(rows, dropped=4)
        self.assertEqual((r['complete_batches'], r['trailing_records']), (2, 1))
        self.assertEqual((r['single_thread_batches'], r['batch_thread_changes']), (2, 1))
        self.assertEqual(r['motif_mismatches'], 0)
        self.assertFalse(r['no_reported_drops'])
        self.assertEqual(r['peak_positive_width_intervals'], 1)

    def test_overlap_with_nonadjacent_long_interval(self):
        r = self.analyze([event(1, 1, 0, 10), event(2, 2, 1, 2), event(1, 3, 3, 4)])
        self.assertEqual(r['entries_overlapping_previous_intervals'], 2)
        self.assertEqual(r['peak_positive_width_intervals'], 2)
        self.assertEqual(r['single_thread_batches'], 0)

    def test_ties_do_not_prove_order_and_zero_width_not_overlap(self):
        r = self.analyze([event(1, 1, 1, 1), event(2, 1, 1, 2)])
        self.assertFalse(r['motif_order_unambiguous'])
        self.assertEqual(r['tied_entry_timestamps'], 1)
        self.assertEqual(r['entries_overlapping_previous_intervals'], 0)

    def test_reordering_and_motif_violation(self):
        r = self.analyze([event(2, 1, 2, 3), event(1, 1, 0, 1), event(2, 1, 4, 5)])
        self.assertEqual(r['reservation_order_inversions'], 1)
        self.assertEqual(r['motif_mismatches'], 1)

    def test_empty_and_invalid(self):
        self.assertFalse(self.analyze([])['motif_order_unambiguous'])
        with self.assertRaises(ValueError):self.analyze([event(1, 1, 3, 2)])
        with self.assertRaises(ValueError):self.analyze([event(True, 1, 1, 2)])
        with self.assertRaises(ValueError):self.analyze([], dropped=-1)
