"""Selection guards tested on synthetic storage, not original animation timing."""
import unittest
from unittest.mock import patch
import struct
from engine.pose_channel_observation import capture_pose_interval


class PoseIntervalTests(unittest.TestCase):
    def capture(self, before, after):
        reads = iter([before, after])
        with patch('engine.pose_channel_observation.capture_pose_channels',
                   return_value={'atomic_snapshot': False}) as inner:
            value = capture_pose_interval(lambda plan: next(reads), 0x100000,
                                          [10], None, [(0x200000, b'guard')])
            inner.assert_called_once()
            return value

    def state(self, current=100, previous=200, a=100, b=200, epoch=5):
        return [struct.pack('<4Q', current, previous, a, b), struct.pack('<I', epoch)]

    def test_stable_endpoints_do_not_claim_completion(self):
        state = self.state()
        result = self.capture(state, state)
        b = result['selection_boundary']
        self.assertEqual(b['current_slot_matches'], [0])
        self.assertEqual(b['previous_slot_matches'], [1])
        self.assertFalse(b['animation_completion_established'])
        self.assertFalse(b['aba_excluded'])
        self.assertFalse(result['atomic_snapshot'])

    def test_each_boundary_field_change_rejected(self):
        for change in ({'current': 200}, {'previous': 100}, {'a': 300},
                       {'b': 300}, {'epoch': 6}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'changed'):
                self.capture(self.state(), self.state(**change))

    def test_aliases_external_and_null_are_not_forced_into_one_slot(self):
        for state, matches, alias in ((self.state(a=100,b=100),[0,1],True),
                                      (self.state(current=300),[],False),
                                      (self.state(current=0,a=0,b=0),[],False)):
            b = self.capture(state,state)['selection_boundary']
            self.assertEqual(b['current_slot_matches'],matches)
            self.assertEqual(b['configured_slots_alias'],alias)

    def test_short_read_refused(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.capture([b'', b''], self.state())
