"""Tests for engine.pose_terrain6_edge_filter (0x19974c0 / 0x1996280 / 0x1995fa0) with authored
kind-6 fixtures (a flat 3x3-vertex grid, y = 0, every triangle wound for a +Y normal).

Native agreement is in native/snow_host/pose_terrain6_leaves_validation.json. The edge-table
convention used here (slot j = edge from vertex j to vertex j+1) is the harness's authored one, not
a recovered game layout.
"""
import math
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_terrain6_edge_filter as ef
from engine import pose_terrain6_tree_query as tq
from engine import pose_narrowphase_capsule_terrain6 as cap

SHAPE, MESH, VERTS, INDS, PAIRS, EDGES, RECS = 0x1000, 0x2000, 0x10000, 0x20000, 0x30000, 0x40000, 0x50000
GUARD = b'\xab' * 0x30


def fb(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def grid(n=3):
    verts = [(float(i), 0.0, float(j)) for j in range(n) for i in range(n)]
    tris = []
    for j in range(n - 1):
        for i in range(n - 1):
            a, b, c, d = j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i
            tris += [(a, d, c), (a, c, b)]
    return verts, tris


def adjacency(tris):
    edges, slots = {}, []
    for t, tri in enumerate(tris):
        for j in range(3):
            key = tuple(sorted((tri[j], tri[(j + 1) % 3])))
            edges.setdefault(key, [len(edges), []])[1].append(t)
            slots.append(edges[key][0])
    pairs = [None] * len(edges)
    for i, ts in edges.values():
        pairs[i] = tuple((ts + [0xFFFF, 0xFFFF])[:2])
    return pairs, slots


def memory(verts, tris, records, pairs=None, slots=None, scale=(1, 1, 1), no_pairs=False):
    if pairs is None:
        pairs, slots = adjacency(tris)
    shape = bytearray(0x100)
    struct.pack_into('<I', shape, 0x40, 2)
    struct.pack_into('<Q', shape, 0x48, MESH)
    struct.pack_into('<3f', shape, 0x70, *scale)
    mesh = bytearray(0x100)
    struct.pack_into('<QQ', mesh, 0x30, VERTS, 0)
    struct.pack_into('<Q', mesh, 0x40, INDS)
    struct.pack_into('<I', mesh, 0x48, len(tris))
    struct.pack_into('<Q', mesh, 0xA8, 0 if no_pairs else PAIRS)
    struct.pack_into('<Q', mesh, 0xB8, EDGES)
    recs = bytearray()
    for (d, p) in records:
        recs += struct.pack('<3fI3fI', *d, len(recs) // 0x30, *p, 0xC0DE) + bytes(0x10)
    recs += GUARD
    return PoseFlatMemory({
        SHAPE: shape, MESH: mesh,
        VERTS: bytearray(struct.pack('<%df' % (3 * len(verts)), *[c for v in verts for c in v]) + bytes(16)),
        INDS: bytearray(struct.pack('<%dH' % (3 * len(tris)), *[i for t in tris for i in t]) + bytes(8)),
        PAIRS: bytearray(b''.join(struct.pack('<HH', *p) for p in pairs) + bytes(8)),
        EDGES: bytearray(struct.pack('<%dI' % len(slots), *slots) + bytes(8)),
        RECS: recs})


def unit(*v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def tags(mem, n):
    return [struct.unpack('<I', bytes(mem.view(RECS + 0x30 * i + 0xC, 4)))[0] for i in range(n)]


UP = (0.0, 1.0, 0.0)
VERTS3, TRIS3 = grid()
# triangle 0 = (0, 3, 4): A = (0,0,0), B = (0,0,1), C = (1,0,1); triangle 7 = (4, 8, 5).


class Filter(unittest.TestCase):
    def run_filter(self, records, tri=0, **kw):
        mem = memory(VERTS3, TRIS3, records, **{k: v for k, v in kw.items() if k != 'frame'})
        trace = []
        args = (kw['frame'],) if 'frame' in kw else ()
        n = ef.neighbourhood_filter(mem, SHAPE, tri, RECS, len(records), *args, trace=trace)
        return n, mem, trace

    def test_count_zero_and_missing_pair_table(self):
        mem = memory(VERTS3, TRIS3, [((0, -1, 0), (0.2, 0, 0.6))])
        self.assertEqual(ef.neighbourhood_filter(mem, SHAPE, 0, RECS, 0), 0)
        n, mem, trace = self.run_filter([((0, -1, 0), (0.2, 0, 0.6))], no_pairs=True)
        self.assertEqual((n, trace), (1, []))                     # untouched, even a back-facing record

    def test_interior_kept_and_back_facing_rejected(self):
        interior = (0.2, 0.0, 0.6)
        n, _, trace = self.run_filter([(UP, interior)])
        self.assertEqual((n, trace), (1, [('interior', False)]))
        n, _, trace = self.run_filter([((0, -1, 0), interior)])
        self.assertEqual((n, trace), (0, [('back', True)]))
        # D.N against -1e-5 (|N| = 1 here): -1e-6 passes the gate, -1e-4 does not
        self.assertEqual(self.run_filter([(unit(1, -1e-6, 0), interior)])[0], 1)
        self.assertEqual(self.run_filter([(unit(1, -1e-4, 0), interior)])[0], 0)

    def test_vertex_fan(self):
        # vertex C = (1,0,1) of triangle 0 is the grid centre (index 4), surrounded by 6 triangles.
        centre = (1.0, 0.0, 1.0)
        n, _, trace = self.run_filter([(UP, centre)])
        self.assertEqual(trace, [('vertex2', False)])             # every neighbour is in plane
        for d in [unit(0.3, 1, 0), unit(-0.3, 1, 0), unit(0, 1, 0.3), unit(0, 1, -0.3)]:
            n, _, trace = self.run_filter([(d, centre)])
            self.assertEqual(trace, [('vertex2', True)], d)
        # corner vertex A = (0,0,0): neighbours lie only toward +x/+z, so a tilt toward -x is kept
        n, _, trace = self.run_filter([(unit(-0.3, 1, -0.3), (0.0, 0.0, 0.0))])
        self.assertEqual(trace, [('vertex0', False)])
        # the walk is one-directional: from triangle 0 it tests B = (0,0,1), then crosses edge A-B,
        # which is a boundary (0xffff), and stops; vertices 1 = (1,0,0) and 4 are never tested.
        n, _, trace = self.run_filter([(unit(0.0, 1, 0.3), (0.0, 0.0, 0.0))])
        self.assertEqual(trace, [('vertex0', True)])
        n, _, trace = self.run_filter([(unit(0.3, 1, 0.0), (0.0, 0.0, 0.0))])
        self.assertEqual(trace, [('vertex0', False)])

    def test_vertex_fan_walks_past_the_first_neighbour(self):
        # at the centre of triangle 7 = (4, 8, 5), vertex 0 is the centre; the first neighbour is 8 = (2,0,2)
        mem_trace = []
        mem = memory(VERTS3, TRIS3, [])
        m = ef.read_mode2_mesh(mem, SHAPE)
        v = [fb(1.0), 0, fb(1.0), 0]
        d = [fb(x) for x in unit(-0.3, 1, -0.3)] + [0]            # points toward vertex 0 = (0,0,0)
        self.assertTrue(ef.vertex_fan_test(mem, m, 7, 0, v, d, 'sse', trace=mem_trace))
        self.assertGreater(len(mem_trace), 1)

    def test_edge_test_reads_slot_j_plus_one(self):
        # one triangle (A, B, C) and a neighbour across A-B lying outward (flat). Record on edge A-B
        # (WC ~ 0) tilted outward: kept when the edge test sees no neighbour, rejected when it does.
        verts = [(0, 0, 0), (0, 0, 1), (1, 0, 1), (-1, 0, 0.5)]
        tris = [(0, 1, 2), (1, 0, 3)]
        on_edge = (0.0, 0.0, 0.5)
        tilt_out = unit(-0.3, 1, 0)
        rec = [(tilt_out, on_edge)]
        pairs = [(0, 1), (0, 0xFFFF)]
        # neighbour id in slot (j+1)%3 = 1 -> used
        mem = memory(verts, tris, rec, pairs=pairs, slots=[1, 0, 1, 0, 1, 1])
        self.assertEqual(ef.neighbourhood_filter(mem, SHAPE, 0, RECS, 1), 0)
        # neighbour only in slot j = 0 -> not seen; N1 = the opposite vertex, so nothing rejects
        mem = memory(verts, tris, rec, pairs=pairs, slots=[0, 1, 1, 0, 1, 1])
        self.assertEqual(ef.neighbourhood_filter(mem, SHAPE, 0, RECS, 1), 1)
        # tilted inward: the triangle's own side rejects whatever the table says
        mem = memory(verts, tris, [(unit(0.3, 1, 0.0), on_edge)], pairs=pairs, slots=[0, 1, 1, 0, 1, 1])
        self.assertEqual(ef.neighbourhood_filter(mem, SHAPE, 0, RECS, 1), 0)

    def test_swap_removal_order_and_tail(self):
        interior = (0.2, 0.0, 0.6)
        n, mem, trace = self.run_filter([((0, -1, 0), interior), (UP, interior), (UP, (0.3, 0, 0.7))])
        self.assertEqual(n, 2)
        self.assertEqual(tags(mem, 3), [2, 1, 2])                 # last copied into slot 0; tail kept
        self.assertEqual(bytes(mem.view(RECS + 0x90, 0x30)), GUARD)
        self.assertEqual([t[0] for t in trace], ['back', 'interior', 'interior'])

    def test_frame_translation_moves_the_point(self):
        interior = (0.2, 0.0, 0.6)
        tilt = unit(0.3, 1, 0)
        self.assertEqual(self.run_filter([(tilt, interior)])[0], 1)
        frame = [list(r) for r in ef.IDENTITY_ROWS] + [[fb(0.8), 0, fb(0.4), 0]]     # -> (1, 0, 1)
        n, _, trace = self.run_filter([(tilt, interior)], frame=frame)
        self.assertEqual((n, trace), (0, [('vertex2', True)]))

    def test_scale_applies_to_vertices(self):
        # x scaled by 2: the centre vertex moves to (2, 0, 1); the unscaled centre is now interior/edge
        n, _, trace = self.run_filter([(UP, (2.0, 0.0, 1.0))], scale=(2, 1, 1))
        self.assertEqual(trace, [('vertex2', False)])

    def test_service_in_the_tester(self):
        """Smoke test: the tester with both modelled services (a capsule lying on the grid, mode 2)."""
        from tests.test_pose_narrowphase_capsule_terrain6 import build, grid as tgrid, LYING, GEOM, OUT, MESH as TMESH
        verts, tris = tgrid(4, 4)
        mem = build(verts, tris, mode=2, cap_t=(1.5, 0.2, 1.5), **LYING)
        # add a one-level-per-leaf tree (all child boxes = root box) and adjacency
        n = len(tris)
        nodes = []

        def make(ids):
            idx = len(nodes)
            nodes.append(None)
            kids = []
            for part in (ids[:len(ids) // 2], ids[len(ids) // 2:]):
                kids.append(('leaf', part[0]) if len(part) == 1 else ('node', make(part)))
            flags = sum(1 << ci for ci, k in enumerate(kids) if k[0] == 'leaf')
            nodes[idx] = bytes(3) + bytes([flags]) + bytes(4) + struct.pack('<HH', *[k[1] for k in kids])
            return idx
        make(list(range(n)))
        tree_nodes = 0x60000
        mem.add(tree_nodes, bytearray(b''.join(nodes) + bytes(16)))
        raw = mem.view(TMESH + 0x80, 0x20)
        raw[0:0x18] = struct.pack('<6f', 3.2, 1, 3.2, -0.1, -0.5, -0.1)
        raw[0x18:0x20] = struct.pack('<Q', tree_nodes)
        pairs, slots = adjacency(tris)
        tpairs, tedges = 0x70000, 0x78000                     # clear of that fixture's regions
        mem.add(tpairs, bytearray(b''.join(struct.pack('<HH', *p) for p in pairs) + bytes(8)))
        mem.add(tedges, bytearray(struct.pack('<%dI' % len(slots), *slots) + bytes(8)))
        mesh = mem.view(TMESH, 0xC0)
        mesh[0xA8:0xB0] = struct.pack('<Q', tpairs)
        mesh[0xB8:0xC0] = struct.pack('<Q', tedges)
        qtr, ftr = [], []
        count = cap.capsule_terrain_tester(mem, GEOM, OUT, 500, query=tq.service(mem, traces=qtr),
                                           edge_filter=ef.service(traces=ftr))
        self.assertGreater(count, 0)
        self.assertEqual(len(qtr), 1)
        self.assertTrue(ftr)
        self.assertEqual(sorted(qtr[0]['ids']), list(range(n)))      # the capsule box covers every node
        for i in range(count):
            feature = struct.unpack('<I', bytes(mem.view(OUT + 0x30 * i + 0x2C, 4)))[0]
            self.assertLess(feature >> 16, n)


if __name__ == '__main__':
    unittest.main()
