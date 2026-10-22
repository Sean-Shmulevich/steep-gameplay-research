"""Check public receipt's lifecycle invariants and portable invalidation model."""
import json
from pathlib import Path
import unittest
from reference.animation_handle import invalidate_control_record

class SkeletonRecordBindingTests(unittest.TestCase):
    def test_binding_then_invalidation_receipt(self):
        receipt = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/skeleton_record_binding_validation.json').read_text())
        self.assertEqual(receipt['cases'], 64)
        self.assertTrue(receipt['same_registry_verified'])
        for row in receipt['rows']:
            a, r = row['inputs'], row['result']
            count = a['record_count'] + (not a['same_cached_record'])
            self.assertEqual(r['record_count'], count)
            self.assertEqual(r['old_record_count'], a['old_record_count'] - (not a['same_cached_record']))
            expected = invalidate_control_record(a['object_flags'], a['object_flags'],
                                                 1, a['status'], count)
            self.assertEqual(r['object_pointer'], expected['pointer'])
            self.assertEqual(r['status'], expected['status_word'])
            self.assertEqual(r['object_flags'], expected['target_object_flags'])
            self.assertTrue(r['cached_record_unchanged_by_invalidation'])
            reclaimed = (not a['same_cached_record'] and a['old_record_count'] == 1
                         and a['old_status_low24'] == 0)
            self.assertEqual(r['events'], ['lock', 'unlock'] + (['record_reclaim'] if reclaimed else []))
