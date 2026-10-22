import json
from pathlib import Path
import unittest
from reference.control_record_pool import recycle_null_record, initialize_reused_record

class ControlRecordPoolTests(unittest.TestCase):
    def test_original_reclaim_reuse_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/record_reuse_validation.json').read_text())
        self.assertEqual(r['cases'], 54)
        for row in r['rows']:
            a = row['inputs']
            self.assertEqual(recycle_null_record(**a), row['recycled'])
            self.assertEqual(initialize_reused_record(row['new_identifier'], a['free_head']), row['initialized'])
            self.assertTrue(row['same_slot_reused'])
            self.assertEqual(row['ownership_after_acquire'], 1)

    def test_counts_and_queued_or_reclaimed_flags_block_recycling(self):
        for status, count in [(1, 0), (0, 1), (1 << 24, 0), (1 << 26, 0)]:
            r = recycle_null_record(77, status, count, 3, -1)
            self.assertFalse(r['recycled'])
            self.assertEqual(r['free_head'], -1)
            self.assertEqual(r['count_or_link'], count)

    def test_free_list_link_replaces_reference_count(self):
        r = recycle_null_record(77, 0, 0, 3, -1)
        self.assertEqual((r['free_head'], r['count_or_link']), (3, 0xffffffff))
        self.assertTrue(r['erase_identifier'])

    def test_reserved_interval_and_preserved_mapping_flag(self):
        for identifier, erase in [(0xefffffff, True), (0xf0000000, False),
                                   (0xf7ffffff, False), (0xf8000000, True)]:
            self.assertEqual(recycle_null_record(identifier, 0, 0, 3, -1)['erase_identifier'], erase)
        self.assertFalse(recycle_null_record(77, 1 << 28, 0, 3, -1)['erase_identifier'])

    def test_zero_identifier_marks_without_recycling(self):
        r = recycle_null_record(0, 0, 0, 3, -1)
        self.assertEqual(r['status_word'], 1 << 26)
        self.assertFalse(r['recycled'])
        self.assertEqual(r['free_head'], -1)
