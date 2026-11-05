"""Tests for engine.pose_pair_update_step (0x18b8fa0), unit and composition.

The composition test drives the recovered stages over the full-chain synthetic
scenario: broadphase getters (pose_broadphase_pair_lists) -> select
(pose_provider_link_selection) -> rebuild (pose_body_connectivity_rebuild) ->
jobs (pose_pair_link_jobs, whose retire is pose_body_connectivity_retire).
All data is authored, not live evidence.
"""
import struct
import unittest

from engine import pose_broadphase_pair_lists as bp
from engine.pose_body_connectivity_rebuild import rebuild_pose_body_connectivity
from engine.pose_body_connectivity_retire import (reserve_pose_pointer_vector,
                                                  retire_pose_body_connectivity)
from engine.pose_endpoint_rings import detach_pose_endpoint_rings
from engine.pose_group_link_remove import remove_pose_group_link
from engine.pose_link_state_reset import reset_pose_link_state
from engine.pose_pair_link_jobs import run_pose_pair_link_jobs
from engine.pose_pair_update_step import (INLINE, PosePairOutputVector,
                                          pose_dynamic_tree_broadphase_vcall,
                                          run_pose_pair_update_step)
from engine.pose_provider_link_selection import select_pose_provider_links
from tests.test_pose_connectivity_full_chain import Chain, check_rb, key_of, q, u32

B, P, CTX = 0x100, 0x200, 0x5000


def controller(broadphase=B, provider=P, context=CTX, frame=7):
    c = bytearray(0x78)
    struct.pack_into('<QQQ', c, 0x28, broadphase, context, provider)
    struct.pack_into('<II', c, 0x48, 0, frame)
    return c


class Recorder:
    def __init__(self, values):
        self.values, self.log = dict(values), []

    def vcall(self, token, slot):
        self.log.append(('vcall', token, slot))
        return self.values.get(slot)


class UnitTests(unittest.TestCase):
    def objects(self):
        return {B: bytearray(0x130), P: bytearray(0x190), 0x300: bytearray(0x130), 0x400: bytearray(0x190)}

    def test_order_counts_truncated_shared_output_and_tail_writes(self):
        c, objs = controller(), self.objects()
        r = Recorder({0x60: (0xDEAD << 32) | 3, 0x68: 0xA000, 0x40: 5, 0x48: 0xB000})
        seen = []

        def select(provider, pairs, count, out):
            self.assertEqual(u32(c, 0x48), 1)
            self.assertEqual((len(out.items), out.capacity, out.storage), (0, 0x200, INLINE))
            r.log.append(('select', provider, pairs, count)); out.items[:] = [11, 12]; seen.append(out)

        def rebuild(context, out):
            r.log.append(('rebuild', context, list(out.items))); self.assertIs(out, seen[0])

        def jobs(provider, pairs, count, out):
            r.log.append(('jobs', provider, pairs, count, list(out.items))); self.assertIs(out, seen[0])

        self.assertIs(run_pose_pair_update_step(c, objects=objs, vcall=r.vcall, select=select,
                      rebuild=rebuild, jobs=jobs, release=lambda s: r.log.append(('release', s))), True)
        self.assertEqual(r.log, [('vcall', B, 0x90), ('vcall', B, 0x60), ('vcall', B, 0x68),
                                 ('select', P, 0xA000, 3), ('rebuild', CTX, [11, 12]),
                                 ('vcall', B, 0x40), ('vcall', B, 0x48),
                                 ('jobs', P, 0xB000, 5, [11, 12]), ('vcall', B, 0x88)])
        self.assertEqual(struct.unpack_from('<II', c, 0x48), (2, 8))
        self.assertEqual(u32(objs[B], 8), 8)
        self.assertEqual(u32(objs[P], 0x180), 8)

    def test_fields_reloaded_after_service_mutation(self):
        c, objs = controller(), self.objects()
        r = Recorder({0x60: 0, 0x68: 0, 0x40: 0, 0x48: 0})

        def select(provider, pairs, count, out):
            struct.pack_into('<QQQ', c, 0x28, 0x300, 0x6666, 0x400)

        def rebuild(context, out):
            self.assertEqual(context, 0x6666)
            struct.pack_into('<I', c, 0x4c, 0xFFFFFFFF)

        def jobs(provider, pairs, count, out):
            self.assertEqual(provider, 0x400)

        run_pose_pair_update_step(c, objects=objs, vcall=r.vcall, select=select, rebuild=rebuild,
                                  jobs=jobs, release=None)
        self.assertEqual([e[1] for e in r.log], [B, B, B, 0x300, 0x300, 0x300])
        self.assertEqual(u32(c, 0x4c), 0)       # 32-bit wrap
        self.assertEqual(u32(objs[0x300], 8), 0); self.assertEqual(u32(objs[0x400], 0x180), 0)
        self.assertEqual(u32(objs[B], 8), 0); self.assertEqual(u32(objs[P], 0x180), 0)

    def test_release_only_for_external_storage_with_capacity(self):
        for storage, capacity, expected in ((INLINE, 0x200, []), (0x9000, 0x400, [0x9000]),
                                            (0x9000, 0, [])):
            c, objs, released = controller(), self.objects(), []

            def select(provider, pairs, count, out):
                out.storage, out.capacity = storage, capacity

            run_pose_pair_update_step(c, objects=objs, vcall=Recorder({0x60: 0, 0x68: 0, 0x40: 0, 0x48: 0}).vcall,
                                      select=select, rebuild=lambda *a: None, jobs=lambda *a: None,
                                      release=released.append)
            self.assertEqual(released, expected)

    def test_observed_class_accessor_adapter(self):
        objs = {B: bytearray(0x130), 0x500: bytearray(16)}
        struct.pack_into('<Q', objs[B], 0xf8, 0x500); struct.pack_into('<QI', objs[B], 0x118, 0xA000, 4)
        struct.pack_into('<QI', objs[0x500], 0, 0xB000, 9)
        updates, finishes = [], []
        v = pose_dynamic_tree_broadphase_vcall(objs, update=updates.append, finish=finishes.append)
        self.assertEqual([v(B, s) for s in (0x40, 0x48, 0x60, 0x68)], [9, 0xB000, 4, 0xA000])
        # agrees with the broadphase lane's getters
        read = lambda a, n: bytes(objs[0x500][a - 0x500:a - 0x500 + n])
        self.assertEqual((bp.added_pair_count(objs[B], read), bp.added_pair_array(objs[B], read),
                          bp.removed_pair_count(objs[B]), bp.removed_pair_array(objs[B])), (9, 0xB000, 4, 0xA000))
        v(B, 0x90); v(B, 0x88)
        self.assertEqual((updates, finishes), ([B], [B]))


class CompositionTests(unittest.TestCase):
    """Removed pairs carry the ring links' 24-byte rows; same end state as the
    body-event refresh chain with divisor 1 (one pair worker)."""

    def test_step_composes_select_rebuild_and_jobs_retire(self):
        c = Chain()
        c.provider.extend(bytes(0x100))            # room for +0x170..+0x180
        before = check_rb(self, c.provider, c.tree_nodes)
        ring = c.ring(1)                           # [10, 60, 40, 30, 20]
        removed = b''.join(bytes(c.links[t][8:0x20]) for t in ring)
        added = struct.pack('<QQQ', 0x1100, 0x1400, 0xABC)
        flat = {0xE000: bytearray(removed), 0xE800: bytearray(added), 0xF000: bytearray(16)}
        bph = bytearray(0x130)
        struct.pack_into('<Q', bph, 0xf8, 0xF000); struct.pack_into('<QI', bph, 0x118, 0xE000, len(ring))
        struct.pack_into('<QI', flat[0xF000], 0, 0xE800, 1)

        def read(a, n):
            for base, raw in flat.items():
                if base <= a < base + len(raw):
                    return bytes(raw[a - base:a - base + n])
            raise KeyError(hex(a))

        slots = {0x40: lambda: bp.added_pair_count(bph, read), 0x48: lambda: bp.added_pair_array(bph, read),
                 0x60: lambda: bp.removed_pair_count(bph), 0x68: lambda: bp.removed_pair_array(bph)}
        calls = []

        def vcall(token, slot):
            calls.append(slot)
            return slots[slot]() if slot in slots else None

        provider_map = {0x6000: c.provider}

        def select(provider, pairs, count, out):
            rows = [struct.pack('<QQQ', *r) for r in bp.decode_pair_rows(read, pairs, count)]
            out.items[:] = select_pose_provider_links(provider_map[provider], rows, bodies=c.bodies,
                                                      metadata=c.metadata, node_arrays=c.node_arrays)

        def rebuild(context, out):
            rebuild_pose_body_connectivity(context, out.items, contexts={CTX: c.context}, objects=c.links,
                bodies=c.bodies, groups=c.groups,
                link=lambda g, t: remove_pose_group_link(c.groups[g], c.links[t], objects=c.links,
                                                         slot_arrays=c.slot_arrays),
                process=lambda ctx, g: c.processed.append((ctx, g)))

        jobs_log = []

        def jobs(provider, pairs, count, out):
            prov = provider_map[provider]
            run_pose_pair_link_jobs(prov, provider, pairs, count, out.items,
                current_dispatcher=lambda: 0xD000, worker_capacity=lambda d: 4,
                retire=lambda o, n: retire_pose_body_connectivity(prov, o, n,
                    queue_owners=c.queue_owners, queue_arrays=c.queue_arrays,
                    detach=lambda t, s: detach_pose_endpoint_rings(t, s, records=c.links, bodies=c.bodies),
                    reset=lambda t: reset_pose_link_state(c.links[t], entry_arrays=c.entries,
                        release_contact=c.released.append, release_held=c.released.append),
                    reserve=lambda d, cap: reserve_pose_pointer_vector(d, cap, allocator=c.alloc)),
                retire_neighbors=lambda n: jobs_log.append(('retire_neighbors', n)),
                rebalance=lambda ctx, n: jobs_log.append(('rebalance', n)),
                dispatch=lambda d, n, cb, table: jobs_log.append(('dispatch', n, decode(prov))),
                merge_links=lambda n: jobs_log.append(('merge_links', n)),
                merge_neighbors=lambda n: jobs_log.append(('merge_neighbors', n)))

        def decode(prov):
            ptr, count = struct.unpack_from('<QI', prov, 0x170)
            return bp.decode_pair_rows(read, ptr, count)

        ctl = controller(broadphase=0x100, provider=0x6000, context=CTX, frame=41)
        run_pose_pair_update_step(ctl, objects={0x100: bph, 0x6000: c.provider}, vcall=vcall,
                                  select=select, rebuild=rebuild, jobs=jobs, release=None)
        self.assertEqual(calls, [0x90, 0x60, 0x68, 0x40, 0x48, 0x88])
        # one worker (1 // 10 + 1); dispatcher saw the added row published at +0x170
        self.assertEqual(jobs_log, [('retire_neighbors', 1), ('rebalance', 1),
                                    ('dispatch', 1, [(0x1100, 0x1400, 0xABC)]),
                                    ('merge_links', 1), ('merge_neighbors', 1)])
        keys = check_rb(self, c.provider, c.tree_nodes)
        self.assertEqual(len(before) - len(keys), 3)
        for t in (20, 40, 50, 777):
            self.assertIn(key_of(t), keys)
        self.assertEqual(c.processed, [(CTX, 0xA000), (CTX, 0xB000)])
        owner = c.queue_owners[0x8000]
        ptr, used, cap = struct.unpack_from('<QII', owner, 0x28)
        self.assertEqual((used, cap), (3, 8))
        self.assertEqual(struct.unpack_from('<3Q', c.queue_arrays[ptr]), (10, 60, 30))
        self.assertEqual(sorted(c.ring(1)), [20, 40])
        self.assertEqual(struct.unpack_from('<II', ctl, 0x48), (2, 42))
        self.assertEqual(u32(bph, 8), 42); self.assertEqual(u32(c.provider, 0x180), 42)


if __name__ == '__main__':
    unittest.main()
