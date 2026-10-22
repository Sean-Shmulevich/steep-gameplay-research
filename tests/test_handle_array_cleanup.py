import json
from pathlib import Path
import unittest
from reference.handle_array_cleanup import plan_handle_array_cleanup as plan

class HandleArrayCleanupTests(unittest.TestCase):
    def test_original_cleanup_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/handle_array_cleanup_validation.json').read_text())
        self.assertEqual(r['cases'], 96)
        for row in r['rows']:
            self.assertEqual(plan(**row['inputs']), row['result'])

    def test_aliases_release_once_per_slot(self):
        r = plan([2], [0, 0], 0x8000)
        self.assertEqual(r['status_words'], [0])
        self.assertEqual(r['effects'], [dict(kind='request_retirement', record=0)])
        self.assertFalse(r['descriptor_cleared'])

    def test_release_and_free_flags_are_independent(self):
        self.assertEqual(plan([1], [0], 0x4000)['effects'], [dict(kind='free_storage')])
        self.assertEqual(plan([1], [0], 0x4000)['status_words'], [1])
        self.assertEqual(plan([1], [0], 0x8000)['effects'], [dict(kind='request_retirement', record=0)])
        self.assertEqual(plan([1], [0], 0xc000)['effects'], [])

    def test_nonnull_empty_storage_is_still_freed(self):
        self.assertEqual(plan([], [], 0)['effects'], [dict(kind='free_storage')])
        self.assertEqual(plan([], [], 0, False)['effects'], [])
