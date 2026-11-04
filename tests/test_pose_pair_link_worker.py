import struct
import unittest
from types import SimpleNamespace

from engine.pose_pair_link_worker import (PoseFlatMemory, acquire_pose_link, find_pose_pair_link,
    process_pose_dynamic_pair, process_pose_static_pair, route_pose_flagged_pair, run_pose_pair_worker,
    reserve_pose_new_link_vector, LINK_BASE_VTABLE, LINK_VTABLE, PAIR_SCRATCH_BYTES)
from engine.pose_body_connectivity_retire import retire_pose_body_connectivity, reserve_pose_pointer_vector
from engine.pose_endpoint_rings import attach_pose_endpoint_rings, detach_pose_endpoint_rings
from engine.pose_link_state_reset import reset_pose_link_state

P, O, PAIRS, N1, N2, BODY, KIND, OLD, FREE, VEC = (0x1000, 0x2000, 0x3000, 0x4000, 0x5000,
                                                    0x6000, 0x7000, 0x8000, 0x9000, 0xA000)


class Services:
    """Authored recording stand-ins for every supplied service."""
    def __init__(self, mem, accept=True, refill_base=0x40000):
        self.mem = mem; self.log = []; self.accept = accept; self.heap = 0x20000; self.links = refill_base
        self.serial = 7
    def allocate(self, size, align, tag):
        p = self.heap; self.heap += 0x1000; self.mem.add(p, bytearray(size)); self.log.append(('allocate', size, align, tag)); return p
    def reallocate(self, old, size, align, tag):
        p = self.heap; self.heap += 0x1000; src = bytes(self.mem.regions[old][:size])
        self.mem.add(p, bytearray(src) + bytearray(size - len(src))); self.log.append(('reallocate', old, size, align, tag)); return p
    def release(self, p): self.log.append(('release', p))
    @property
    def allocator(self): return self
    def scratch_allocate(self, size): self.log.append(('scratch', size)); return 0xABC0
    def scratch_release(self, p): self.log.append(('scratch_release', p))
    def generate_contacts(self, owner, a, b, link, same): self.log.append(('contacts', a, b, link, same))
    def refresh_contact_flag(self, link): self.log.append(('flag', link))
    def release_held(self, link): self.log.append(('held', link)); self.mem.set_q(link + 0x78, 0)
    def external_contacts(self, owner, a, b, link): self.log.append(('external', link))
    def filter(self, provider, link):
        self.log.append(('filter', link)); return self.accept(link) if callable(self.accept) else self.accept
    def update_neighbor(self, owner, pair): self.log.append(('update_neighbor', pair))
    def create_neighbor(self, owner, pair): self.log.append(('create_neighbor', pair))
    def refill_links(self, dest, n):
        self.log.append(('refill', dest, n))
        for i in range(n):
            p = self.links; self.links += 0x100; self.mem.add(p, bytearray(0x90)); self.mem.set_q(dest + 8 * i, p)
    def destroy_link(self, link):
        self.log.append(('destroy', link)); self.mem.set_b(link + 0x84, 0xFC)
    def next_serial(self):
        v = self.serial; self.serial += 1; return v


def world(pairs, tree1=(), tree2=(), free=(), new_cap=0, kinds=(1, 1), c0=(1, 1), aa=(0, 0), flags52=(0, 0)):
    """Small synthetic fixture. tree entries are (key, value) inserted as a right chain."""
    m = PoseFlatMemory()
    prov = m.add(P, bytearray(0x200))
    for nodes, entries, desc in ((N1, tree1, 8), (N2, tree2, 0x38)):
        raw = m.add(nodes, bytearray(max(1, len(entries)) * 32))
        for i, (key, value) in enumerate(sorted(entries)):
            struct.pack_into('<iiiBBxxQQ', raw, i * 32, -1, i + 1 if i + 1 < len(entries) else -1, i - 1, 0, 0, value, key)
        struct.pack_into('<Q', prov, desc, nodes); struct.pack_into('<i', prov, desc + 0x14, 0 if entries else -1)
    for i, kind in enumerate(kinds):
        k = m.add(KIND + i * 0x100, bytearray(0x60)); struct.pack_into('<H', k, 0x50, kind); k[0x52] = flags52[i]
        b = m.add(BODY + i * 0x100, bytearray(0x100)); struct.pack_into('<Q', b, 0x30, KIND + i * 0x100)
        struct.pack_into('<H', b, 0xC0, c0[i]); b[0xAA] = aa[i]
    m.add(PAIRS, b''.join(struct.pack('<QQQ', *p) for p in pairs) + bytes(24))
    struct.pack_into('<QII', prov, 0x170, PAIRS, len(pairs), 0)
    own = m.add(O, bytearray(0x80)); struct.pack_into('<Q', own, 0, P)
    if new_cap:
        m.add(VEC, bytearray(new_cap * 8)); struct.pack_into('<QII', own, 8, VEC, 0, new_cap)
    arr = m.add(FREE, bytearray(max(1, len(free)) * 8 + 64))
    for i, link in enumerate(free):
        m.add(link, bytearray(range(0x90))); struct.pack_into('<Q', arr, i * 8, link)
    struct.pack_into('<QII', own, 0x28, FREE, len(free), len(free) + 8)
    for value in [v for _, v in tree1]:
        if value not in m.regions: m.add(value, bytearray(0x90))
    return m


A, B = BODY, BODY + 0x100


class AcquireTests(unittest.TestCase):
    def test_recycle_pops_last_destroys_then_reinitializes_in_place(self):
        m = world([], free=(0x11000, 0x12000)); s = Services(m)
        link = acquire_pose_link(m, O + 0x28, allocator=s, destroy=s.destroy_link, refill=s.refill_links, next_serial=s.next_serial)
        self.assertEqual(link, 0x12000); self.assertEqual(m.d(O + 0x30), 1)
        self.assertEqual(s.log, [('destroy', 0x12000)])
        self.assertEqual(m.q(link), LINK_VTABLE)
        self.assertEqual([m.q(link + o) for o in range(8, 0x40, 8)], [0] * 7)
        self.assertEqual(m.d(link + 0x40), 7)
        self.assertEqual(m.q(link + 0x58), link + 0x68)
        self.assertEqual((m.d(link + 0x60), m.d(link + 0x64), m.q(link + 0x78), m.d(link + 0x80)), (0, 1, 0, 0xFFFFFFFF))
        # flags read after the destructor rewrote them: 0xFC -> clear bit1, set bit0
        self.assertEqual(m.b(link + 0x84), 0xFD)
        # bytes outside the constructor's writes survive (0x44..0x4f, 0x68..0x77, 0x85..)
        self.assertEqual(bytes(m.view(link + 0x44, 12)), bytes(range(0x44, 0x50)))
        self.assertEqual(bytes(m.view(link + 0x68, 16)), bytes(range(0x68, 0x78)))
        self.assertEqual(LINK_BASE_VTABLE + 8, LINK_VTABLE)

    def test_empty_vector_refills_five_and_returns_unconstructed_last(self):
        m = PoseFlatMemory({VEC: bytearray(struct.pack('<QII', 0, 0, 2))}); s = Services(m)
        link = acquire_pose_link(m, VEC, allocator=s, destroy=s.destroy_link, refill=s.refill_links, next_serial=s.next_serial)
        self.assertEqual(s.log[0], ('allocate', 40, 0x10, 0x28))  # max(0+5, 2*2) = 5
        self.assertEqual(s.log[1], ('refill', 0x20000, 5)); self.assertEqual(len(s.log), 2)
        self.assertEqual(m.d(VEC + 8), 4); self.assertEqual(link, 0x40400)
        self.assertEqual(bytes(m.view(link, 0x90)), bytes(0x90))  # no destroy, no constructor

    def test_empty_vector_with_capacity_five_skips_reserve_and_doubles_otherwise(self):
        m = PoseFlatMemory({VEC: bytearray(struct.pack('<QII', 0x30000, 0, 5)), 0x30000: bytearray(40)}); s = Services(m)
        acquire_pose_link(m, VEC, allocator=s, destroy=None, refill=s.refill_links, next_serial=None)
        self.assertEqual(s.log, [('refill', 0x30000, 5)])
        m = PoseFlatMemory({VEC: bytearray(struct.pack('<QII', 0x30000, 0, 4)), 0x30000: bytearray(32)}); s = Services(m)
        acquire_pose_link(m, VEC, allocator=s, destroy=None, refill=s.refill_links, next_serial=None)
        self.assertEqual(s.log[0], ('reallocate', 0x30000, 64, 0x10, 0x28))

    def test_new_link_reserve_uses_tag_0x25(self):
        m = PoseFlatMemory({VEC: bytearray(struct.pack('<QII', 0, 3, 0))}); s = Services(m)
        reserve_pose_new_link_vector(m.view(VEC, 16), 8, allocator=s)
        self.assertEqual(s.log, [('allocate', 64, 0x10, 0x25)]); self.assertEqual(m.d(VEC + 0xC), 8)


class SearchTests(unittest.TestCase):
    def test_unsigned_search(self):
        m = world([], tree1=((5, 0xA0000), (2**63, 0xB0000)))
        self.assertEqual(find_pose_pair_link(m, P + 8, 2**63), (1, 0xB0000))
        self.assertEqual(find_pose_pair_link(m, P + 8, 6), (-1, None))
        self.assertEqual(find_pose_pair_link(world([]), P + 8, 5), (-1, None))


class DynamicPairTests(unittest.TestCase):
    def run_pair(self, accept, tree=(), aa=(0, 0), held=0):
        m = world([(A, B, 9)], tree1=tree, free=(0x11000,), new_cap=1, aa=aa); s = Services(m, accept)
        if tree: m.set_q(tree[0][1] + 0x78, held); m.set_b(tree[0][1] + 0x84, 0xFF)
        process_pose_dynamic_pair(m, O, PAIRS, s); return m, s

    def test_new_link_copies_pair_and_is_pushed_with_bit1_clear(self):
        m, s = self.run_pair(True)
        self.assertEqual([m.q(0x11000 + o) for o in (8, 0x10, 0x18)], [A, B, 9])
        self.assertEqual(m.q(0x11000 + 0x50), 0x11000); self.assertEqual(m.b(0x11084) & 2, 0)
        self.assertEqual((m.d(O + 0x10), m.q(VEC)), (1, 0x11000))
        self.assertEqual([e[0] for e in s.log], ['destroy', 'contacts', 'flag', 'filter'])
        self.assertEqual(s.log[1], ('contacts', A, B, 0x11000, True))

    def test_rejected_new_link_is_still_pushed_with_bit1(self):
        m, _ = self.run_pair(False)
        self.assertEqual(m.d(O + 0x10), 1); self.assertTrue(m.b(0x11084) & 2)

    def test_found_link_is_never_pushed_and_rejection_clears_bit0(self):
        m, s = self.run_pair(False, tree=((9, 0xA0000),), held=0x55)
        self.assertEqual(m.d(O + 0x10), 0); self.assertEqual(m.b(0xA0084), 0xFE)
        self.assertIn(('held', 0xA0000), s.log); self.assertNotIn('destroy', [e[0] for e in s.log])
        m, _ = self.run_pair(True, tree=((9, 0xA0000),))
        self.assertEqual((m.d(O + 0x10), m.b(0xA0084)), (0, 0xFF))

    def test_external_branch_replaces_held_release(self):
        m, s = self.run_pair(True, tree=((9, 0xA0000),), aa=(0, 0x80), held=0x55)
        self.assertIn(('external', 0xA0000), s.log); self.assertNotIn('held', [e[0] for e in s.log])
        self.assertEqual(m.q(0xA0078), 0x55)

    def test_growth_doubles_new_vector_with_tag_0x25(self):
        m = world([(A, B, 9)], free=(0x11000,), new_cap=1); s = Services(m)
        m.set_d(O + 0x10, 1)
        process_pose_dynamic_pair(m, O, PAIRS, s)
        self.assertIn(('reallocate', VEC, 16, 0x10, 0x25), s.log); self.assertEqual(m.d(O + 0x10), 2)


class StaticAndFlaggedTests(unittest.TestCase):
    def test_static_skip_rules_and_creation(self):
        m = world([(A, B, 9)], free=(0x11000,), kinds=(0x8002, 4)); s = Services(m)
        process_pose_static_pair(m, O, PAIRS, s); self.assertEqual(s.log, [])
        m = world([(A, B, 9)], tree1=((9, 0xA0000),), free=(0x11000,), kinds=(0, 1)); s = Services(m)
        process_pose_static_pair(m, O, PAIRS, s); self.assertEqual(s.log, [])
        m = world([(A, B, 9)], free=(0x11000,), kinds=(4, 0x8002)); s = Services(m)
        process_pose_static_pair(m, O, PAIRS, s)
        self.assertEqual(s.log, [('destroy', 0x11000), ('allocate', 64, 0x10, 0x25)])
        self.assertTrue(m.b(0x11084) & 2); self.assertEqual(m.d(O + 0x10), 1)

    def test_flagged_routes_on_second_tree(self):
        m = world([(A, B, 9)], tree2=((9, 1),)); s = Services(m)
        route_pose_flagged_pair(m, O, PAIRS, s); self.assertEqual(s.log, [('update_neighbor', PAIRS)])
        m = world([(A, B, 9)], tree1=((9, 0xA0000),)); s = Services(m)
        route_pose_flagged_pair(m, O, PAIRS, s); self.assertEqual(s.log, [('create_neighbor', PAIRS)])


class WorkerTests(unittest.TestCase):
    def test_classification_cursor_and_scratch(self):
        calls = []
        def rec(name): return lambda mem, owner, pair, services: calls.append((name, pair))
        def run(**kw):
            calls.clear(); m = world([(A, B, 1), (B, A, 2)], **kw); s = Services(m)
            m.set_d(O + 0x10, 9); m.set_d(O + 0x20, 9)
            run_pose_pair_worker(m, O, s, dynamic=rec('dyn'), static=rec('static'), flagged=rec('flag'))
            return m, s
        m, s = run()
        self.assertEqual(calls, [('dyn', PAIRS), ('dyn', PAIRS + 24)])
        self.assertEqual(s.log, [('scratch', PAIR_SCRATCH_BYTES), ('scratch_release', 0xABC0)])
        self.assertEqual((m.d(O + 0x10), m.d(O + 0x20), m.q(O + 0x58), m.d(O + 0x60), m.d(P + 0x17C)), (0, 0, 0, 0, 3))
        run(kinds=(0x8002, 0x8002), flags52=(0, 4)); self.assertEqual([c[0] for c in calls], ['flag', 'flag'])
        run(c0=(1, 0)); self.assertEqual(calls, [])
        run(kinds=(1, 7)); self.assertEqual([c[0] for c in calls], ['static', 'static'])

    def test_cursor_beyond_count_and_count_reread(self):
        m = world([(A, B, 1), (B, A, 2)]); s = Services(m); m.set_d(P + 0x17C, 5); seen = []
        run_pose_pair_worker(m, O, s, dynamic=lambda *a: seen.append(a))
        self.assertEqual(seen, []); self.assertEqual(m.d(P + 0x17C), 6)
        m = world([(A, B, 1), (B, A, 2)]); s = Services(m)
        def shrink(mem, owner, pair, services): seen.append(pair); mem.set_d(P + 0x178, 0)
        seen.clear(); run_pose_pair_worker(m, O, s, dynamic=shrink); self.assertEqual(seen, [PAIRS])


class RetireToWorkerCompositionTests(unittest.TestCase):
    def test_retired_links_are_recycled_by_the_worker(self):
        """Retire stage (18de440) pushes links onto owner+0x28; the worker pops them LIFO."""
        m = world([(A, B, 1), (B, A, 2)], free=(), new_cap=0)
        m.set_d(O + 0x30, 0); m.set_d(O + 0x34, 0); m.set_q(O + 0x28, 0)
        records = {}
        for t in (0x11000, 0x12000):
            r = m.add(t, bytearray(0x90)); struct.pack_into('<QQ', r, 8, A, B); struct.pack_into('<Q', r, 0, 0xDEAD)
            records[t] = r
        bodies = {A: m.regions[A], B: m.regions[B]}
        for t in records: attach_pose_endpoint_rings(t, 1, records=records, bodies=bodies)
        prov = m.regions[P]; struct.pack_into('<Q', prov, 0x70, O); s = Services(m)
        retire_pose_body_connectivity(prov, [0x11000, 0x12000], 1, queue_owners={O: m.regions[O]}, queue_arrays=m.regions,
            detach=lambda t, sel: detach_pose_endpoint_rings(t, sel, records=records, bodies=bodies),
            reset=lambda t: reset_pose_link_state(records[t], entry_arrays={}, release_contact=None, release_held=None),
            reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=s))
        self.assertEqual(m.d(O + 0x30), 2)
        run_pose_pair_worker(m, O, s)
        self.assertEqual([e[1] for e in s.log if e[0] == 'destroy'], [0x12000, 0x11000])
        self.assertEqual(m.d(O + 0x30), 0)
        new = m.q(O + 8)
        self.assertEqual([m.q(new), m.q(new + 8)], [0x12000, 0x11000])
        self.assertEqual([m.q(0x12000 + 0x18), m.q(0x11000 + 0x18)], [1, 2])
        self.assertEqual(m.d(0x12000 + 0x40) + 1, m.d(0x11000 + 0x40))


if __name__ == '__main__':
    unittest.main()
