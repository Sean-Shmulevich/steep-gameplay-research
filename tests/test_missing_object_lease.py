import json
from pathlib import Path
import unittest
from reference.record_retirement import increment_ownership_word, decrement_ownership_word

class MissingObjectLeaseTests(unittest.TestCase):
    def test_original_acquire_release_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/missing_object_lease_validation.json').read_text())
        self.assertEqual(r['cases'], 40)
        for row in r['rows']:
            before = row['inputs']['status_word']
            acquired = increment_ownership_word(before)
            released = decrement_ownership_word(acquired['status_word'])
            self.assertEqual(acquired, row['acquired'])
            self.assertEqual(released, row['released'])
            self.assertEqual(released['status_word'], before)
            self.assertEqual(row['object_pointer'], 0)
            self.assertTrue(row['record_preserved'])
            self.assertEqual('retirement_request' in row['release_events'], released['request_retirement'])
            self.assertEqual(row['acquisition_events'], ['lock', 'record_map_lookup', 'unlock'])

    def test_last_reference_requests_retirement_without_proving_reclamation(self):
        r = decrement_ownership_word(0x81000001)
        self.assertEqual(r['status_word'], 0x81000000)
        self.assertTrue(r['request_retirement'])
        self.assertFalse(r['ownership_underflow'])

    def test_nonlast_release_does_not_request_retirement(self):
        self.assertFalse(decrement_ownership_word(9)['request_retirement'])

    def test_underflow_borrows_flags(self):
        r = decrement_ownership_word(0x01000000)
        self.assertEqual(r['status_word'], 0x00ffffff)
        self.assertTrue(r['ownership_underflow'])
        self.assertFalse(r['request_retirement'])
        self.assertEqual(decrement_ownership_word(0)['status_word'], 0xffffffff)

    def test_input_contract(self):
        for bad in (-1, 2**32, True, 1.0):
            with self.assertRaises(ValueError):
                decrement_ownership_word(bad)
