import functools
import struct
import unittest

from engine.pose_pair_link_merge import (LINK_COMPARATOR, compare_pose_link_order, merge_pose_neighbor_records,
    merge_pose_new_links, reserve_pose_link_merge_vector, reserve_pose_neighbor_merge_vector)
from engine.pose_pair_link_worker import PoseFlatMemory, run_pose_pair_worker
from engine.pose_pair_link_jobs import run_pose_pair_link_jobs, PAIR_WORKER_CALLBACK
from engine.pose_body_connectivity_retire import retire_pose_body_connectivity, reserve_pose_pointer_vector
from engine.pose_dispatch import dispatch_pose_workers, pose_dispatch_serial_atomics
try:
    from tests.test_pose_pair_link_worker import Services
except ImportError:
    from test_pose_pair_link_worker import Services

P = 0x1000


class Svc:
    """Recording stand-ins for the merge services over a PoseFlatMemory."""
    def __init__(self, mem, sort_key=None):
        self.mem = mem; self.log = []; self.heap = 0x100000; self.sort_key = sort_key
    def reserve(self, desc, cap):
        self.log.append(('reserve', desc, cap))
        ptr = self.heap; self.heap += 0x10000; self.mem.add(ptr, bytearray(cap * 8 + 8))
        self.mem.set_q(desc, ptr); self.mem.set_d(desc + 0xC, cap)
    def copy(self, dst, src, n):
        self.log.append(('copy', dst, src, n))
        if n: self.mem.view(dst, n)[:] = bytes(self.mem.view(src, n))
    def sort(self, base, count, size, cmp):
        self.log.append(('sort', base, count, size, cmp))
        items = [self.mem.q(base + 8 * i) for i in range(count)]
        items.sort(key=self.sort_key or (lambda x: 0))
        for i, v in enumerate(items): self.mem.set_q(base + 8 * i, v)
    def attach(self, rec, sel): self.log.append(('attach', rec, sel))
    def insert(self, tree, key, value): self.log.append(('insert', tree, key, value))
    def finish(self, provider): self.log.append(('finish', provider))


def fixture(vectors, off_ptr, off_cnt, links_base=0x40000):
    """provider with one owner per vector; each vector holds record pointers whose +0x18 is the key."""
    mem = PoseFlatMemory(); prov = mem.add(P, bytearray(0x200))
    n = 0
    for i, vec in enumerate(vectors):
        owner = 0x2000 + 0x100 * i
        o = mem.add(owner, bytearray(0x80)); struct.pack_into('<Q', prov, 0x70 + 8 * i, owner)
        arr = mem.add(0x10000 + 0x1000 * i, bytearray(8 * max(1, len(vec))))
        for j, key in enumerate(vec):
            rec = links_base + 0x100 * n; n += 1
            r = mem.add(rec, bytearray(0x90)); struct.pack_into('<Q', r, 0x18, key)
            struct.pack_into('<Q', arr, 8 * j, rec)
        struct.pack_into('<Q', o, off_ptr, 0x10000 + 0x1000 * i); struct.pack_into('<I', o, off_cnt, len(vec))
    return mem


class NewLinkMergeTests(unittest.TestCase):
    def test_concatenates_sorts_attaches_and_inserts(self):
        mem = fixture([[5, 6], [], [7]], 8, 0x10); s = Svc(mem)
        merge_pose_new_links(mem, P, 3, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=s.attach, insert=s.insert)
        recs = [0x40000, 0x40100, 0x40200]
        self.assertEqual(s.log[0], ('reserve', P + 0x28, 3))          # cap 0 -> exactly total
        self.assertEqual([e for e in s.log if e[0] == 'copy'][0][3], 16)
        self.assertEqual(mem.d(P + 0x30), 3)
        self.assertIn(('sort', mem.q(P + 0x28), 3, 8, LINK_COMPARATOR), s.log)
        tail = s.log[s.log.index(('sort', mem.q(P + 0x28), 3, 8, LINK_COMPARATOR)) + 1:]
        self.assertEqual(tail, [x for r, k in zip(recs, (5, 6, 7)) for x in (('attach', r, 1), ('insert', P + 8, k, r))])

    def test_capacity_doubling_and_no_reserve_when_it_fits(self):
        mem = fixture([[1] * 5, [2] * 4], 8, 0x10); s = Svc(mem)
        mem.set_d(P + 0x34, 3); mem.set_d(P + 0x30, 99)
        merge_pose_new_links(mem, P, 2, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=s.attach, insert=s.insert)
        self.assertEqual(s.log[0], ('reserve', P + 0x28, 12))         # 3 -> 6 -> 12 >= 9
        mem2 = fixture([[1] * 5], 8, 0x10); s2 = Svc(mem2)
        mem2.set_d(P + 0x34, 5); mem2.set_q(P + 0x28, 0x70000); mem2.add(0x70000, bytearray(40))
        merge_pose_new_links(mem2, P, 1, reserve=s2.reserve, copy=s2.copy, sort=s2.sort, attach=s2.attach, insert=s2.insert)
        self.assertFalse([e for e in s2.log if e[0] == 'reserve'])
        self.assertEqual(mem2.q(P + 0x28), 0x70000)

    def test_zero_workers_still_sorts_and_walks_nothing(self):
        mem = fixture([], 8, 0x10); s = Svc(mem); mem.set_d(P + 0x30, 4)
        merge_pose_new_links(mem, P, 0, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=s.attach, insert=s.insert)
        self.assertEqual(mem.d(P + 0x30), 0)
        self.assertEqual(s.log, [('sort', 0, 0, 8, LINK_COMPARATOR)])

    def test_count_is_reread_each_pass(self):
        mem = fixture([[1, 2, 3]], 8, 0x10); s = Svc(mem)
        def attach(rec, sel):
            s.attach(rec, sel); mem.set_d(P + 0x30, 1)               # service shrinks the vector
        merge_pose_new_links(mem, P, 1, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=attach, insert=s.insert)
        self.assertEqual(sum(e[0] == 'attach' for e in s.log), 1)

    def test_doubling_that_wraps_is_reported(self):
        mem = fixture([[1]], 8, 0x10); s = Svc(mem)
        mem.set_d(P + 0x34, 0x80000000)
        mem.set_d(0x2000 + 0x10, 0xFFFFFFF0 & ~7)                    # large total: native would spin
        with self.assertRaises(OverflowError):
            merge_pose_new_links(mem, P, 1, reserve=s.reserve, copy=s.copy, sort=s.sort, attach=s.attach, insert=s.insert)

    def test_comparator_orders_by_first_then_second_body_kind(self):
        mem = PoseFlatMemory()
        def link(addr, k1, k2):
            r = mem.add(addr, bytearray(0x20))
            for off, kind in ((8, k1), (0x10, k2)):
                body = addr + 0x1000 + off * 0x10; kd = body + 0x100
                mem.add(body, bytearray(0x40)); mem.add(kd, bytearray(0x60))
                mem.set_q(body + 0x30, kd); mem.set_d(kd + 0x54, kind); mem.set_q(addr + off, body)
            return addr
        a, b, c = link(0x5000, 3, 9), link(0x6000, 3, 4), link(0x7000, 0xFFFFFFFF, 0)
        self.assertEqual(compare_pose_link_order(mem, a, b), 5)
        self.assertEqual(compare_pose_link_order(mem, b, a), -5)
        self.assertEqual(compare_pose_link_order(mem, a, a), 0)
        self.assertEqual(compare_pose_link_order(mem, a, c), 4)       # 3 - 0xffffffff wraps to 4
        self.assertEqual(compare_pose_link_order(mem, c, a), -4)
        order = sorted([a, b, c], key=functools.cmp_to_key(lambda x, y: compare_pose_link_order(mem, x, y)))
        self.assertEqual(order, [c, b, a])   # wrapped difference: 0xffffffff sorts as -1


class NeighborMergeTests(unittest.TestCase):
    def test_concatenates_attaches_with_zero_inserts_and_tails_into_finish(self):
        mem = fixture([[9], [8, 7]], 0x18, 0x20); s = Svc(mem)
        merge_pose_neighbor_records(mem, P, 2, reserve=s.reserve, copy=s.copy, attach=s.attach, insert=s.insert,
                                    finish=s.finish)
        self.assertEqual(s.log[0], ('reserve', P + 0x58, 3))
        self.assertEqual(mem.d(P + 0x60), 3)
        recs = [0x40000, 0x40100, 0x40200]
        self.assertEqual([mem.q(mem.q(P + 0x58) + 8 * i) for i in range(3)], recs)   # no sort
        self.assertEqual(s.log[-7:], [x for r, k in zip(recs, (9, 8, 7)) for x in (('attach', r, 0), ('insert', P + 0x38, k, r))] + [('finish', P)])
        self.assertNotIn(('sort',), [e[:1] for e in s.log])

    def test_reserve_wrappers_use_distinct_tags(self):
        tags = []
        class A:
            def allocate(self, size, align, tag): tags.append(tag); return 0x100
        for fn in (reserve_pose_link_merge_vector, reserve_pose_neighbor_merge_vector):
            d = bytearray(16); fn(d, 4, allocator=A())
        self.assertEqual(tags, [0x22, 0x24])


class OrchestrationCompositionTests(unittest.TestCase):
    def test_worker_links_flow_through_the_real_merge_inside_18ddc40(self):
        mem = PoseFlatMemory(); provider = mem.add(P, bytearray(0x200))
        owners = [0x2000 + 0x100 * i for i in range(3)]
        for i, o in enumerate(owners):
            raw = mem.add(o, bytearray(0x80)); struct.pack_into('<Q', raw, 0, P)
            struct.pack_into('<Q', provider, 0x70 + 8 * i, o)
        kind = mem.add(0x3000, bytearray(0x60)); struct.pack_into('<H', kind, 0x50, 7)
        for b in (0x3100, 0x3200):
            raw = mem.add(b, bytearray(0x100)); struct.pack_into('<Q', raw, 0x30, 0x3000)
        mem.add(0x3800, bytearray(32)); struct.pack_into('<Qi', provider, 8, 0x3800, 0); struct.pack_into('<i', provider, 0x1C, -1)
        npairs = 25
        mem.add(0x4000, b''.join(struct.pack('<QQQ', 0x3100, 0x3200, 100 + k) for k in range(npairs)))
        links = [0x6000 + 0x100 * i for i in range(3)]
        for t in links: mem.add(t, bytearray(0x90))
        s = Services(mem)
        extra_links = []
        for i in range(2):                                           # records another worker would have produced
            r = mem.add(0x7000 + 0x100 * i, bytearray(0x90)); struct.pack_into('<Q', r, 0x18, 500 + i); extra_links.append(0x7000 + 0x100 * i)
        extra_neighbors = []
        for i in range(2):
            r = mem.add(0x7800 + 0x100 * i, bytearray(0x90)); struct.pack_into('<Q', r, 0x18, 900 + i); extra_neighbors.append(0x7800 + 0x100 * i)
        dispatcher = bytearray(0x728); struct.pack_into('<I', dispatcher, 0x10, 4)
        cas, add = pose_dispatch_serial_atomics(dispatcher); queue = []
        def invoke(callback, owner, caller): run_pose_pair_worker(mem, owner, s)
        def dispatch(d, n, callback, table):
            slots = [struct.unpack_from('<Q', provider, table - P + 8 * i)[0] for i in range(n)]
            dispatch_pose_workers(d, n, callback, slots, atomic_compare_exchange=cas, atomic_add=add,
                                  enqueue=queue.append, take=lambda: queue.pop(0) if queue else None,
                                  invoke=invoke, notify=lambda h: None, wait=lambda: self.fail('wait'))
            # worker 1 and 2 "produced" records of their own (the serial claim lets worker 0 take every pair)
            for owner, recs, off in ((owners[1], extra_links, 8), (owners[2], extra_neighbors, 0x18)):
                arr = mem.add(0x20000 + owner, bytearray(16))
                for j, r in enumerate(recs): struct.pack_into('<Q', arr, 8 * j, r)
                mem.set_q(owner + off, 0x20000 + owner); mem.set_d(owner + off + 8, len(recs))
        ms = Svc(mem, sort_key=lambda link: mem.q(link + 0x18))      # authored sort: order by key
        def retire(out, n):
            retire_pose_body_connectivity(provider, links, n, queue_owners={o: mem.regions[o] for o in owners},
                queue_arrays=mem.regions, detach=lambda t, sel: None, reset=lambda t: None,
                reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=s))
        merge_links = lambda n: merge_pose_new_links(mem, P, n, reserve=ms.reserve, copy=ms.copy, sort=ms.sort,
                                                     attach=ms.attach, insert=ms.insert)
        merge_neighbors = lambda n: merge_pose_neighbor_records(mem, P, n, reserve=ms.reserve, copy=ms.copy,
            attach=ms.attach, insert=ms.insert, finish=ms.finish)
        run_pose_pair_link_jobs(provider, P, 0x4000, npairs, None, current_dispatcher=lambda: dispatcher,
            worker_capacity=lambda d: struct.unpack_from('<I', d, 0x10)[0], retire=retire,
            retire_neighbors=lambda n: None, rebalance=lambda c, n: None, dispatch=dispatch,
            merge_links=merge_links, merge_neighbors=merge_neighbors)
        # worker 0 created 25 links (owner+8); two foreign links were appended; all 27 are merged
        self.assertEqual(mem.d(P + 0x30), npairs + 2)
        inserts = [e for e in ms.log if e[0] == 'insert']
        link_keys = [e[2] for e in inserts if e[1] == P + 8]
        self.assertEqual(link_keys, sorted(link_keys)); self.assertEqual(len(link_keys), npairs + 2)
        self.assertEqual(link_keys[:npairs], [100 + k for k in range(npairs)])
        self.assertEqual(link_keys[npairs:], [500, 501])
        self.assertEqual([e[2] for e in inserts if e[1] == P + 0x38], [900, 901])
        self.assertEqual(ms.log[-1], ('finish', P))
        self.assertEqual(mem.d(P + 0x60), 2)
        self.assertEqual(mem.d(P + 0x17C), npairs + 3)


if __name__ == '__main__':
    unittest.main()
