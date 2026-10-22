import json
from pathlib import Path
import unittest
from engine.motion_child_requests import ChildSlot, request_mode_zero, service_child


class MotionChildRequestsTests(unittest.TestCase):
    def test_integrated_original_chain_receipts(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/motion_child_request_validation.json').read_text())
        self.assertEqual(len(r['rows']), 8)
        for row in r['rows']:
            with self.subTest(row=row):
                slot = ChildSlot('old', 6)
                events = []
                for identity in ('new1', 'new2'):
                    slot, added = request_mode_zero(slot, identity)
                    events += added
                    if row['immediate'] and not row['busy']:
                        slot, added = service_child(slot)
                        events += added
                self.assertEqual(events, row['events_before_service'])
                slot, added = service_child(slot)
                events += added
                self.assertEqual(events, row['events_after_service'])
                self.assertEqual(slot, ChildSlot('new2', 0))

    def test_noop_service_and_identity_guard(self):
        slot = ChildSlot('old', 6)
        self.assertEqual(service_child(slot), (slot, []))
        with self.assertRaises(ValueError): request_mode_zero(slot, 'old')
        with self.assertRaises(ValueError): request_mode_zero(slot, '')
