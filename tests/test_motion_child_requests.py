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

class ChildInputEntryTests(unittest.TestCase):
    def test_real_entry_in_original_request_chain(self):
        from engine.motion_child_requests import sample_child_entry
        r = json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/motion_child_input_entry_validation.json').read_text())
        self.assertEqual(len(r['rows']), 32)
        for row in r['rows']:
            result = sample_child_entry(row['active_count'], row['threshold'],
                                        row['cached_profile_bits'])
            self.assertEqual(result.cached_profile_bits, 0x3f200000)
            self.assertTrue(result.actor_flag)
            self.assertEqual(result.within_input_count_threshold, bool(row['entry_flag']))

    def test_unsigned_boundary_and_invalid_inputs(self):
        from engine.motion_child_requests import sample_child_entry
        self.assertFalse(sample_child_entry(0xffffffff, 3, 0).within_input_count_threshold)
        self.assertTrue(sample_child_entry(0xffffffff, 0xffffffff, 0).within_input_count_threshold)
        with self.assertRaises(ValueError): sample_child_entry(-1, 3, 0)
