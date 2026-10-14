import struct
import unittest
from engine.animation_membership_observation import capture_membership


class AnimationMembershipObservationTests(unittest.TestCase):
    def setUp(self):
        self.base = 0x140000000
        self.entity, self.world, self.graph = 0x100000, 0x200000, 0x300000
        self.source, self.storage, self.kino, self.other = 0x400000, 0x500000, 0x600000, 0x700000
        q = lambda v: struct.pack('<Q', v)
        self.mem = {0x90000: b'identity', self.entity + 0x60: q(self.world),
            self.world + 0x1038: q(self.graph), self.graph: q(self.world),
            self.graph + 0x3af0: q(self.base + 0x1ec7f38),
            self.world + 0x530: struct.pack('<QiI', self.source, 2, 2 | 0x80000000),
            self.graph + 0x3c88: struct.pack('<Qii', self.storage, 0, 3),
            self.source: struct.pack('<2Q', self.kino, self.other),
            self.storage: struct.pack('<3Q', self.kino, self.other, 0xdead),
            self.kino: q(self.base + 0x1f289d0) + bytes(8) + q(self.entity),
            self.other: q(self.base + 0x1f289d0) + bytes(8) + q(0x800000)}
        self.calls = []

    def reader(self, plan):
        self.calls.append(plan)
        result = []
        for address, size in plan:
            if address in self.mem:
                result.append(self.mem[address][:size])
            elif address - 16 in (self.kino, self.other):
                result.append(self.mem[address - 16][16:24])
            else:
                self.fail('Unexpected dereference: ' + hex(address))
        return result

    def capture(self, read=None):
        return capture_membership(read or self.reader, self.entity, self.world,
                                  self.base, [(0x90000, b'identity')])

    def test_source_and_stale_storage_are_not_execution(self):
        result = self.capture()
        self.assertTrue(result['source_membership_observed'])
        self.assertEqual(result['player_kino_source_matches'], [dict(
            source_index=0, storage_indices=[0], unclaimed_prefix_indices=[])])
        self.assertFalse(result['callback_execution_established'])
        self.assertFalse(result['safe_to_step_established'])

    def test_unclaimed_prefix_reported_separately(self):
        self.mem[self.graph + 0x3c88] = struct.pack('<Qii', self.storage, 1, 3)
        self.assertEqual(self.capture()['player_kino_source_matches'][0]['unclaimed_prefix_indices'], [0])

    def test_empty_source_does_not_dereference_old_storage_values(self):
        self.mem[self.world + 0x530] = struct.pack('<QiI', 0, 0, 0)
        result = self.capture()
        self.assertFalse(result['source_membership_observed'])
        self.assertEqual(result['storage_capacity'], 3)
        self.assertEqual(result['player_kino_source_matches'], [])

    def test_replaced_source_array_rejected(self):
        reads = 0
        def reader(plan):
            nonlocal reads
            result = self.reader(plan)
            if any(a == self.source for a, _ in plan):
                reads += 1
                if reads == 2:
                    result[next(i for i, (a, _) in enumerate(plan) if a == self.source)] = bytes(16)
            return result
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.capture(reader)

    def test_oversized_or_invalid_headers_rejected(self):
        for remaining, capacity in ((-1, 3), (4, 3), (0, 1025)):
            self.mem[self.graph + 0x3c88] = struct.pack('<Qii', self.storage, remaining, capacity)
            with self.assertRaisesRegex(ValueError, 'storage'):
                self.capture()

    def test_wrong_world_and_short_transport_rejected(self):
        self.mem[self.entity + 0x60] = struct.pack('<Q', 0xdead)
        with self.assertRaisesRegex(ValueError, 'different world'):
            self.capture()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.capture(lambda plan: [])
