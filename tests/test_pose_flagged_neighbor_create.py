import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory, route_pose_flagged_pair, run_pose_pair_worker
from engine.pose_flagged_neighbor_create import (
    acquire_pose_neighbor_record, compose_pose_shape_frame, create_pose_flagged_neighbor,
    push_pose_shape_pair, reserve_pose_tagged_vector, NEIGHBOR_BASE_VTABLE, NEIGHBOR_VTABLE)
from engine.pose_neighbor_retire import retire_pose_neighbor_records
from engine.pose_endpoint_rings import attach_pose_endpoint_rings, detach_pose_endpoint_rings
from engine.pose_body_connectivity_retire import reserve_pose_pointer_vector

P, O, PAIRS, N2, A, B, KIND = 0x1000, 0x2000, 0x3000, 0x4000, 0x6000, 0x6100, 0x7000
ARR_A, ARR_B, ALT_B, SHAPES, FILTERS, LOCAL = 0x8000, 0x8400, 0x8800, 0x9000, 0x9800, 0xA000
FREE, REC, CONT, DISP = 0xB000, 0xC000, 0xC800, 0xD000
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
ON = 0x0C        # +0x44 bits 2 and 3


class Services:
    """Authored recording stand-ins: collider selection, overlap, allocator, serial, worker callbacks."""
    def __init__(self, mem, hit=True):
        self.mem = mem; self.log = []; self.hit = hit; self.heap = 0x20000; self.serial = 40
    def allocate(self, size, align, tag):
        p = self.heap; self.heap += 0x1000; self.mem.add(p, bytearray(size)); self.log.append(('allocate', size, align, tag)); return p
    def reallocate(self, old, size, align, tag):
        p = self.heap; self.heap += 0x1000; src = bytes(self.mem.regions[old][:size])
        self.mem.add(p, bytearray(src) + bytearray(size - len(src))); self.log.append(('reallocate', old, size, tag)); return p
    def release(self, p): self.log.append(('release', p))
    @property
    def allocator(self): return self
    def next_serial(self):
        v = self.serial; self.serial += 1; return v
    def select_collider(self, dispatcher, a, b): self.log.append(('select', dispatcher, a, b)); return 0xC0110
    def test_overlap(self, collider, query):
        self.log.append(('overlap', query[2], query[3])); self.last_query = query
        return self.hit(query) if callable(self.hit) else self.hit
    # worker-only services
    def scratch_allocate(self, size): return 0xABC0
    def scratch_release(self, p): pass
    def update_neighbor(self, owner, pair): self.log.append(('update_neighbor', pair))


def put_frame(m, address, basis=IDENTITY, t=(0.0, 0.0, 0.0)):
    for r, row in enumerate(basis):
        for c, v in enumerate(row): m.put('<f', address + r * 0x10 + c * 4, v)
    for c, v in enumerate(t): m.put('<f', address + 0x30 + c * 4, v)


def world(n_a=1, n_b=1, groups=(1, 1), flags52=(4, 4), entry=None, free=(), out_cap=0, key=9, tree=()):
    """Synthetic fixture. Every shape entry passes all masks unless entry(m, address, side, index) edits it."""
    m = PoseFlatMemory()
    prov = m.add(P, bytearray(0x200)); struct.pack_into('<Q', prov, 0x68, DISP)
    raw = m.add(N2, bytearray(32 * max(1, len(tree))))
    for i, (k, v) in enumerate(sorted(tree)):
        struct.pack_into('<iiiBBxxQQ', raw, i * 32, -1, i + 1 if i + 1 < len(tree) else -1, i - 1, 0, 0, v, k)
    struct.pack_into('<QII', prov, 0x38, N2, len(tree), 0); struct.pack_into('<ii', prov, 0x4C, 0 if tree else -1, -1)
    m.add(FILTERS, bytearray(0x60)); struct.pack_into('<QQ', m.regions[FILTERS], 0x48, 1, 1)
    for s in range(8):
        m.add(SHAPES + s * 0x40, bytearray(0x40)); m.set_q(SHAPES + s * 0x40 + 0x20, FILTERS)
    m.add(LOCAL, bytearray(0x40)); put_frame(m, LOCAL)
    for side, (body, arr, n) in enumerate(((A, ARR_A, n_a), (B, ARR_B, n_b))):
        k = m.add(KIND + side * 0x100, bytearray(0x60)); struct.pack_into('<Q', k, 0x20, groups[side]); k[0x52] = flags52[side]
        b = m.add(body, bytearray(0x100)); struct.pack_into('<Q', b, 0x30, KIND + side * 0x100)
        struct.pack_into('<H', b, 0xC0, n); struct.pack_into('<Q', b, 0xB8, arr); put_frame(m, body + 0x40)
        for base in ((arr, ALT_B) if side else (arr,)):
            m.add(base, bytearray(72 * 4))
            for e in range(4):
                o = base + e * 72
                m.set_q(o + 0x10, SHAPES + (side * 4 + e) * 0x40); m.set_q(o + 0x18, LOCAL)
                m.set_q(o + 0x28, 1); m.set_q(o + 0x30, 1); m.set_d(o + 0x38, 1); m.set_d(o + 0x3C, 1); m.set_b(o + 0x44, ON)
                if entry: entry(m, o, side, e)
    m.add(PAIRS, struct.pack('<QQQ', A, B, key) + bytes(24))
    own = m.add(O, bytearray(0x80)); struct.pack_into('<Q', own, 0, P)
    if out_cap: m.add(0xE000, bytearray(out_cap * 8)); struct.pack_into('<QII', own, 0x18, 0xE000, 0, out_cap)
    arr = m.add(FREE, bytearray(8 * max(1, len(free)) + 64))
    for i, rec in enumerate(free): struct.pack_into('<Q', arr, i * 8, rec)
    struct.pack_into('<QII', own, 0x48, FREE, len(free), len(free) + 4)
    return m


def entries(m, record):
    return [m.d(m.q(record + 0x48) + 4 * i) for i in range(m.d(record + 0x50))]


class LeafTests(unittest.TestCase):
    def test_frame_composition_is_float32_in_native_order(self):
        m = PoseFlatMemory(); m.add(0, bytearray(0x40))
        basis = ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        frame = compose_pose_shape_frame((basis, (10.0, 0.0, 0.0)), (IDENTITY, (1.0, 2.0, 3.0)))
        self.assertEqual(frame, (basis, (8.0, 1.0, 3.0)))
        # (1 + 2^-24) + 2^-24 differs from 1 + (2^-24 + 2^-24) in float32: left-to-right order kept.
        e = 2.0 ** -24
        frame = compose_pose_shape_frame((IDENTITY, (0.0, 0.0, 0.0)), (((1.0, e, e),) + IDENTITY[1:], (0.0, 0.0, 0.0)))
        self.assertEqual(frame[0][0], (1.0, e, e))
        frame = compose_pose_shape_frame((((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)), (0.0, 0.0, 0.0)),
                                         (((1.0, e, e),) + IDENTITY[1:], (0.0, 0.0, 0.0)))
        self.assertEqual(frame[0][0][0], 1.0)            # (1 + e) rounds to 1, then + e rounds to 1

    def test_acquire_pops_without_reinit_or_constructs_with_serial(self):
        m = world(free=(REC,)); m.add(REC, bytearray(range(0x60))); s = Services(m)
        self.assertEqual(acquire_pose_neighbor_record(m, O + 0x28, allocator=s, next_serial=s.next_serial), REC)
        self.assertEqual(bytes(m.regions[REC]), bytes(range(0x60))); self.assertEqual(m.d(O + 0x50), 0)
        r = acquire_pose_neighbor_record(m, O + 0x28, allocator=s, next_serial=s.next_serial)
        self.assertEqual(s.log, [('allocate', 0x60, 0x10, 0x29)])
        self.assertEqual((m.q(r), m.d(r + 0x40), m.q(r + 0x48), m.q(r + 0x50), m.d(r + 0x58), m.b(r + 0x5C)),
                         (NEIGHBOR_VTABLE, 40, 0, 0, 0xFFFFFFFF, 0))
        self.assertNotEqual(NEIGHBOR_BASE_VTABLE, NEIGHBOR_VTABLE)

    def test_shape_pair_push_packs_u16s_and_grows_with_tag_0x2a(self):
        m = PoseFlatMemory(); m.add(REC, bytearray(0x60)); s = Services(m)
        self.assertEqual(push_pose_shape_pair(m, REC, 0x10002, 0x3, allocator=s), 0)
        self.assertEqual(s.log, [('allocate', 32, 0x10, 0x2A)]); self.assertEqual(entries(m, REC), [0x00030002])
        for i in range(7): push_pose_shape_pair(m, REC, i, i, allocator=s)
        push_pose_shape_pair(m, REC, 9, 9, allocator=s)
        self.assertEqual(s.log[-1][0::2], ('reallocate', 64)); self.assertEqual(m.d(REC + 0x54), 16)

    def test_tagged_reserve_release_and_clamp(self):
        m = PoseFlatMemory(); m.add(0x100, struct.pack('<QII', 0x9000, 5, 8)); s = Services(m)
        reserve_pose_tagged_vector(m, 0x100, 8, allocator=s, element_size=4, tag=0x2A); self.assertEqual(s.log, [])
        reserve_pose_tagged_vector(m, 0x100, 0, allocator=s, element_size=8, tag=0x27)
        self.assertEqual(s.log, [('release', 0x9000)]); self.assertEqual((m.q(0x100), m.d(0x108), m.d(0x10C)), (0, 0, 0))


class CreateTests(unittest.TestCase):
    def run_create(self, m, hit=True):
        s = Services(m, hit); r = create_pose_flagged_neighbor(m, O, PAIRS, s); return r, s

    def test_zero_count_or_no_hit_creates_nothing(self):
        for m, hit in ((world(n_a=0, n_b=2), True), (world(n_a=2, n_b=2), False)):
            r, s = self.run_create(m, hit)
            self.assertEqual(r, 0); self.assertEqual(m.d(O + 0x20), 0)
            self.assertFalse(any(e[0] == 'allocate' for e in s.log))
        self.assertEqual(len([e for e in s.log if e[0] == 'overlap']), 4)

    def test_hits_share_one_record_pushed_once(self):
        m = world(n_a=2, n_b=3)
        r, s = self.run_create(m, hit=lambda q: q[3] != SHAPES + 5 * 0x40)
        self.assertEqual(entries(m, r), [0x00000000, 0x00020000, 0x00000001, 0x00020001])
        self.assertEqual((m.q(r + 8), m.q(r + 0x10), m.q(r + 0x18), m.d(r + 0x58), m.b(r + 0x5C)), (A, B, 9, 1, 1))
        self.assertEqual((m.d(O + 0x20), m.d(O + 0x24), m.q(m.q(O + 0x18))), (1, 8, r))
        self.assertEqual([e for e in s.log if e[0] == 'allocate'],
                         [('allocate', 0x60, 0x10, 0x29), ('allocate', 32, 0x10, 0x2A), ('allocate', 64, 0x10, 0x27)])
        self.assertEqual(s.log[0], ('select', DISP, SHAPES, SHAPES + 4 * 0x40))

    def test_null_and_disabled_entries_are_skipped(self):
        def edit(m, o, side, e):
            if (side, e) == (0, 0): m.set_q(o + 0x10, 0)
            if (side, e) == (1, 1): m.set_b(o + 0x44, 0x08)        # bit 3 alone is not enough
        r, s = self.run_create(world(n_a=2, n_b=2, entry=edit))
        self.assertEqual([e[1:] for e in s.log if e[0] == 'overlap'], [(SHAPES + 0x40, SHAPES + 4 * 0x40)])

    def test_group_and_mask_branches(self):
        def narrow_only(m, o, side, e):       # wide masks disjoint, narrow intersect
            if side: m.set_q(o + 0x28, 2); m.set_q(o + 0x30, 2)
        cases = [((1, 2), 0, 0),              # cross group: wide test fails
                 ((1, 1), 0, 0),              # same group, no 0x10: both tests required
                 ((1, 1), 0x14, 1)]           # same group, A kind bit 0x10: narrow only
        for groups, f52, want in cases:
            m = world(groups=groups, flags52=(f52, 4), entry=narrow_only); r, s = self.run_create(m)
            self.assertEqual(len([e for e in s.log if e[0] == 'overlap']), want, (groups, f52))
        def no_narrow(m, o, side, e):
            if side: m.set_d(o + 0x38, 0); m.set_d(o + 0x3C, 0)
        m = world(groups=(1, 2), flags52=(0x14, 4), entry=no_narrow)
        self.assertTrue(self.run_create(m)[0])        # cross group ignores the narrow masks
        m = world(); m.set_q(FILTERS + 0x48, 2)
        self.assertEqual(self.run_create(m)[0], 0)    # filter masks (+0x48/+0x50) must cross

    def test_world_frames_reach_the_query(self):
        m = world(); put_frame(m, A + 0x40, t=(1.0, 2.0, 3.0)); put_frame(m, LOCAL, t=(0.5, 0.0, 0.0))
        r, s = self.run_create(m)
        (ba, ta), (bb, tb), sa, sb = s.last_query
        self.assertEqual((ba, ta, bb, tb), (IDENTITY, (1.5, 2.0, 3.0), IDENTITY, (0.5, 0.0, 0.0)))

    def test_rereads_kind_flags_shape_array_and_pair_triple(self):
        def narrow_only(m, o, side, e):
            if side: m.set_q(o + 0x28, 2); m.set_q(o + 0x30, 2)
        m = world(n_b=2, flags52=(0x14, 4), entry=narrow_only)
        for e in range(4): m.set_q(ALT_B + e * 72 + 0x10, SHAPES + 7 * 0x40)
        def swap(q): m.set_q(B + 0xB8, ALT_B); m.set_q(PAIRS + 0x10, 77); m.set_q(KIND + 0x20, 5); return True
        r, s = self.run_create(m, swap)
        self.assertEqual([e[2] for e in s.log if e[0] == 'overlap'], [SHAPES + 4 * 0x40, SHAPES + 7 * 0x40])
        self.assertEqual(m.q(r + 0x18), 77)               # triple read after the first hit; group word cached
        m = world(n_b=2, flags52=(0x14, 4), entry=narrow_only)
        def clear_bit(q): m.set_b(KIND + 0x52, 0x04); return True
        r, s = self.run_create(m, clear_bit)
        self.assertEqual(len([e for e in s.log if e[0] == 'overlap']), 1)   # kind+0x52 reread per shape pair

    def test_recycled_record_keeps_its_old_shape_pair_storage(self):
        m = world(free=(REC,)); m.add(REC, bytearray(0x60)); m.add(CONT, bytearray(16))
        struct.pack_into('<QII', m.regions[REC], 0x48, CONT, 0, 4); m.set_d(REC + 0x40, 1234)
        r, s = self.run_create(m)
        self.assertEqual((r, m.d(r + 0x40), m.q(r + 0x48), entries(m, r)), (REC, 1234, CONT, [0]))
        self.assertEqual([e for e in s.log if e[0] == 'allocate'], [('allocate', 64, 0x10, 0x27)])


class WorkerCompositionTests(unittest.TestCase):
    def worker_world(self, **kw):
        m = world(**kw); prov = m.regions[P]
        struct.pack_into('<QII', prov, 0x170, PAIRS, 1, 0)
        for side in (0, 1): struct.pack_into('<H', m.regions[KIND + side * 0x100], 0x50, 1)
        return m

    def bound(self, m, s):
        s.create_neighbor = lambda owner, pair: create_pose_flagged_neighbor(m, owner, pair, s)
        return lambda mem, owner, pair, services: route_pose_flagged_pair(mem, owner, pair, services)

    def test_worker_flagged_route_builds_a_neighbor_record(self):
        m = self.worker_world(n_a=2, n_b=2); s = Services(m)
        run_pose_pair_worker(m, O, s, flagged=self.bound(m, s), dynamic=None, static=None)
        self.assertEqual(m.d(O + 0x20), 1); r = m.q(m.q(O + 0x18))
        self.assertEqual(entries(m, r), [0, 0x10000, 1, 0x10001]); self.assertEqual(m.d(r + 0x58), 1)
        m = self.worker_world(tree=((9, 0x55),)); s = Services(m)
        run_pose_pair_worker(m, O, s, flagged=self.bound(m, s), dynamic=None, static=None)
        self.assertEqual(s.log, [('update_neighbor', PAIRS)]); self.assertEqual(m.d(O + 0x20), 0)

    def test_indexed_router_miss_reaches_create_with_two_arguments(self):
        """18e0a60 leaves r8d = -1 on a miss; 18e01e0 never reads r8, so create takes (owner, pair)."""
        from engine.pose_flagged_neighbor_update import route_pose_flagged_pair_indexed
        m = self.worker_world(n_a=1, n_b=2, tree=((3, 0x55), (12, 0x66))); s = Services(m)
        s.create_neighbor = lambda owner, pair: create_pose_flagged_neighbor(m, owner, pair, s)
        run_pose_pair_worker(m, O, s, flagged=route_pose_flagged_pair_indexed, dynamic=None, static=None)
        r = m.q(m.q(O + 0x18)); self.assertEqual((m.d(O + 0x20), entries(m, r)), (1, [0, 0x10000]))

    def test_retired_neighbor_record_is_recycled_by_the_flagged_route(self):
        """18de510 queues a state-4 record on owner+0x48; 18e0a60 -> 18e01e0 pops it, unreconstructed."""
        m = self.worker_world(tree=((9, REC),)); m.add(CONT, bytearray(32))
        rec = m.add(REC, bytearray(0x60)); struct.pack_into('<QQQ', rec, 8, A, B, 9)
        struct.pack_into('<QII', rec, 0x48, CONT, 3, 8); struct.pack_into('<IIB', rec, 0x40, 555, 0, 0)
        struct.pack_into('<I', rec, 0x58, 4)
        struct.pack_into('<QII', m.regions[O], 0x48, 0, 0, 0)
        bodies = {A: m.regions[A], B: m.regions[B]}
        attach_pose_endpoint_rings(REC, 0, records=m.regions, bodies=bodies)
        prov = m.regions[P]; struct.pack_into('<Q', prov, 0x70, O); s = Services(m)
        retire_pose_neighbor_records(prov, 1, node_arrays=m.regions, records=m.regions, queue_owners={O: m.regions[O]},
            queue_arrays=m.regions, detach=lambda t, sel: detach_pose_endpoint_rings(t, sel, records=m.regions, bodies=bodies),
            reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=s))
        self.assertEqual((m.d(O + 0x50), m.i(P + 0x4C), m.d(REC + 0x50), m.q(REC + 8)), (1, -1, 0, 0))
        run_pose_pair_worker(m, O, s, flagged=self.bound(m, s), dynamic=None, static=None)
        self.assertEqual(m.d(O + 0x50), 0); self.assertEqual(m.q(m.q(O + 0x18)), REC)
        self.assertEqual((m.q(REC + 8), m.q(REC + 0x10), m.q(REC + 0x18), m.d(REC + 0x58), m.b(REC + 0x5C)), (A, B, 9, 1, 1))
        self.assertEqual((m.d(REC + 0x40), m.q(REC + 0x48), entries(m, REC)), (555, CONT, [0]))
        self.assertNotIn(0x29, [e[3] for e in s.log if e[0] == 'allocate'])


if __name__ == '__main__':
    unittest.main()
