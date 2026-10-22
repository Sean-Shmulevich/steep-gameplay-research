import json
from pathlib import Path
import unittest
from reference.record_publication import complete_record_publication as complete, transfer_publication_count as transfer

class PublicationCompletionTests(unittest.TestCase):
    def test_original_drain_and_transfer_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/publication_completion_validation.json').read_text())
        self.assertEqual(r['cases'], 64)
        for row in r['rows']:
            self.assertEqual(complete(**row['inputs']), row['result'])
            expected = row['result']['status_word'] if row['ready_count'] else row['inputs']['status_word']
            self.assertEqual(row['status_after'], expected)
        self.assertEqual(len(r['transfer_cases']), 12)
        for row in r['transfer_cases']:
            self.assertEqual(transfer(row['submitted'], row['ready']), row['result'])

    def test_stale_identifier_does_not_publish(self):
        self.assertEqual(complete(77, 88, 1, 5),
                         dict(identifier_matched=False, status_word=5, notify_object=0))

    def test_matching_null_record_becomes_visible_without_notification(self):
        self.assertEqual(complete(77, 77, 0, 5),
                         dict(identifier_matched=True, status_word=0x80000005, notify_object=0))

    def test_current_object_is_notification_target(self):
        self.assertEqual(complete(77, 77, 2, 5)['notify_object'], 2)

    def test_transfer_preserves_pending_ready_and_wrap(self):
        self.assertEqual(transfer(7, 9), dict(submitted=0, ready=16))
        self.assertEqual(transfer(1, 0xffffffff), dict(submitted=0, ready=0))
