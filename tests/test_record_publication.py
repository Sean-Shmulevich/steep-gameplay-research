import json
from pathlib import Path
import unittest
from reference.record_publication import plan_record_publication as plan

class RecordPublicationTests(unittest.TestCase):
    def test_original_publication_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/record_publication_validation.json').read_text())
        self.assertEqual(r['cases'], 216)
        for row in r['rows']:
            self.assertEqual(plan(**row['inputs']), row['result'])

    def test_deferred_empty_binding_clears_visibility_override(self):
        r = plan(0, 1, 0x80000005, 0xffffffff, 2, 3, 0)
        self.assertEqual(r['object_pointer'], 1)
        self.assertEqual(r['status_word'], 5)
        self.assertEqual(r['target_flags'], 0xfff80003)
        self.assertTrue(r['publication_queued'])

    def test_mode_one_overrides_context_three(self):
        r = plan(0, 1, 5, 0, 2, 3, 1)
        self.assertEqual(r['status_word'], 0x80000005)
        self.assertFalse(r['publication_queued'])

    def test_different_existing_target_remains_until_other_work(self):
        for context in (0, 3):
            r = plan(2, 1, 5, 0, 2, context, 0)
            self.assertEqual((r['object_pointer'], r['status_word']), (2, 5))
            self.assertEqual(r['publication_queued'], context == 3)

    def test_matching_target_skips_all_changes(self):
        r = plan(1, 1, 5, 0xabcdef12, 2, 3, 0)
        self.assertEqual(r['target_flags'], 0xabcdef12)
        self.assertFalse(r['registry_preparation_requested'])
        self.assertFalse(r['publication_queued'])
