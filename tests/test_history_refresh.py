"""Reset/evaluation composition, validated by history_refresh_validation.json."""
import struct
import unittest
from engine.action_refresh import reset_action
from engine.action_history_action import evaluate_history_action


class HistoryRefreshTests(unittest.TestCase):
    def test_suppressed_refresh_retains_event_and_cached_predicate(self):
        state = bytearray(0xe0)
        state[0x30] = state[0xb8] = 1
        struct.pack_into('<2Q', state, 0xc0, 100, 190)
        state[0x60:0x84] = b'\xff' * 0x24
        result = reset_action(bytes(state), owner_suppressed=True,
                              evaluate=lambda _: self.fail('suppressed evaluation'))
        self.assertEqual(result[0x60:0x84], bytes(0x24))
        self.assertEqual(result[0x30], 1)
        self.assertEqual(result[0xb8:], bytes(state[0xb8:]))

    def test_hold_can_mature_across_suppressed_refresh_without_new_history(self):
        history = bytearray(0x3c0)
        struct.pack_into('<4f', history, 0x1a0, 0, 1, 0, 0)
        struct.pack_into('<f', history, 0x2e0, .75)
        state = bytes(0xe0)
        reads = []
        def refresh(state, now, suppressed):
            def clock():
                reads.append(now)
                return now
            def evaluate(cleared):
                return evaluate_history_action(cleared, bytes(history), (0, 1, 0, 0),
                    direction_kind=0, magnitude_threshold=.5, mode=1,
                    hold_delay=.1, repeat_delay=0,
                    ownership_blocked=lambda: False, read_clock=clock)['snapshot']
            return reset_action(state, owner_suppressed=suppressed, evaluate=evaluate)
        state = refresh(state, 100, False)
        self.assertEqual(state[0x30], 0)
        state = refresh(state, 150, True)
        self.assertEqual(reads, [100])
        self.assertEqual(struct.unpack_from('<Q', state, 0xc0)[0], 100)
        state = refresh(state, 200, False)
        self.assertEqual(state[0x30], 1)
        self.assertEqual(reads, [100, 200])
        self.assertEqual(struct.unpack_from('<f', state, 0x60)[0], .75)
