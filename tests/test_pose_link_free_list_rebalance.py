import struct
import unittest

from engine.pose_link_free_list_rebalance import rebalance_pose_link_free_lists
from engine.pose_pair_link_jobs import run_pose_pair_link_jobs
from engine.pose_pair_link_worker import PoseFlatMemory
from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector
try:
    from tests.test_pose_pair_link_worker import Services
except ImportError:  # discovered with tests/ as top level
    from test_pose_pair_link_worker import Services

P = 0x1000
CTX = 0x2000      # context stride 0x100, three vectors at +0, +0x10, +0x20
DATA = 0x10000


def build(counts, caps=None, tag=0):
    """counts[i] = (c0, c1, c2); elements are unique tags 0x1000*(i+1)+0x100*v+k."""
    mem = PoseFlatMemory(); ctxs = []
    for i, row in enumerate(counts):
        ctx = CTX + 0x100 * i; ctxs.append(ctx); raw = mem.add(ctx, bytearray(0x40))
        for v, n in enumerate(row):
            cap = (caps[i][v] if caps else n)
            base = DATA + 0x1000 * (3 * i + v)
            data = mem.add(base, bytearray(max(cap, 1) * 8))
            for k in range(n): struct.pack_into('<Q', data, 8 * k, tag + 0x10000 * (i + 1) + 0x100 * v + k)
            struct.pack_into('<QII', raw, 0x10 * v, base if cap else 0, n, cap)
    return mem, ctxs


def contents(mem, ctx, v):
    base, n = mem.q(ctx + 0x10 * v), mem.d(ctx + 0x10 * v + 8)
    return [mem.q(base + 8 * k) for k in range(n)]


class RebalanceTests(unittest.TestCase):
    def run_it(self, counts, caps=None, n=None):
        mem, ctxs = build(counts, caps); s = Services(mem)
        rebalance_pose_link_free_lists(mem, ctxs, len(ctxs) if n is None else n, allocator=s)
        return mem, ctxs, s

    def test_surplus_moves_one_hop_per_pass_and_conserves(self):
        mem, ctxs, s = self.run_it([(9, 0, 0), (0, 0, 0), (0, 0, 0)], caps=[(9, 0, 0)] * 3)
        got = [contents(mem, c, 0) for c in ctxs]
        self.assertEqual([len(g) for g in got], [4, 4, 1])      # limit 4; ripple detailed below
        self.assertEqual(sorted(x for g in got for x in g), [0x10000 + k for k in range(9)])

    def test_exact_ripple_values(self):
        # sum 9, n 3 -> limit 4. Pass0: ctx0 9->4, ctx1 gets 5. Pass1: ctx1 5->4, ctx2 gets 1.
        # Pass2: ctx2 1 <= 4. Pass3: ctx0 4 <= 4 ... Pass4: ctx1 4. Final 4,4,1.
        mem, ctxs, s = self.run_it([(9, 0, 0), (0, 0, 0), (0, 0, 0)], caps=[(9, 0, 0)] * 3)
        self.assertEqual([mem.d(c + 8) for c in ctxs], [4, 4, 1])
        # popped from the tail: ctx0 keeps its first four, ctx1 received tail-first order
        self.assertEqual(contents(mem, ctxs[0], 0), [0x10000 + k for k in range(4)])
        self.assertEqual(contents(mem, ctxs[1], 0), [0x10008 - 0 - k for k in range(4)])

    def test_empty_destination_grows_to_eight_then_doubles(self):
        mem, ctxs, s = self.run_it([(20, 0, 0), (0, 0, 0)], caps=[(20, 0, 0), (0, 0, 0)])
        # sum 20, n 2 -> limit 11; ctx0 sends 9 to ctx1: allocate 8, then reallocate 16
        sizes = [e[1:] for e in s.log if e[0] in ('allocate', 'reallocate')]
        self.assertEqual([e[0] for e in s.log], ['allocate', 'reallocate'])
        self.assertEqual(s.log[0][1:], (64, 0x10, 0x28))
        self.assertEqual(mem.d(ctxs[1] + 0xC), 16)
        self.assertEqual([mem.d(c + 8) for c in ctxs], [11, 9])

    def test_three_vectors_use_independent_limits_and_stay_independent(self):
        mem, ctxs, s = self.run_it([(0, 6, 0), (0, 0, 7)], caps=[(0, 6, 0), (0, 0, 7)])
        # vec1: sum 6 -> limit 4, ctx0 6->4; vec2: sum 7 -> limit 4, ctx1 7->4
        self.assertEqual([mem.d(c + 0x18) for c in ctxs], [4, 2])
        self.assertEqual([mem.d(c + 0x28) for c in ctxs], [3, 4])
        self.assertEqual([mem.d(c + 8) for c in ctxs], [0, 0])

    def test_balanced_input_is_untouched(self):
        mem, ctxs, s = self.run_it([(3, 3, 3), (3, 3, 3), (4, 4, 4)])
        self.assertEqual(s.log, [])
        self.assertEqual([mem.d(c + 8) for c in ctxs], [3, 3, 4])

    def test_single_context_never_moves(self):
        mem, ctxs, s = self.run_it([(5, 6, 7)])
        self.assertEqual(s.log, []); self.assertEqual(mem.d(ctxs[0] + 8), 5)

    def test_count_limits_contexts_read(self):
        mem, ctxs, s = self.run_it([(9, 0, 0), (0, 0, 0), (50, 0, 0)], caps=[(9, 0, 0), (0, 0, 0), (50, 0, 0)], n=2)
        self.assertEqual(mem.d(ctxs[2] + 8), 50)
        self.assertEqual([mem.d(c + 8) for c in ctxs[:2]], [5, 4])

    def test_zero_contexts_is_not_asserted(self):
        with self.assertRaises(ZeroDivisionError):
            rebalance_pose_link_free_lists(PoseFlatMemory(), [], 0, allocator=None)


class OrchestrationBindingTests(unittest.TestCase):
    def test_bound_as_rebalance_service_of_pair_link_jobs(self):
        """Contexts are slot owner + 0x28; the unbalanced free list is levelled between stages."""
        mem = PoseFlatMemory(); provider = mem.add(P, bytearray(0x200)); s = Services(mem)
        owners = [0x5000 + 0x100 * i for i in range(3)]
        links = [0x70000 + 0x10 * k for k in range(12)]
        for i, o in enumerate(owners):
            raw = mem.add(o, bytearray(0x80)); struct.pack_into('<Q', provider, 0x70 + 8 * i, o)
            n = 12 if i == 0 else 0
            base = 0x20000 + 0x1000 * i; data = mem.add(base, bytearray(max(n, 8) * 8))
            for k in range(n): struct.pack_into('<Q', data, 8 * k, links[k])
            struct.pack_into('<QII', raw, 0x28, base, n, max(n, 8))
        log = []
        def noop(*a): pass
        dispatcher = bytearray(0x728); struct.pack_into('<I', dispatcher, 0x10, 3)
        def rebalance(ctxs, n):
            log.append((list(ctxs), n))
            rebalance_pose_link_free_lists(mem, ctxs, n, allocator=s)
        run_pose_pair_link_jobs(provider, P, 0x4000, 25, None, current_dispatcher=lambda: dispatcher,
            worker_capacity=lambda d: struct.unpack_from('<I', d, 0x10)[0], retire=noop,
            retire_neighbors=noop, rebalance=rebalance, dispatch=noop, merge_links=noop, merge_neighbors=noop)
        self.assertEqual(log, [([o + 0x28 for o in owners], 3)])
        # sum 12, n 3 -> limit 5: 12 -> 5 (7 sent), 7 -> 5 (2 sent): final 5, 5, 2
        self.assertEqual([mem.d(o + 0x30) for o in owners], [5, 5, 2])
        seen = [x for o in owners for x in contents(mem, o + 0x28, 0)]
        self.assertEqual(sorted(seen), links)       # conservation, no duplicates
        # ctx1 started empty with capacity 8: 7 pushes grow nothing; ctx2 received 2
        self.assertEqual(s.log, [])
        self.assertEqual(struct.unpack_from('<QII', provider, 0x170), (0x4000, 25, 0))


if __name__ == '__main__':
    unittest.main()
