import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory, run_pose_pair_worker
from engine.pose_flagged_neighbor_update import (
    append_pose_shape_pair, compose_pose_shape_transform, reserve_pose_entry_vector,
    route_pose_flagged_pair_indexed, update_pose_flagged_neighbor, ENTRY_RESERVE_TAG)

P, O, PAIR, NODES, REC, ENT = 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000
BODY_A, BODY_B, KIND_A, KIND_B = 0x7000, 0x7200, 0x8000, 0x8100
ENTRIES_A, ENTRIES_B, LOCAL, SHAPE, MASK = 0x9000, 0x9400, 0xA000, 0xB000, 0xC000
FACTORY, FRAME = 0xF000, 77
IDENTITY = [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, 0, 0, 0]


class Services:
    """Authored recording stand-ins for the tester factory, tester and allocator."""
    def __init__(self, mem, hit=True):
        self.mem = mem; self.log = []; self.hit = hit; self.heap = 0x40000
    @property
    def allocator(self): return self
    def allocate(self, size, align, tag):
        p = self.heap; self.heap += 0x1000; self.mem.add(p, bytearray(size))
        self.log.append(('allocate', size, align, tag)); return p
    def reallocate(self, old, size, align, tag):
        p = self.heap; self.heap += 0x1000
        src = bytes(self.mem.regions[old][:size]); self.mem.add(p, bytearray(src) + bytearray(size - len(src)))
        self.log.append(('reallocate', old, size, align, tag)); return p
    def release(self, p): self.log.append(('release', p))
    def select_tester(self, factory, a, b): self.log.append(('select', factory, a, b)); return 0xE000
    def test_overlap(self, tester, wa, wb, a, b):
        self.log.append(('test', tester, tuple(wa), tuple(wb), a, b))
        return self.hit(a, b) if callable(self.hit) else self.hit
    def create_neighbor(self, owner, pair): self.log.append(('create_neighbor', pair))
    def scratch_allocate(self, size): return 0xABC0
    def scratch_release(self, p): pass
    def tests(self): return [x for x in self.log if x[0] == 'test']


def _transform(values):
    raw = bytearray(0x40)
    for r in range(4):
        for c in range(3):
            struct.pack_into('<f', raw, r * 0x10 + c * 4, values[3 * r + c])
    return raw


def build(*, na=1, nb=1, entries=(), cap=None, state=0, solid_a=0x0C, solid_b=0x0C,
          group=(0x111, 0x222), kind_flags=(4, 4), active=(True, True), null_b=(),
          body_a=IDENTITY, local=IDENTITY, key=9, extra_keys=()):
    mem = PoseFlatMemory()
    mem.add(P, bytearray(0x200)); mem.add(O, bytearray(0x80)); mem.add(PAIR, bytearray(24))
    mem.set_q(O, P); mem.set_q(P + 0x38, NODES); mem.set_q(P + 0x68, FACTORY); mem.set_d(P + 0x180, FRAME)
    keys = [key] + list(extra_keys)
    nodes = bytearray(32 * len(keys))
    for s, k in enumerate(keys):   # right-leaning chain; keys ascending after the root
        struct.pack_into('<iiiIQQ', nodes, 32 * s, -1, s + 1 if s + 1 < len(keys) else -1, s - 1, 0, REC + s * 0x100, k)
        mem.add(REC + s * 0x100, bytearray(0x80))
    mem.add(NODES, nodes); mem.put('<i', P + 0x4C, 0)
    entries = list(entries); cap = len(entries) if cap is None else cap
    mem.set_q(REC + 0x48, ENT if cap else 0); mem.set_d(REC + 0x50, len(entries))
    mem.set_d(REC + 0x54, cap); mem.set_d(REC + 0x58, state)
    if cap:
        mem.add(ENT, bytearray(4 * cap))
        for t, (i, j) in enumerate(entries):
            mem.set_d(ENT + 4 * t, i | j << 16)
    for body, kind, entry_base, n, g, kf, act, flag, base in (
            (BODY_A, KIND_A, ENTRIES_A, na, group[0], kind_flags[0], active[0], solid_a, 0),
            (BODY_B, KIND_B, ENTRIES_B, nb, group[1], kind_flags[1], active[1], solid_b, 16)):
        mem.add(body, bytearray(0x100)); mem.add(kind, bytearray(0x60))
        mem.add(entry_base, bytearray(0x48 * max(n, 1)))
        mem.view(body + 0x40, 0x40)[:] = _transform(body_a if body == BODY_A else IDENTITY)
        mem.set_q(body + 0x30, kind); mem.set_q(body + 0xB8, entry_base); mem.put('<H', body + 0xC0, n)
        mem.put('<H', kind + 0x50, 1); mem.set_b(kind + 0x52, kf); mem.set_q(kind + 0x20, g)
        mem.set_d(kind + 0x1C, FRAME if act else FRAME + 1)
        for j in range(n):
            e = entry_base + 0x48 * j; sh = SHAPE + (base + j) * 0x40; loc = LOCAL + (base + j) * 0x40
            mk = MASK + (base + j) * 0x80
            mem.add(sh, bytearray(0x40)); mem.add(loc, _transform(local)); mem.add(mk, bytearray(0x60))
            mem.set_q(e + 0x10, 0 if (body == BODY_B and j in null_b) else sh); mem.set_q(e + 0x18, loc)
            mem.set_q(e + 0x28, 1); mem.set_q(e + 0x30, 1); mem.set_d(e + 0x38, 1); mem.set_d(e + 0x3C, 1)
            mem.set_b(e + 0x44, flag)
            mem.set_q(sh + 0x20, mk); mem.set_q(mk + 0x48, 1); mem.set_q(mk + 0x50, 1)
    mem.set_q(PAIR, BODY_A); mem.set_q(PAIR + 8, BODY_B); mem.set_q(PAIR + 0x10, key)
    return mem


def entries(mem):
    base = mem.q(REC + 0x48)
    return [(mem.w(base + 4 * k), mem.w(base + 4 * k + 2)) for k in range(mem.d(REC + 0x50))]


class FlaggedNeighborUpdateTests(unittest.TestCase):
    def test_dormant_pair_promotes_only_state_one(self):
        for state, expected in ((1, 2), (3, 3), (4, 4)):
            mem = build(state=state, active=(False, False), entries=[(0, 0)])
            svc = Services(mem)
            update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
            self.assertEqual(mem.d(REC + 0x58), expected)
            self.assertEqual(mem.b(REC + 0x5C), 1)
            self.assertEqual(svc.log, [])
            self.assertEqual(entries(mem), [(0, 0)])     # no empty-state check on this path

    def test_one_active_body_is_not_dormant(self):
        mem = build(state=1, active=(False, True))
        svc = Services(mem)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(len(svc.tests()), 1)

    def test_kind_high_bit_uses_state_nibble(self):
        mem = build(state=1, active=(False, False))
        mem.put('<H', KIND_B + 0x50, 0x8002); mem.set_b(KIND_B + 0x53, 0x32)   # nibble 2: inactive
        update_pose_flagged_neighbor(mem, O, PAIR, 0, Services(mem))
        self.assertEqual(mem.d(REC + 0x58), 2)
        mem = build(state=1, active=(False, False))
        mem.put('<H', KIND_B + 0x50, 0x8002); mem.set_b(KIND_B + 0x53, 0x21)
        svc = Services(mem); update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(len(svc.tests()), 1)

    def test_hit_allocates_entry_vector_and_sets_contact_state(self):
        mem = build(na=2, nb=2, cap=0)
        svc = Services(mem, hit=lambda a, b: a == SHAPE + 0x40 and b == SHAPE + 16 * 0x40)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertIn(('allocate', 32, 0x10, ENTRY_RESERVE_TAG), svc.log)
        self.assertEqual(entries(mem), [(1, 0)])
        self.assertEqual(mem.d(REC + 0x58), 2)
        self.assertEqual(mem.d(REC + 0x54), 8)

    def test_existing_hit_is_not_duplicated_and_miss_swap_removes(self):
        mem = build(na=1, nb=3, entries=[(0, 0), (0, 1), (0, 2), (5, 5)])
        svc = Services(mem, hit=lambda a, b: b == SHAPE + 16 * 0x40 + 0x40)   # only j=1
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        # (0,0) removed -> slot0 = (5,5); (0,2) removed -> its slot takes the last.
        self.assertEqual(entries(mem), [(5, 5), (0, 1)])
        self.assertEqual(mem.d(REC + 0x58), 2)

    def test_all_misses_empty_record_to_state_four(self):
        mem = build(na=1, nb=1, entries=[(0, 0)], state=1)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, Services(mem, hit=False))
        self.assertEqual(entries(mem), [])
        self.assertEqual(mem.d(REC + 0x58), 4)

    def test_null_second_shape_keeps_stale_entry(self):
        mem = build(na=1, nb=1, entries=[(0, 0)], null_b=(0,), state=3)
        svc = Services(mem)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(entries(mem), [(0, 0)])
        self.assertEqual(mem.d(REC + 0x58), 3)
        self.assertEqual(svc.log, [])

    def test_nonsolid_first_shape_removes_its_row_without_tests(self):
        mem = build(na=1, nb=2, solid_a=0x04, entries=[(0, 0), (1, 0), (0, 1), (0, 7)])
        svc = Services(mem)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(entries(mem), [(0, 7), (1, 0)])
        self.assertEqual(svc.tests(), [])

    def test_nonsolid_second_shape_removes_entry(self):
        mem = build(na=1, nb=1, solid_b=0x08, entries=[(0, 0)])
        svc = Services(mem)
        update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(entries(mem), [])
        self.assertEqual(svc.tests(), [])

    def test_group_mask_branches(self):
        def run(group, kind_flags, setup):
            mem = build(group=group, kind_flags=kind_flags); setup(mem)
            svc = Services(mem); update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
            return len(svc.tests())
        zero_q = lambda m: [m.set_q(ENTRIES_A + o, 0) for o in (0x28, 0x30)]
        zero_d = lambda m: [m.set_d(ENTRIES_A + o, 0) for o in (0x38, 0x3C)]
        # different groups: q masks only
        self.assertEqual(run((1, 2), (4, 4), zero_d), 1)
        self.assertEqual(run((1, 2), (4, 4), zero_q), 0)
        # same group without first-kind 0x10: both required
        self.assertEqual(run((1, 1), (4, 4), zero_d), 0)
        self.assertEqual(run((1, 1), (4, 4), zero_q), 0)
        # same group with first-kind 0x10: d masks only; second kind's flag is not read
        self.assertEqual(run((1, 1), (0x14, 4), zero_q), 1)
        self.assertEqual(run((1, 1), (4, 0x14), zero_q), 0)

    def test_shape_mask_pair_cross_test(self):
        mem = build()
        mem.set_q(MASK + 0x48, 2); mem.set_q(MASK + 0x50, 0)          # first: low=2, high=0
        mem.set_q(MASK + 16 * 0x80 + 0x48, 1); mem.set_q(MASK + 16 * 0x80 + 0x50, 2)
        svc = Services(mem); update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(len(svc.tests()), 1)        # second.high & first.low
        mem.set_q(MASK + 16 * 0x80 + 0x50, 1)
        svc = Services(mem); update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        self.assertEqual(svc.tests(), [])

    def test_world_transform_composition_and_query(self):
        body = [0, 1.0, 0, -1.0, 0, 0, 0, 0, 1.0, 10.0, 20.0, 30.0]       # 90 degrees about z
        local = [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, 1.0, 2.0, 3.0]
        mem = build(body_a=body, local=local)
        svc = Services(mem); update_pose_flagged_neighbor(mem, O, PAIR, 0, svc)
        _, tester, wa, wb, a, b = svc.tests()[0]
        self.assertEqual(wa, (0, 1.0, 0, -1.0, 0, 0, 0, 0, 1.0, 8.0, 21.0, 33.0))
        self.assertEqual(wb, (1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0, 1.0, 2.0, 3.0))
        self.assertEqual((a, b), (SHAPE, SHAPE + 16 * 0x40))
        self.assertEqual(svc.log[0], ('select', FACTORY, SHAPE, SHAPE + 16 * 0x40))

    def test_compose_rounds_each_operation_to_float32(self):
        third = struct.unpack('<f', struct.pack('<f', 1 / 3))[0]
        out = compose_pose_shape_transform([third] * 12, [third] * 9 + [0.0, 0.0, 0.0])
        product = struct.unpack('<f', struct.pack('<f', third * third))[0]
        two = struct.unpack('<f', struct.pack('<f', product + product))[0]
        self.assertEqual(out[0], struct.unpack('<f', struct.pack('<f', two + product))[0])

    def test_append_and_reserve_leaves(self):
        mem = build(entries=[(1, 2)], cap=1)
        svc = Services(mem)
        self.assertEqual(append_pose_shape_pair(mem, REC, 0x1FFFF, 3, allocator=svc), 1)
        self.assertEqual(entries(mem), [(1, 2), (0xFFFF, 3)])
        self.assertEqual(svc.log[0][0], 'reallocate'); self.assertEqual(svc.log[0][2], 8)
        reserve_pose_entry_vector(mem, REC + 0x48, 2, allocator=svc)
        self.assertEqual((mem.d(REC + 0x50), mem.d(REC + 0x54)), (2, 2))
        reserve_pose_entry_vector(mem, REC + 0x48, 1, allocator=svc)
        self.assertEqual((mem.d(REC + 0x50), mem.d(REC + 0x54)), (1, 1))     # count clamped
        reserve_pose_entry_vector(mem, REC + 0x48, 0, allocator=svc)
        self.assertEqual(mem.q(REC + 0x48), 0); self.assertEqual(svc.log[-1][0], 'release')
        n = len(svc.log); reserve_pose_entry_vector(mem, REC + 0x48, 0, allocator=svc)
        self.assertEqual(len(svc.log), n)

    def test_router_forwards_found_index(self):
        mem = build(key=9, extra_keys=(12, 15), state=0)
        mem.set_q(PAIR + 0x10, 15)                       # third node -> REC+0x200
        mem.set_d(REC + 0x200 + 0x58, 7)
        svc = Services(mem, hit=False)
        route_pose_flagged_pair_indexed(mem, O, PAIR, svc)
        self.assertEqual(mem.b(REC + 0x200 + 0x5C), 1)
        self.assertEqual(mem.d(REC + 0x200 + 0x58), 4)
        self.assertEqual(mem.b(REC + 0x5C), 0)
        mem.set_q(PAIR + 0x10, 10)
        route_pose_flagged_pair_indexed(mem, O, PAIR, svc)
        self.assertEqual(svc.log[-1], ('create_neighbor', PAIR))


class WorkerFlaggedRouteComposition(unittest.TestCase):
    """run_pose_pair_worker (0x18ddd30) with the flagged route bound to 0x18dfa10."""

    def _worker_fixture(self, keys):
        mem = build(cap=0, extra_keys=(20,))
        pairs = 0xD000
        raw = bytearray()
        for k in keys:
            raw += struct.pack('<QQQ', BODY_A, BODY_B, k)
        mem.add(pairs, raw + bytearray(24))
        mem.set_q(P + 0x170, pairs); mem.set_d(P + 0x178, len(keys)); mem.set_d(P + 0x17C, 0)
        return mem, pairs

    def test_flagged_pairs_update_found_records_and_create_missing(self):
        mem, pairs = self._worker_fixture([9, 11, 20])
        svc = Services(mem)
        run_pose_pair_worker(mem, O, svc, flagged=route_pose_flagged_pair_indexed)
        self.assertEqual(entries(mem), [(0, 0)])
        self.assertEqual(mem.d(REC + 0x58), 2)
        self.assertEqual(mem.b(REC + 0x100 + 0x5C), 1)       # key 20 -> node 1's record
        self.assertEqual([x for x in svc.log if x[0] == 'create_neighbor'], [('create_neighbor', pairs + 24)])
        self.assertEqual(len(svc.tests()), 2)

    def test_unflagged_pairs_do_not_reach_the_handler(self):
        mem, _ = self._worker_fixture([9])
        mem.set_b(KIND_A + 0x52, 0); mem.set_b(KIND_B + 0x52, 0)
        seen = []
        run_pose_pair_worker(mem, O, Services(mem), flagged=route_pose_flagged_pair_indexed,
                             dynamic=lambda m, o, p, s: seen.append(p))
        self.assertEqual(seen, [0xD000])
        self.assertEqual(mem.b(REC + 0x5C), 0)


if __name__ == '__main__':
    unittest.main()
