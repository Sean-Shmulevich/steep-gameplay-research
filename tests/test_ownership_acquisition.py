import json
from pathlib import Path
import unittest
from reference.record_retirement import increment_ownership_word, plan_retirement

class OwnershipAcquisitionTests(unittest.TestCase):
    def test_original_acquire_and_queue_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/ownership_acquisition_validation.json').read_text())
        self.assertEqual(r['cases'], 96)
        for row in r['rows']:
            status = row['inputs']['status_word']
            after = increment_ownership_word(status)
            self.assertEqual(after, row['increment'])
            self.assertEqual(row['lock_observations'], [status, after['status_word']])
            self.assertEqual(plan_retirement(after['status_word'], True, 0), row['retirement'])

    def test_zero_count_becomes_owned_before_cleanup(self):
        after = increment_ownership_word(0x81000000)
        self.assertEqual(plan_retirement(after['status_word'], True, 0)['effects'],
                         ['clear_queued_bit'])
        self.assertFalse(after['lifetime_acquisition_proven'])

    def test_low_count_overflow_changes_flags_without_saturating(self):
        after = increment_ownership_word(0x00ffffff)
        self.assertEqual(after['status_word'], 0x01000000)
        self.assertEqual(after['ownership_count'], 0)
        self.assertTrue(after['ownership_overflow'])
        self.assertIn('object_cleanup', plan_retirement(after['status_word'], True, 0)['effects'])
        self.assertEqual(increment_ownership_word(0xffffffff)['status_word'], 0)

    def test_validation(self):
        for bad in (-1, 2**32, True, 1.0):
            with self.assertRaises(ValueError):
                increment_ownership_word(bad)
