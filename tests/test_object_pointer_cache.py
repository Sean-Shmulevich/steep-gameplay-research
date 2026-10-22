import json
from pathlib import Path
import unittest
from reference.object_pointer_cache import finalize_pointer_cache as build

class ObjectPointerCacheTests(unittest.TestCase):
    def test_original_two_call_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/pointer_cache_validation.json').read_text())
        self.assertEqual(r['cases'], 96)
        for row in r['rows']:
            first = build(**row['inputs'])
            self.assertEqual(first, row['result'])
            self.assertEqual(build(row['inputs']['records'], row['second_mask'], first['values']), row['second_result'])

    def test_hidden_nonempty_cache_does_not_refresh_after_visibility_change(self):
        records = [dict(pointer=123, status=0)]
        first = build(records, 0)
        self.assertEqual(first['values'], [0])
        second = build(records, 2**64-1, first['values'])
        self.assertEqual(second['values'], [0])
        self.assertFalse(second['rebuilt'])
        self.assertFalse(second['lock_requested'])

    def test_sign_override_and_partial_mask(self):
        records = [dict(pointer=0x12345678, status=0), dict(pointer=0x12345678, status=0x80000000)]
        self.assertEqual(build(records, 0xffff0000)['values'], [0x12340000, 0x12345678])

    def test_empty_cache_retries_and_retains_nothing(self):
        first = build([], 0)
        second = build([], 2**64-1, first['values'])
        self.assertTrue(second['rebuilt'])
        self.assertFalse(second['lifetime_retained'])
