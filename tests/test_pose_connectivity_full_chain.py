"""End-to-end synthetic composition of the body connectivity refresh chain.

Composes only recovered modules over ONE shared memory model (token -> bytearray):
refresh -> select_pose_provider_links (collect) -> rebuild_pose_body_connectivity
(link = remove_pose_group_link, process = recording stub) ->
retire_pose_body_connectivity (detach = detach_pose_endpoint_rings, reset =
reset_pose_link_state, reserve = reserve_pose_pointer_vector with a fake allocator).
Everything here is authored synthetic data, not live evidence.
"""
import struct
import unittest

from engine.pose_body_connectivity_rebuild import rebuild_pose_body_connectivity
from engine.pose_body_connectivity_refresh import refresh_pose_body_connectivity
from engine.pose_body_connectivity_retire import (reserve_pose_pointer_vector,
                                                  retire_pose_body_connectivity)
from engine.pose_endpoint_rings import attach_pose_endpoint_rings, detach_pose_endpoint_rings
from engine.pose_group_link_remove import DETACHED, remove_pose_group_link
from engine.pose_link_state_reset import reset_pose_link_state
from engine.pose_provider_link_selection import select_pose_provider_links

U64 = struct.Struct('<Q')


def q(raw, off):
    return U64.unpack_from(raw, off)[0]


def u32(raw, off):
    return struct.unpack_from('<I', raw, off)[0]


class Allocator:
    """Authored deterministic allocator stand-in (vtable +8/+0x10/+0x18)."""
    def __init__(self, arrays):
        self.arrays, self.next, self.log = arrays, 0x9000, []

    def allocate(self, size, align, tag):
        p = self.next; self.next += 0x1000
        self.arrays[p] = bytearray(size); self.log.append(('allocate', size)); return p

    def reallocate(self, old, size, align, tag):
        p = self.next; self.next += 0x1000
        src = self.arrays[old][:size]
        self.arrays[p] = bytearray(src) + bytearray(size - len(src))
        self.log.append(('reallocate', old, size)); return p

    def release(self, p):
        self.log.append(('release', p))


# ---- authored red-black tree builder (NOT a recovered insertion routine) -------
def build_rb_nodes(pairs):
    """pairs: [(key, value)] in slot order. Median-split balanced BST; nodes on the
    deepest level are red, all other levels black (valid RB for median split)."""
    n = len(pairs)
    nodes = bytearray(32 * n)
    order = sorted(range(n), key=lambda i: pairs[i][0])
    depth_max = 0

    def build(lo, hi, parent, depth):
        nonlocal depth_max
        if lo >= hi:
            return -1
        mid = (lo + hi) // 2
        slot = order[mid]
        depth_max = max(depth_max, depth)
        left = build(lo, mid, slot, depth + 1)
        right = build(mid + 1, hi, slot, depth + 1)
        struct.pack_into('<iii', nodes, slot * 32, left, right, parent)
        struct.pack_into('<QQ', nodes, slot * 32 + 16, pairs[slot][1], pairs[slot][0])
        depths[slot] = depth
        return slot

    depths = {}
    root = build(0, n, -1, 0)
    # a level is "incomplete" only at depth_max; make it red unless the level is full
    full_last = (n + 1) & n == 0
    for slot, d in depths.items():
        nodes[slot * 32 + 12] = 1 if (d == depth_max and not full_last and d > 0) else 0
    return nodes, root


def check_rb(test, provider, nodes):
    """Assert the tree at provider+8 is a valid red-black tree; return in-order keys."""
    active, free, _, root, _head = struct.unpack_from('<IIIii', provider, 0x10)
    keys = []

    def walk(i, parent, lo, hi):
        if i == -1:
            return 1
        left, right, par = struct.unpack_from('<iii', nodes, i * 32)
        red = nodes[i * 32 + 12]
        key = q(nodes, i * 32 + 24)
        test.assertEqual(par, parent)
        test.assertEqual(nodes[i * 32 + 13], 0, 'live node marked free')
        test.assertTrue(lo <= key <= hi)
        for c in (left, right):
            if red and c != -1:
                test.assertEqual(nodes[c * 32 + 12], 0, 'red-red violation')
        lb = walk(left, i, lo, key)
        keys.append(key)
        rb = walk(right, i, key, hi)
        test.assertEqual(lb, rb, 'black height mismatch')
        return lb + (0 if red else 1)

    if root != -1:
        test.assertEqual(nodes[root * 32 + 12], 0, 'red root')
    walk(root, -1, 0, 2 ** 64 - 1)
    test.assertEqual(len(keys), active)
    return keys


def key_of(t):
    return 0x8000000000000000 + t * 0x111   # high-bit keys exercise unsigned compare


class Chain:
    """Shared memory model for one scenario."""
    BODY_TOKEN = {1: 0x1100, 2: 0x1200, 3: 0x1300, 4: 0x1400}
    # token -> (endpoint1 body, endpoint2 body)
    LINKS = {10: (1, 2), 20: (3, 1), 30: (1, 3), 40: (2, 1), 60: (4, 1), 50: (2, 3)}
    # metadata (priority bit15, state nibble) per body; body 2 priority clear, body 3 state 2
    META = {1: (0x8000, 0x00), 2: (0x7FFF, 0x00), 3: (0x8000, 0x32), 4: (0x8000, 0x01)}

    def __init__(self, meta=None, ring_links=(10, 20, 30, 40, 60, 50)):
        meta = meta or self.META
        T = self.BODY_TOKEN
        self.bodies = {T[b]: bytearray(0xA0) for b in T}
        self.metadata, self.groups, self.slot_arrays = {}, {}, {}
        for b, (prio, state) in meta.items():
            m = bytearray(0x60)
            struct.pack_into('<H', m, 0x50, prio); m[0x53] = state
            self.metadata[0x2000 + b] = m
            struct.pack_into('<Q', self.bodies[T[b]], 0x30, 0x2000 + b)
        # chain body1 -> metadata -> owner -> controller
        self.owners, self.controllers = {0x3000: bytearray(0x40)}, {0x4000: bytearray(0x80)}
        struct.pack_into('<Q', self.metadata[0x2001], 0x20, 0x3000)
        struct.pack_into('<Q', self.owners[0x3000], 0x20, 0x4000)
        struct.pack_into('<QQ', self.controllers[0x4000], 0x30, 0x5000, 0x6000)  # ctx, provider
        self.context = bytearray(0x470)
        struct.pack_into('<Q', self.context, 0x464, 0xFFFFFFFF_00000009)  # stale counters
        # links
        self.links = {}
        self.entries = {}
        for t, (a, b) in self.LINKS.items():
            r = bytearray(0x100)
            struct.pack_into('<QQQ', r, 8, T[a], T[b], key_of(t))
            struct.pack_into('<QI', r, 0x58, 500 + t, 1)
            struct.pack_into('<Q', r, 0x78, t + 1)
            self.links[t] = r
            self.entries[500 + t] = bytearray(struct.pack('<QQ', 0, t + 2))
        self.links[90] = bytearray(0x100)    # unrelated group member, not in any ring/tree
        # rings (selector 1 heads at body+0x80), attach in listed order
        self.ring_tokens = {}
        for t in ring_links:
            attach_pose_endpoint_rings(t, 1, records=self.links_by_token(), bodies=self.bodies_by_link())
        # groups: body1 -> GA, body4 -> GB, bodies 2/3 -> GC
        self.group_tokens = {1: 0xA000, 4: 0xB000, 2: 0xC000, 3: 0xC000}
        for b, g in self.group_tokens.items():
            struct.pack_into('<Q', self.bodies[T[b]], 0x10, g)
        for g, members, arr in ((0xA000, [30, 10, 90], 0xA100), (0xB000, [60], 0xB100),
                                (0xC000, [20, 40, 50], 0xC100)):
            grp = bytearray(0x100)
            struct.pack_into('<QI', grp, 0x40, arr, len(members))
            self.groups[g] = grp
            self.slot_arrays[arr] = bytearray(struct.pack('<%dQ' % len(members), *members))
            for i, m in enumerate(members):
                struct.pack_into('<I', self.links[m], 0x80, i)
        # provider: tree at +8, owner slot table at +0x70
        pairs = [(key_of(t), t) for t in (10, 20, 30, 40, 60, 50)] + [(key_of(777), 777)]
        self.tree_nodes, root = build_rb_nodes(pairs)
        self.provider = bytearray(0x100)
        struct.pack_into('<QIIIii', self.provider, 8, 0x7000, len(pairs), 0, 0, root, -1)
        self.node_arrays = {0x7000: self.tree_nodes}
        struct.pack_into('<Q', self.provider, 0x70, 0x8000)
        self.queue_owners = {0x8000: bytearray(0x40)}
        self.queue_arrays = {}
        self.alloc = Allocator(self.queue_arrays)
        self.released = []
        self.processed, self.calls = [], []

    # token views: rings use link tokens and body tokens
    def links_by_token(self):
        return self.links

    def bodies_by_link(self):
        return self.bodies

    def run(self):
        T = self.BODY_TOKEN
        provider_map = {0x6000: self.provider}

        def collect(token, rows):
            self.calls.append('collect')
            self.assertion_token = token
            return select_pose_provider_links(provider_map[token], rows, bodies=self.bodies,
                metadata=self.metadata, node_arrays=self.node_arrays)

        def link(group_token, token):
            remove_pose_group_link(self.groups[group_token], self.links[token],
                objects=self.links, slot_arrays=self.slot_arrays)

        def process(context, group_token):
            self.processed.append((context, group_token, self.groups[group_token][0xA1],
                                   u32(self.groups[group_token], 0x48)))

        def rebuild(context, output):
            self.calls.append('rebuild')
            rebuild_pose_body_connectivity(context, output, contexts={0x5000: self.context},
                objects=self.links, bodies=self.bodies, groups=self.groups,
                link=link, process=process)

        def retire(provider_token, output, divisor):
            self.calls.append('retire')
            retire_pose_body_connectivity(provider_map[provider_token], output, divisor,
                queue_owners=self.queue_owners, queue_arrays=self.queue_arrays,
                detach=lambda t, s: detach_pose_endpoint_rings(t, s, records=self.links,
                                                               bodies=self.bodies),
                reset=lambda t: reset_pose_link_state(self.links[t], entry_arrays=self.entries,
                    release_contact=self.released.append, release_held=self.released.append),
                reserve=lambda d, c: reserve_pose_pointer_vector(d, c, allocator=self.alloc))

        refresh_pose_body_connectivity(self.bodies[T[1]], body_token=T[1],
            metadata=self.metadata, owners=self.owners, controllers=self.controllers,
            links=self.links, collect=collect, rebuild=rebuild, retire=retire)

    def ring(self, body):
        """Members of body's selector-1 ring from its head; asserts prev/next symmetry."""
        T = self.BODY_TOKEN[body]
        head = q(self.bodies[T], 0x80)
        if not head:
            return []
        out, cur = [], head
        while True:
            r = self.links[cur]
            port = 0x20 if q(r, 8) == T else 0x30
            nxt = q(r, port)
            nr = self.links[nxt]
            nport = 0x20 if q(nr, 8) == T else 0x30
            assert q(nr, nport + 8) == cur, 'prev/next asymmetric'
            out.append(cur)
            cur = nxt
            if cur == head:
                return out


class FullChainTests(unittest.TestCase):
    def test_full_chain_selected_links_all_stages(self):
        c = Chain()
        self.assertEqual(c.ring(1), [10, 60, 40, 30, 20])   # attach-after-head order
        before_tree_keys = check_rb(self, c.provider, c.tree_nodes)
        self.assertEqual(len(before_tree_keys), 7)
        c.run()
        self.assertEqual(c.calls, ['collect', 'rebuild', 'retire'])
        selected = [10, 60, 30]    # ring order, 40 (body2 prio clear) / 20 (body3 state 2) skipped

        # tree: still valid RB, selected keys gone, others (incl. ineligible, stray) remain
        keys = check_rb(self, c.provider, c.tree_nodes)
        self.assertEqual(sorted(keys), sorted(before_tree_keys[i] for i in range(7)
                         if before_tree_keys[i] not in {key_of(t) for t in selected}))
        self.assertEqual(len(keys), 4)
        for t in (20, 40, 50, 777):
            self.assertIn(key_of(t), keys)

        # group arrays: GA [30,10,90] -> remove 10 then 30, index repair onto 90
        ga = c.groups[0xA000]
        self.assertEqual(u32(ga, 0x48), 1)
        self.assertEqual(q(c.slot_arrays[0xA100], 0), 90)
        self.assertEqual(u32(c.links[90], 0x80), 0)
        self.assertEqual(u32(c.groups[0xB000], 0x48), 0)
        for t in selected:
            self.assertEqual(u32(c.links[t], 0x80), DETACHED)
        gc = c.groups[0xC000]
        self.assertEqual(u32(gc, 0x48), 3)
        self.assertEqual(struct.unpack('<3Q', c.slot_arrays[0xC100]), (20, 40, 50))
        self.assertEqual([u32(c.links[t], 0x80) for t in (20, 40, 50)], [0, 1, 2])

        # process stub: once per queued group, in first-eligible-link order, a1 cleared
        self.assertEqual(c.processed, [(0x5000, 0xA000, 0, 1), (0x5000, 0xB000, 0, 0)])
        self.assertEqual(struct.unpack_from('<II', c.context, 0x464), (2, 0))

        # rings: selected detached, ports cleared, endpoints zeroed, key kept
        for t in selected:
            r = c.links[t]
            self.assertEqual(r[0x20:0x40], bytes(32))
            self.assertEqual(r[8:0x18], bytes(16))
            self.assertEqual(q(r, 0x18), key_of(t))
            self.assertEqual(q(r, 0x78), 0)
        self.assertEqual(c.ring(1), [40, 20] if c.ring(1)[0] == 40 else [20, 40])
        self.assertEqual(sorted(c.ring(1)), [20, 40])
        self.assertEqual(sorted(c.ring(2)), [40, 50])
        self.assertEqual(sorted(c.ring(3)), [20, 50])
        self.assertEqual(c.ring(4), [])
        self.assertEqual(q(c.bodies[Chain.BODY_TOKEN[4]], 0x80), 0)

        # ineligible/untouched links keep endpoints, ports and held payload
        for t, (a, b) in ((20, (3, 1)), (40, (2, 1)), (50, (2, 3))):
            self.assertEqual(struct.unpack_from('<QQ', c.links[t], 8),
                             (Chain.BODY_TOKEN[a], Chain.BODY_TOKEN[b]))
            self.assertEqual(q(c.links[t], 0x78), t + 1)

        # queue: all to owner slot0 (divisor 1), in selection order, via fake allocator
        owner = c.queue_owners[0x8000]
        ptr, used, cap = struct.unpack_from('<QII', owner, 0x28)
        self.assertEqual((used, cap), (3, 8))
        self.assertEqual(struct.unpack_from('<3Q', c.queue_arrays[ptr]), (10, 60, 30))
        self.assertEqual(c.alloc.log, [('allocate', 64)])
        self.assertEqual(c.released, [12, 11, 62, 61, 32, 31])

    def test_empty_ring_calls_no_services(self):
        c = Chain(ring_links=())
        tree = bytes(c.tree_nodes); prov = bytes(c.provider)
        c.run()
        self.assertEqual(c.calls, [])
        self.assertEqual(c.processed, [])
        self.assertEqual(bytes(c.tree_nodes), tree); self.assertEqual(bytes(c.provider), prov)
        self.assertEqual(q(c.context, 0x464), 0xFFFFFFFF_00000009)   # rebuild never ran
        self.assertEqual(c.queue_arrays, {})

    def test_all_ineligible_runs_stages_with_empty_selection(self):
        bad = {b: (0x0001, 0x00) for b in (1, 2, 3, 4)}     # priority bit15 clear everywhere
        c = Chain(meta=bad)
        tree = bytes(c.tree_nodes); prov = bytes(c.provider)
        groups = {g: bytes(v) for g, v in c.groups.items()}
        rings = {b: c.ring(b) for b in (1, 2, 3, 4)}
        c.run()
        self.assertEqual(c.calls, ['collect', 'rebuild', 'retire'])   # stages still called
        self.assertEqual(bytes(c.tree_nodes), tree); self.assertEqual(bytes(c.provider), prov)
        self.assertEqual({g: bytes(v) for g, v in c.groups.items()}, groups)
        self.assertEqual({b: c.ring(b) for b in (1, 2, 3, 4)}, rings)
        self.assertEqual(c.processed, [])
        self.assertEqual(struct.unpack_from('<II', c.context, 0x464), (0, 0))  # rebuild zeroed it
        self.assertEqual(struct.unpack_from('<QII', c.queue_owners[0x8000], 0x28), (0, 0, 0))
        self.assertEqual(c.released, [])


if __name__ == '__main__':
    unittest.main()
