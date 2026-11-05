import struct
import unittest

from engine.pose_island_attach import (attach_changed_links, merge_island_groups,
                                       absorb_island_group, append_group_link,
                                       finalize_group_bytes, publish_pending_links,
                                       bind_island_attach)
from engine.pose_pair_link_worker import PoseFlatMemory

CTX = 0x1000
G = [0x2000, 0x2100, 0x2200]
G410 = 0x2800
G408 = 0x2900
ARR = 0x3000
BODY = 0x10000
META = 0x20000
LINK = 0x30000
SPAN = 0x40000


class World:
    def __init__(self):
        self.mem = PoseFlatMemory()
        self.next_array = ARR
        self.mem.add(CTX, bytearray(0x4a0))
        self.mem.set_q(CTX + 0x408, G408)
        self.mem.set_q(CTX + 0x410, G410)
        for off in (0x418, 0x428, 0x470, 0x490):
            self.mem.set_q(CTX + off, self.array(16))
            self.mem.set_d(CTX + off + 12, 16)
        self.bodies = 0
        self.links = 0
        for g in G + [G410, G408]:
            self.mem.add(g, bytearray(0x100))
            for off in (0x10, 0x40, 0x90):
                self.mem.set_q(g + off, self.array(16))
                self.mem.set_d(g + off + 12, 16)

    def array(self, n):
        p = self.next_array
        self.next_array += n * 8 + 0x40
        self.mem.add(p, bytearray(n * 8))
        return p

    def body(self, group, bit15=True, kind=0):
        b = BODY + self.bodies * 0x200
        m = META + self.bodies * 0x60
        self.bodies += 1
        self.mem.add(b, bytearray(0x200))
        self.mem.add(m, bytearray(0x60))
        self.mem.set_q(b + 0x30, m)
        self.mem.put('<H', m + 0x50, 0x8000 if bit15 else 0)
        self.mem.set_b(m + 0x53, kind)
        n = self.mem.d(group + 0x18)
        self.mem.set_q(self.mem.q(group + 0x10) + 8 * n, b)
        self.mem.set_d(group + 0x18, n + 1)
        self.mem.set_q(b + 0x10, group)
        self.mem.set_d(b + 0x1c, n)
        return b

    def link(self, b1, b2, flags=0):
        l = LINK + self.links * 0x100
        self.links += 1
        self.mem.add(l, bytearray(0x100))
        self.mem.set_q(l + 8, b1)
        self.mem.set_q(l + 0x10, b2)
        self.mem.set_b(l + 0x84, flags)
        return l

    def span(self, links):
        self.mem.add(SPAN, bytearray(max(8, 8 * len(links))))
        for k, l in enumerate(links):
            self.mem.set_q(SPAN + 8 * k, l)


def recorder(log):
    return dict(
        finalize=lambda c, g: log.append(('finalize', g)),
        remove_body=lambda g, b: log.append(('remove_body', g, b)),
        append_body=lambda g, b: log.append(('append_body', g, b)),
        merge=lambda c, a, b: log.append(('merge', a, b)),
        append_link=lambda g, l: log.append(('append_link', g, l)))


class AttachOrderTests(unittest.TestCase):
    def test_entry_clears_pending_and_skips_flagged_links(self):
        w = World()
        w.mem.set_d(CTX + 0x498, 5)
        b1, b2 = w.body(G[0]), w.body(G[1])
        w.span([w.link(b1, b2, flags=2)])
        log = []
        attach_changed_links(w.mem, CTX, SPAN, 1, **recorder(log))
        self.assertEqual(log, [])
        self.assertEqual(w.mem.d(CTX + 0x498), 0)

    def test_merge_or_special_move_then_link_append(self):
        w = World()
        a, b, s = w.body(G[0]), w.body(G[1]), w.body(G410)
        l1, l2, l3 = w.link(a, b), w.link(s, a), w.link(a, s)
        w.span([l1, l2, l3])
        log = []
        attach_changed_links(w.mem, CTX, SPAN, 3, **recorder(log))
        self.assertEqual(log, [
            ('finalize', G[0]), ('finalize', G[1]), ('merge', G[0], G[1]), ('append_link', G[0], l1),
            ('finalize', G410), ('finalize', G[0]), ('remove_body', G410, s), ('append_body', G[0], s),
            ('append_link', G410, l2),
            ('finalize', G[0]), ('finalize', G410), ('remove_body', G410, s), ('append_body', G[0], s),
            ('append_link', G[0], l3)])

    def test_bit15_clear_endpoint_skips_membership_change(self):
        w = World()
        a, b = w.body(G[0]), w.body(G[1], bit15=False)
        l = w.link(a, b)
        w.span([l])
        log = []
        attach_changed_links(w.mem, CTX, SPAN, 1, **recorder(log))
        self.assertEqual([e[0] for e in log], ['finalize', 'finalize', 'append_link'])


class MergeAbsorbTests(unittest.TestCase):
    def test_larger_group_absorbs_and_tie_keeps_first(self):
        w = World()
        w.body(G[0])
        w.body(G[1])
        w.body(G[1])
        log = []
        args = dict(absorb=lambda d, s: log.append(('absorb', d, s)),
                    remove_group=lambda c, g: log.append(('remove', g)),
                    destroy=lambda g, f: log.append(('destroy', g, f)))
        self.assertEqual(merge_island_groups(w.mem, CTX, G[0], G[1], **args), G[1])
        self.assertEqual(log, [('absorb', G[1], G[0]), ('remove', G[0]), ('destroy', G[0], 1)])
        self.assertEqual(w.mem.d(CTX + 0x468), 1)
        w.body(G[0])
        log.clear()
        self.assertEqual(merge_island_groups(w.mem, CTX, G[0], G[1], **args), G[0])

    def test_absorb_renumbers_and_zeroes_source_counts(self):
        w = World()
        d0 = w.body(G[0])
        s0, s1 = w.body(G[1]), w.body(G[1])
        l = w.link(s0, s1)
        append_group_link(w.mem, G[1], l, grow_links=None)
        pose = 0x50000
        w.mem.add(pose, bytearray(0x80))
        w.mem.set_q(w.mem.q(G[1] + 0x90), pose)
        w.mem.set_d(G[1] + 0x98, 1)
        absorb_island_group(w.mem, G[0], G[1], grow_bodies=None, grow_links=None, allocator=None)
        self.assertEqual(w.mem.d(G[0] + 0x18), 3)
        self.assertEqual([w.mem.d(b + 0x1c) for b in (d0, s0, s1)], [0, 1, 2])
        self.assertEqual(w.mem.q(s1 + 0x10), G[0])
        self.assertEqual(w.mem.d(l + 0x80), 0)
        self.assertEqual((w.mem.q(pose + 0x60), w.mem.d(pose + 0x68)), (G[0], 0))
        self.assertEqual([w.mem.d(G[1] + o) for o in (0x18, 0x48, 0x98)], [0, 0, 0])

    def test_absorb_grows_by_doubling_and_pose_from_zero_exactly(self):
        w = World()
        w.mem.set_d(G[0] + 0x1c, 1)
        w.body(G[0])
        w.body(G[1])
        w.body(G[1])
        w.mem.set_q(G[0] + 0x90, 0)
        w.mem.set_d(G[0] + 0x9c, 0)
        w.mem.set_d(G[1] + 0x98, 3)
        for k in range(3):
            w.mem.add(0x51000 + k * 0x100, bytearray(0x80))
            w.mem.set_q(w.mem.q(G[1] + 0x90) + 8 * k, 0x51000 + k * 0x100)
        log = []

        class Alloc:
            def allocate(self, size, align, tag):
                log.append(('alloc', size, align, tag))
                return w.array(size // 8)

        def grow(desc, cap):
            log.append(('grow', desc, cap))
            new = w.array(cap)
            old, n = w.mem.q(desc), w.mem.d(desc + 8)
            w.mem.view(new, n * 8)[:] = w.mem.view(old, n * 8).tobytes()
            w.mem.set_q(desc, new)
            w.mem.set_d(desc + 12, cap)
        absorb_island_group(w.mem, G[0], G[1], grow_bodies=grow, grow_links=grow, allocator=Alloc())
        self.assertEqual(log, [('grow', G[0] + 0x10, 4), ('alloc', 24, 0x10, 0x37)])
        self.assertEqual(w.mem.d(G[0] + 0x9c), 3)

    def test_link_append_index_is_count_before_growth(self):
        w = World()
        w.mem.set_d(G[0] + 0x48, 16)
        l = w.link(0, 0)
        grown = []

        def grow(desc, cap):
            grown.append(cap)
            new = w.array(cap)
            w.mem.set_q(desc, new)
            w.mem.set_d(desc + 12, cap)
        append_group_link(w.mem, G[0], l, grow_links=grow)
        self.assertEqual(grown, [32])
        self.assertEqual(w.mem.d(l + 0x80), 16)
        self.assertEqual(w.mem.d(G[0] + 0x48), 17)


class FinalizeAndPublishTests(unittest.TestCase):
    def test_finalize_queues_kind2_first_endpoint_links_then_publish(self):
        w = World()
        b = w.body(G[0], kind=0x12)
        other = w.body(G[1])
        w.mem.set_b(G[0] + 0xa0, 1)
        w.mem.set_q(w.mem.q(CTX + 0x428), G[0])
        w.mem.set_d(CTX + 0x428 + 8, 1)
        l = w.link(b, other)
        append_group_link(w.mem, G[0], l, grow_links=None)
        self.assertTrue(finalize_group_bytes(w.mem, CTX, G[0]))
        self.assertEqual(w.mem.d(CTX + 0x498), 1)
        self.assertEqual(w.mem.b(w.mem.q(b + 0x30) + 0x53), 0x10)  # quiet reset after queueing
        self.assertEqual(w.mem.b(G[0] + 0xa0), 0)
        self.assertEqual(w.mem.d(CTX + 0x420), 1)                 # moved to the 418 list
        owner = 0x60000
        w.mem.add(owner, bytearray(0x40))
        w.mem.set_q(owner + 0x28, 0x777)
        w.mem.set_q(owner + 0x30, CTX)
        out = []
        publish_pending_links(w.mem, owner, lambda i, v: out.append((i, v)))
        self.assertEqual(out, [(0x777, l + 8)])
        w.mem.set_q(w.mem.q(CTX + 0x490), 0)
        out.clear()
        publish_pending_links(w.mem, owner, lambda i, v: out.append((i, v)))
        self.assertEqual(out, [(0x777, 0)])

    def test_bound_attach_merges_through_reconstructed_services(self):
        w = World()
        for g in G[:2]:
            n = w.mem.d(CTX + 0x420)
            w.mem.set_q(w.mem.q(CTX + 0x418) + 8 * n, g)
            w.mem.set_d(CTX + 0x420, n + 1)
            w.mem.set_d(g + 0xc, n)
        a, b = w.body(G[0]), w.body(G[1])
        l = w.link(a, b)
        w.span([l])
        destroyed = []
        attach = bind_island_attach(w.mem, remove_body=None, grow_bodies=None, grow_links=None,
                                    grow_arrays=None, allocator=None,
                                    destroy_group=lambda g, f: destroyed.append(g))
        attach(CTX, SPAN, 1)
        self.assertEqual(destroyed, [G[1]])
        self.assertEqual(w.mem.d(CTX + 0x420), 1)
        self.assertEqual(w.mem.q(b + 0x10), G[0])
        self.assertEqual(w.mem.d(G[0] + 0x48), 1)


class BroadphaseReceiverTests(unittest.TestCase):
    def test_pair_record_append_grows_from_zero_and_copies_link_plus8(self):
        from engine.pose_island_attach import append_broadphase_pair, mark_broadphase_active
        mem = PoseFlatMemory()
        bp, vec, link = 0x1000, 0x2000, 0x3000
        mem.add(bp, bytearray(0x100))
        mem.add(vec, bytearray(0x10))
        mem.add(link, bytearray(range(0x40)))
        mem.set_q(bp + 0xf8, vec)
        grown = []

        def grow(desc, cap):
            grown.append(cap)
            mem.add(0x5000, bytearray(cap * 24))
            mem.set_q(desc, 0x5000)
            mem.set_d(desc + 12, cap)
        append_broadphase_pair(mem, bp, link + 8, grow=grow)
        self.assertEqual(grown, [8])
        self.assertEqual(mem.view(0x5000, 24).tobytes(), bytes(range(8, 32)))
        self.assertEqual(mem.d(vec + 8), 1)
        mark_broadphase_active(mem, bp, 0)
        self.assertEqual(mem.b(bp + 0x49), 1)
        mark_broadphase_active(mem, bp, 0x100)  # low byte only
        self.assertEqual(mem.b(bp + 0x49), 1)
        mark_broadphase_active(mem, bp, 1)
        self.assertEqual(mem.b(bp + 0x49), 3)


if __name__ == '__main__':
    unittest.main()
