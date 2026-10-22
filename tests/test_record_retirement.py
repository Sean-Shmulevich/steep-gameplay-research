import json
from pathlib import Path
import unittest
from reference.record_retirement import plan_retirement

class RecordRetirementTests(unittest.TestCase):
    def test_original_loop_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/retirement_queue_validation.json').read_text())
        self.assertEqual(receipt['cases'], 144)
        for row in receipt['rows']:
            result = plan_retirement(**row['inputs'])
            self.assertEqual(result, row['result'])
            initial = row['inputs']['status_word']
            if 'object_cleanup' in result['effects']:
                initial ^= row['callback_status_xor']
            self.assertEqual(initial & result['clear_status_mask'], row['status_after_stubs'])

    def test_reacquired_ownership_skips_queued_cleanup(self):
        plan = plan_retirement(0x81000001, True, 0)
        self.assertEqual(plan['effects'], ['clear_queued_bit'])
        self.assertFalse(plan['lifetime_acquisition_proven'])

    def test_null_object_still_attempts_record_reclaim(self):
        self.assertEqual(plan_retirement(0x81000000, False, 0)['effects'],
                         ['clear_queued_bit', 'record_reclaim'])

    def test_disposal_modes_preserve_cleanup_before_reclaim(self):
        for mode, disposal in [(0, 'schedule_object_disposal'), (1, 'append_object_to_disposal_list'),
                               (2, 'append_object_to_disposal_list')]:
            self.assertEqual(plan_retirement(0x01000000, True, mode)['effects'],
                             ['object_cleanup', disposal, 'clear_queued_bit', 'record_reclaim'])

    def test_input_contract(self):
        for args in [(-1, True, 0), (0, 1, 0), (0, True, -1), (2**32, True, 0)]:
            with self.assertRaises(ValueError):
                plan_retirement(*args)
