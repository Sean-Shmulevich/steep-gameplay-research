import json
from pathlib import Path
import unittest
from reference.record_retirement import assign_owned_record, decrement_ownership_word

class ReferenceReaderTests(unittest.TestCase):
    def test_original_reader_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/reference_reader_validation.json').read_text())
        self.assertEqual(r['cases'], 96)
        for row in r['rows']:
            if row['rejected']:
                states = list(row['initial_statuses'])
                release = decrement_ownership_word(states[row['old_record']])
                states[row['old_record']] = release['status_word']
                want = dict(status_words=states, slot_record=0,
                            retirement_requests=[row['old_record']] if release['request_retirement'] else [])
            else:
                want = assign_owned_record(row['initial_statuses'], row['old_record'], row['lookup_record'])
            self.assertEqual(want, row['result'])
            self.assertEqual(row['bytes_consumed'], 10)
            self.assertEqual('followup_request' in row['events'], row['tag'] == 1)

    def test_alias_assignment_preserves_ownership(self):
        self.assertEqual(assign_owned_record([5], 0, 0),
                         dict(status_words=[5], slot_record=0, retirement_requests=[]))

    def test_distinct_assignment_retires_last_old_reference(self):
        self.assertEqual(assign_owned_record([1, 3], 0, 1),
                         dict(status_words=[0, 4], slot_record=1, retirement_requests=[0]))
