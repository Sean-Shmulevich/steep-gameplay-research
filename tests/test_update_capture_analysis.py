import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('capture_analysis',Path(__file__).resolve().parents[1]/'scripts/analyze_update_capture.py')
a=importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


def rows(count=3):
    snapshot={'valid':5,'request':7,'runtime':'private-runtime','main':'private-body','rider':'private-rider'}
    return [{'kind':'summary','records':count,'dropped':0,'installed':1,'restored':1,'drained':1}]+[
        {'kind':'record','index':i,'actor':'private-actor','elapsed':a.f32(a.f32(.025)/3),
         'derivative':a.f32(.025),'before':dict(snapshot),'after':dict(snapshot)} for i in range(count)]


class CaptureTimingAnalysisTests(unittest.TestCase):
    def test_exact_subdivision_and_no_private_payload(self):
        result=a.analyze(rows())
        self.assertEqual(result['float32_subdivision_matching_groups'],1)
        self.assertNotIn('private-',str(result))
        self.assertFalse(result['direct_native_substep_index_used'])

    def test_partial_group_not_declared_exact(self):
        self.assertEqual(a.analyze(rows(2))['nonmatching_or_partial_groups'],1)

    def test_missing_counter_or_changed_identity_breaks_group(self):
        for field,value in [('valid',1),('runtime','different'),('request',8)]:
            data=rows(); data[2]['after'][field]=value
            result=a.analyze(data)
            self.assertEqual(result['rejected_timing_records'],1)
            self.assertEqual(result['observed_request_groups'],2)

    def test_malformed_export_rejected(self):
        data=rows(); data.pop()
        with self.assertRaisesRegex(ValueError,'Incomplete'): a.analyze(data)
        data=rows(); data[2]['index']=0
        with self.assertRaisesRegex(ValueError,'indices'): a.analyze(data)

    def test_nonfinite_and_different_derivative_not_matching(self):
        data=rows(); data[1]['elapsed']=None
        self.assertEqual(a.analyze(data)['rejected_timing_records'],1)
        data=rows(); data[2]['derivative']=.026
        self.assertEqual(a.analyze(data)['nonmatching_or_partial_groups'],1)

    def test_counter_decrement_wrap_and_reset(self):
        data=rows()
        for r, before, after in zip(data[1:], (0,-2147483648,-10), (-1,2147483647,0)):
            r['before']['preconsume_counter']=before
            r['after']['preconsume_counter']=after
        result=a.analyze(data)['preconsume_counter']
        self.assertEqual(result['decrement_by_one_pairs'],2)
        self.assertEqual(result['unsigned_delta_histogram'],{10:1,4294967295:2})
        self.assertFalse(result['consumer_execution_proved'])

    def test_counter_unavailable_and_invalid_are_distinct(self):
        data=rows()
        data[1]['before']['preconsume_counter']=0
        data[1]['after']['preconsume_counter']=-1
        data[1]['after']['valid']=0
        result=a.analyze(data)['preconsume_counter']
        self.assertEqual(result['unavailable_pairs'],2)
        self.assertEqual(result['invalid_pairs'],1)
        self.assertEqual(result['available_pairs'],0)

    def test_countdown_discriminates_elapsed_from_consumed(self):
        data=rows()
        for r in data[1:]:
            r['before']['preconsume_timers']=[2,-1]
            r['after']['preconsume_timers']=[2,a.f32(-1-r['elapsed'])]
        result=a.analyze(data)['preconsume_countdown']
        self.assertEqual(result['elapsed_subtraction_matches'],3)
        self.assertEqual(result['distinct_clock_pairs'],3)
        self.assertEqual(result['distinct_consumed_matches'],0)

    def test_countdown_reset_not_subtraction_and_missing_not_zero(self):
        data=rows()
        data[1]['before']['preconsume_timers']=[0,-1]
        data[1]['after']['preconsume_timers']=[2,a.f32(.333)]
        result=a.analyze(data)['preconsume_countdown']
        self.assertEqual(result['available_pairs'],1)
        self.assertEqual(result['unavailable_pairs'],2)
        self.assertEqual(result['elapsed_subtraction_matches'],0)


class WrapperIntervalTests(unittest.TestCase):
    def intervals(self, values):
        data = rows(len(values))
        for r, (start, end, thread) in zip(data[1:], values):
            r.update(entry=start, exit=end, thread=thread)
        return data

    def test_serial_calls_can_migrate_threads(self):
        data = self.intervals([(1, 3, 7), (3, 5, 8), (6, 9, 7)])
        result = a.analyze(data)['wrapper_intervals']
        self.assertEqual(result['same_actor_overlapping_pairs'], 0)
        self.assertEqual(result['thread_changes_between_nonoverlapping_neighbors'], 2)
        self.assertFalse(result['scheduler_exclusion_proved'])
        self.assertFalse(result['input_ingestion_order_proved'])
        self.assertNotIn('private-', str(result))

    def test_nested_overlap_and_reservation_reordering(self):
        data = self.intervals([(3, 4, 8), (1, 10, 7), (5, 6, 9)])
        result = a.analyze(data)['wrapper_intervals']
        self.assertEqual(result['same_actor_overlapping_pairs'], 2)
        self.assertEqual(result['reservation_order_entry_reversals'], 1)

    def test_rebinding_does_not_hide_overlap_but_other_actor_does(self):
        data = self.intervals([(1, 5, 7), (2, 6, 8), (3, 7, 9)])
        data[2]['after']['main'] = 'rebound'
        data[3]['actor'] = 'other-actor'
        self.assertEqual(a.analyze(data)['wrapper_intervals']['same_actor_overlapping_pairs'], 1)

    def test_missing_invalid_and_zero_duration(self):
        data = self.intervals([(1, 1, 7), (4, 3, 8), (5, 6, 9)])
        del data[3]['entry']
        result = a.analyze(data)['wrapper_intervals']
        self.assertEqual(result['zero_duration_intervals'], 1)
        self.assertEqual(result['invalid_intervals'], 1)
        self.assertEqual(result['unavailable_intervals'], 1)
        self.assertEqual(result['same_actor_overlapping_pairs'], 0)
