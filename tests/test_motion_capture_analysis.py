import copy
import unittest
from scripts.analyze_motion_capture import ARRAYS, POINTERS, SCALARS, analyze_motion


def row(i=0):
    s = {k: 'abc' for k in POINTERS}
    s.update({k: 0 for k in SCALARS})
    s.update({k: [0] * n for k, n in ARRAYS.items()})
    return dict(actor='private-actor', entry=i*10+1, exit=i*10+5,
                motion_attempted=1, motion_before_valid=1, motion_after_valid=1,
                motion_before=copy.deepcopy(s), motion_after=copy.deepcopy(s),
                frame_valid=1, attribution_valid=1, outer_completion_counter=7,
                substep_ordinal=i, selected_count=3)


class MotionAnalysisTests(unittest.TestCase):
    def test_separates_callback_gap_and_boundary_changes(self):
        a, b, c = row(0), row(1), row(2)
        a['motion_after']['nonzero_counts'][0] = 1
        b['motion_before']['nonzero_counts'][0] = 1
        b['motion_before']['current_input_bits'][0] = 0x80000000
        c['outer_completion_counter'] = 8
        c['substep_ordinal'] = 0
        c['motion_before']['latches'][0] = 1
        result = analyze_motion([a, b, c])
        self.assertEqual(result['counts']['adjacent_same_batch_pairs'], 1)
        self.assertEqual(result['counts']['observed_boundary_pairs'], 1)
        self.assertEqual(result['same_batch_gap_changed_fields'], {'current_input_bits': 1})
        self.assertEqual(result['observed_boundary_changed_fields'], {'latches': 1})
        self.assertEqual(result['within_update_changed_fields']['nonzero_counts'], 2)
        self.assertNotIn('private-actor', str(result))
        self.assertNotIn('abc', str(result))
        self.assertFalse(result['ingestion_execution_proved'])

    def test_rejection_breaks_adjacency(self):
        a, b, c = row(0), row(1), row(2)
        b['motion_after_valid'] = 0
        b.pop('motion_after')
        result = analyze_motion([a, b, c])
        self.assertEqual(result['counts']['valid_pairs'], 2)
        self.assertEqual(result['counts']['after_rejected'], 1)
        self.assertNotIn('adjacent_same_batch_pairs', result['counts'])

    def test_malformed_bits_flags_and_pointers(self):
        for mutate in (lambda r: r['motion_before'].update(motion='no pointer'),
                       lambda r: r.update(motion_before_valid=True),
                       lambda r: r['motion_before'].update(ingested_bits=[-1]*8),
                       lambda r: r['motion_before'].update(baseline_bits=[0]*11)):
            r = row(); mutate(r)
            self.assertEqual(analyze_motion([r])['counts']['malformed_records'], 1)

    def test_overlap_wrong_owner_and_nonsequential(self):
        for field, value in [('entry', 4), ('actor', 'other'), ('frame_valid', 0)]:
            a, b = row(), row(1); b[field] = value
            self.assertEqual(analyze_motion([a,b])['counts']['unqualified_neighbor_pairs'], 1)
        a,b = row(),row(2)
        self.assertEqual(analyze_motion([a,b])['counts']['nonsequential_pairs'], 1)

    def test_missing_and_disabled(self):
        r = row();r.update(motion_attempted=0,motion_before_valid=0,motion_after_valid=0)
        result=analyze_motion([{},r])
        self.assertEqual(result['counts'], {'unavailable_records':1,'disabled_records':1})
