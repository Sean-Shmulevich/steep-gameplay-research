import struct
import unittest
from functools import cmp_to_key
from engine.pose_group_batches import (run_pose_group_batches, order_pose_groups,
                                       compare_pose_group_work)


def sort_prefix(slots, count, compare):
    # Supplied test policy, not a claim about CRT equal-key ordering.
    slots[:count] = sorted(slots[:count], key=cmp_to_key(compare))


def fixture(weights, capacity=128):
    context = bytearray([0x5a] * 0x450)
    struct.pack_into('<QI', context, 0x418, 0x2000, len(weights))
    struct.pack_into('<QII', context, 0x438, 0x3000, 19, capacity)
    groups = {}
    for i, weight in enumerate(weights):
        group = bytearray(0xa8)
        struct.pack_into('<I', group, 0x98, weight)
        groups[0x4000 + i * 0x100] = group
    arrays = {0x2000: list(groups)}
    batches = {0x3000 + i * 16: bytearray([0xcc] * 16) for i in range(128)}
    return context, arrays, groups, batches


class BatchTests(unittest.TestCase):
    def run_case(self, weights, capacity=128, workers=64):
        context, arrays, groups, batches = fixture(weights, capacity)
        events = []
        def dispatch(n, token):
            count = struct.unpack_from('<I', context, 0x440)[0]
            events.append(('dispatch', n, token, [
                struct.unpack_from('<I', batches[0x3000+i*16])[0] for i in range(count)]))
            self.assertEqual(struct.unpack_from('<I', context, 0x448)[0], 0)
        run_pose_group_batches(context, context_token=0x1000, scalar=.125,
            settings_token=0x9000, worker_capacity=workers, arrays=arrays,
            groups=groups, batches=batches, sort_prefix=sort_prefix,
            grow=lambda c,n: events.append(('grow', n)), dispatch=dispatch,
            finish=lambda c: events.append(('finish', struct.unpack_from('<I', c, 0x440)[0])))
        return context, arrays, groups, batches, events

    def test_threshold_zero_tail_and_indices(self):
        context, arrays, groups, batches, events = self.run_case([0, 12, 13, 0, 1])
        self.assertEqual(events, [('dispatch', 2, 0x1308, [2, 3]), ('finish', 0)])
        self.assertEqual([struct.unpack_from('<I', groups[t], 0x98)[0]
                          for t in arrays[0x2000]], [13, 12, 1, 0, 0])
        for i, token in enumerate(arrays[0x2000]):
            self.assertEqual(struct.unpack_from('<I', groups[token], 0xc)[0], i)
        self.assertEqual(batches[0x3000][4:8], bytes([0xcc]*4))
        self.assertEqual(struct.unpack_from('<Q', batches[0x3010], 8)[0], 0x2010)

    def test_worker_caps_and_zero_worker_finish(self):
        for capacity, expected in [(0, 0), (3, 3), (128, 32)]:
            context, _, _, _, events = self.run_case(list(range(25, 65)), workers=capacity)
            self.assertEqual(events[-1], ('finish', 0))
            if expected:
                self.assertEqual(events[0][1], expected)
                for i in range(expected):
                    self.assertEqual(struct.unpack_from('<fQ', context, 0x14+24*i), (.125, 0x9000))
            else:
                self.assertEqual(events, [('finish', 0)])
            self.assertEqual(context[0x14+24*expected:0x18+24*expected], b'ZZZZ')

    def test_growth_and_all_zero_groups(self):
        *_, events = self.run_case(list(range(25, 45)), capacity=0)
        self.assertEqual(events[:3], [('grow', 8), ('grow', 16), ('grow', 32)])
        *_, events = self.run_case([0]*26)
        self.assertEqual(events[0][3], [25, 1])
        *_, events = self.run_case([])
        self.assertEqual(events, [('finish', 0)])

    def test_signed_work_overflow_and_comparator(self):
        # One huge work value makes the signed accumulator negative, so the
        # following zero-work groups stay in the same batch.
        *_, events = self.run_case([0xffffffff, 0, 0])
        self.assertEqual(events[0][3], [3])
        _, _, groups, _ = fixture([0xffffffff, 0])
        a,b = groups.values()
        self.assertEqual(compare_pose_group_work(a,b), 1)
        # Wrapped contact+pose sum partitions as zero, despite nonzero fields.
        context, arrays, groups, _ = fixture([0xffffffff, 2])
        struct.pack_into('<I', groups[0x4000], 0x48, 1)
        order_pose_groups(context, arrays=arrays, groups=groups, sort_prefix=sort_prefix)
        self.assertEqual(arrays[0x2000], [0x4100, 0x4000])


if __name__ == '__main__':
    unittest.main()
