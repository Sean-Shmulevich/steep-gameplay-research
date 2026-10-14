import struct
import unittest

from engine.scheduler_observation import (
    JOBS, TABLE_RVAS, capture_pair, decode_sweep, observation_ranges,
)


class SchedulerObservationTests(unittest.TestCase):
    def setUp(self):
        self.owner, self.base, self.guard = 0x100000, 0x140000000, 0x90000
        self.blocks = []
        for _, _, kind in JOBS:
            block = bytearray(0x64)
            struct.pack_into('<Q', block, 0, self.base + TABLE_RVAS[kind])
            self.blocks.append(bytes(block))
        self.blocks.append(struct.pack('<i', 0))
        self.calls = 0

    def reader(self, plan):
        self.calls += 1
        if plan == [(self.guard, 8)]:
            return [b'identity']
        self.assertEqual(plan, observation_ranges(self.owner))
        return self.blocks.copy()

    def capture(self, reader=None):
        return capture_pair(reader or self.reader, self.owner, self.base,
                            [(self.guard, b'identity')])

    def test_equal_counters_never_assert_pause_safety(self):
        result = self.capture()
        self.assertEqual(self.calls, 6)
        self.assertEqual(result['changes'], {})
        for flag in ('atomic_snapshot', 'safe_to_step_established',
                     'live_player_membership_established'):
            self.assertFalse(result[flag])

    def test_empty_claims_can_have_active_executions(self):
        block = bytearray(self.blocks[4])
        struct.pack_into('<6I', block, 0x4c, 2, 2, 1, 7, 7, 0)
        self.blocks[4] = bytes(block)
        row = decode_sweep(self.blocks, self.base)['AnimationUpdateTime']
        self.assertEqual(row['remaining_to_claim'], 0)
        self.assertEqual(row['executions'], 2)
        self.assertEqual(row['state_name'], 'scheduled')

    def test_changed_counters_retained_without_frame_inference(self):
        def reader(plan):
            if self.calls == 4:
                block = bytearray(self.blocks[4])
                struct.pack_into('<I', block, 0x58, 0xffffffff)
                self.blocks[4] = bytes(block)
            return self.reader(plan)
        result = self.capture(reader)
        self.assertEqual(result['changes']['AnimationUpdateTime']['started'],
                         [0, 0xffffffff])

    def test_guard_failure_aborts_instead_of_returning_valid_report(self):
        def reader(plan):
            result = self.reader(plan)
            return [b'changed!'] if self.calls == 3 else result
        with self.assertRaisesRegex(ValueError, 'after sweep'):
            self.capture(reader)
        self.assertEqual(self.calls, 3)

    def test_wrong_table_and_short_reads_rejected(self):
        self.blocks[0] = bytes(0x64)
        with self.assertRaisesRegex(ValueError, 'table mismatch'):
            self.capture()
        with self.assertRaisesRegex(ValueError, 'incomplete read'):
            self.capture(lambda plan: [b''])

    def test_invalid_plan_does_not_call_transport(self):
        for owner, guards in ((True, [(self.guard, b'x')]),
                              (self.owner, []),
                              (self.owner, [(self.guard, b'x' * 257)])):
            with self.assertRaises(ValueError):
                capture_pair(self.reader, owner, self.base, guards)
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
