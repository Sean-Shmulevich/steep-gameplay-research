import math
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_convex_point_query as mod
from engine.pose_convex_point_query import (
    bind_point_query, convex_point_query, hull_support, DEFAULT_STATICS, NEG_FLT_MAX)
from engine.pose_narrowphase_sphere import sphere_convex_tester

# Authored synthetic layout (not engine addresses).
SHAPE, VERTS, TABLE, LIST, GEOM, SA, PLB, PLANES, OUT = (
    0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x7000, 0x7100, 0x8000)
IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
CUBE = [(sx, sy, sz) for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)]


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def flt(b):
    return struct.unpack('<f', struct.pack('<I', b))[0]


def vec(*xs):
    return [bits(x) for x in xs]


def rows_of(t=(0.0, 0.0, 0.0), rows=IDENT):
    return [vec(*r, 0.0) for r in rows] + [vec(*t, 0.0)]


def hull(points, field=None, padding=(0.0, 0.0, 0.0), lookup=None):
    """Kind-5 shape with the constructor's n+1 count convention and a padding slot."""
    vert = bytearray(12 * (len(points) + 2))
    for i, p in enumerate(list(points) + [padding]):
        struct.pack_into('<3f', vert, 12 * i, *p)
    shape = bytearray(0x110)
    struct.pack_into('<QI', shape, 0x40, VERTS, len(points) + 1 if field is None else field)
    regions = {SHAPE: shape, VERTS: vert}
    if lookup:
        e0, e4, e8, table, items = lookup
        struct.pack_into('<QQ', shape, 0xC0, TABLE, 0)
        struct.pack_into('<Q', shape, 0xD0, LIST)
        struct.pack_into('<IIf', shape, 0xE0, e0, e4, e8)
        regions[TABLE] = bytearray(struct.pack('<%dI' % len(table), *table))
        regions[LIST] = bytearray(struct.pack('<%dI' % max(len(items), 1), *(items or [0])))
    return PoseFlatMemory(regions)


def query(mem, point, rows=None, iterations=16, **kw):
    dist, on_hull, on_point = convex_point_query(mem, rows or rows_of(), SHAPE, vec(*point, 0.0),
                                                 iterations, **kw)
    return flt(dist[0]), [flt(x) for x in on_hull[:3]], [flt(x) for x in on_point[:3]], dist


class SupportTest(unittest.TestCase):
    def test_brute_force_skips_the_padding_slot(self):
        # Padding slot (index n) is the most extreme point but the scan stops at count-2.
        mem = hull(CUBE, padding=(100.0, 100.0, 100.0))
        self.assertEqual(hull_support(mem, SHAPE, vec(1.0, 1.0, 1.0)), 7)

    def test_count_field_without_padding_skips_the_last_real_vertex(self):
        mem = hull(CUBE, field=len(CUBE))
        self.assertNotEqual(hull_support(mem, SHAPE, vec(1.0, 1.0, 1.0)), 7)

    def test_first_strict_maximum_and_nan_direction(self):
        mem = hull([(1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)])
        self.assertEqual(hull_support(mem, SHAPE, vec(1.0, 0.0, 0.0)), 0)
        nan = 0x7FC00000
        self.assertEqual(hull_support(mem, SHAPE, [nan, 0, 0]), 0)    # unordered never wins

    def test_single_vertex_and_zero_field(self):
        self.assertEqual(hull_support(hull([(3.0, 0.0, 0.0)]), SHAPE, vec(-1.0, 0.0, 0.0)), 0)
        with self.assertRaises(ValueError):
            hull_support(hull([(3.0, 0.0, 0.0)], field=0), SHAPE, vec(1.0, 0.0, 0.0))

    def test_start_value_is_minus_flt_max(self):
        self.assertEqual(flt(NEG_FLT_MAX), -3.4028234663852886e+38)
        mem = hull([(0.0, 0.0, 0.0), (-3e38, 0.0, 0.0)])
        # dot -inf/-huge does not beat -FLT_MAX unless strictly greater
        self.assertEqual(hull_support(mem, SHAPE, vec(1.0e10, 0.0, 0.0)), 0)

    def test_lookup_direct_and_list_entries(self):
        # 2x2x2 cells, E4 = 2, E0 = 1, E8 = 1.0: cell = trunc(1 + c/|d|), clamped to 0..1
        table = [0] * 8
        table[7] = 3 << 1                                  # (+,+,+) cell: vertex 3 directly
        table[1] = (0 << 1) | 1                            # (+,-,-) cell: list at item 0
        items = [(4 << 1), (5 << 1), (6 << 1) | 1]         # vertices 4, 5, 6; last item ends
        mem = hull(CUBE, lookup=(1, 2, 1.0, table, items))
        self.assertEqual(hull_support(mem, SHAPE, vec(1.0, 1.0, 1.0)), 3)
        self.assertEqual(hull_support(mem, SHAPE, vec(1.0, -1.0, -1.0)), 4)   # CUBE[4] = (1,-1,-1)

    def test_lookup_nan_direction_clamps_to_cell_zero(self):
        table = [(2 << 1)] + [0] * 7
        mem = hull(CUBE, lookup=(1, 2, 1.0, table, []))
        self.assertEqual(hull_support(mem, SHAPE, [0x7FC00000, 0, 0]), 2)


class QueryTest(unittest.TestCase):
    def test_point_inside_reports_count_four_and_zero_distance(self):
        trace = []
        d, h, p, _ = query(hull(CUBE), (0.2, -0.1, 0.3), trace=trace)
        self.assertEqual(trace[-1], {'exit': 'inside', 'count': 4})
        self.assertEqual(d, 0.0)
        self.assertEqual(h, p)
        for a, b in zip(h, (0.2, -0.1, 0.3)):
            self.assertAlmostEqual(a, b, places=5)

    def test_outside_face_edge_vertex_regions(self):
        mem = hull(CUBE)
        d, h, p, _ = query(mem, (3.0, 0.25, -0.5))
        self.assertAlmostEqual(d, 2.0, places=5)
        self.assertEqual(p, [3.0, 0.25, -0.5])
        for a, b in zip(h, (1.0, 0.25, -0.5)):
            self.assertAlmostEqual(a, b, places=5)
        d, h, _, _ = query(mem, (3.0, 3.0, 0.5))                     # edge region
        self.assertAlmostEqual(d, 8 ** 0.5, places=5)
        d, h, _, _ = query(mem, (2.0, -3.0, 4.0))                    # vertex region: exact vertex
        self.assertEqual(h, [1.0, -1.0, 1.0])
        self.assertAlmostEqual(d, (1 + 4 + 9) ** 0.5, places=5)

    def test_frame_transform_and_translation(self):
        rows = rows_of(t=(10.0, 0.0, 0.0), rows=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        d, h, _, _ = query(hull([(2.0, 0.0, 0.0)]), (0.0, 0.0, 0.0), rows=rows)
        self.assertEqual(h, [10.0, 2.0, 0.0])                       # t + x*b0
        self.assertAlmostEqual(d, 104 ** 0.5, places=4)

    def test_zero_iterations_returns_vertex_zero(self):
        for it in (0, -1):
            trace = []
            d, h, p, _ = query(hull(CUBE), (5.0, 5.0, 5.0), iterations=it, trace=trace)
            self.assertEqual(h, list(CUBE[0]))
            self.assertEqual(p, [5.0, 5.0, 5.0])
            self.assertEqual(trace, [{'exit': 'iterations', 'count': 1}])

    def test_point_on_vertex_zero_stops_on_direction(self):
        trace = []
        d, h, _, _ = query(hull(CUBE), CUBE[0], trace=trace)
        self.assertEqual(trace[-1]['exit'], 'direction')
        self.assertEqual(d, 0.0)

    def test_repeat_and_no_progress_exits(self):
        trace = []
        query(hull([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]), (5.0, 1.0, 0.0), trace=trace)
        self.assertEqual(trace[-1], {'exit': 'repeat', 'count': 1})
        trace = []
        d, h, _, _ = query(hull([(1.0, 0.0, 0.0)]), (5.0, 0.0, 0.0), trace=trace)
        # vertex 0 is not in the visited list at first: it is appended again, the segment
        # collapses to vertex A, |v|^2 does not drop below 0.999999*prev, and the saved
        # simplex is restored.
        self.assertEqual(trace[0]['index'], 0)
        self.assertEqual(trace[-1], {'exit': 'no-progress', 'count': 1})
        self.assertEqual((d, h), (4.0, [1.0, 0.0, 0.0]))

    def test_iteration_cap(self):
        pts = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            pts.append((math.cos(a), math.sin(a), 0.0))
        trace = []
        query(hull(pts), (3.0, 1.0, 0.0), iterations=1, trace=trace)
        self.assertEqual(trace[-1], {'exit': 'iterations', 'count': 2})
        trace = []
        query(hull(pts), (3.0, 1.0, 0.0), iterations=16, trace=trace)
        self.assertEqual(trace[-1], {'exit': 'repeat', 'count': 2})

    def test_degenerate_segment_uses_first_static(self):
        pts = [(0.0, 0.0, 0.0), (1e-4, 0.0, 0.0)]
        p = (5e-5, 1.0, 0.0)
        trace = []
        query(hull(pts), p, trace=trace)
        self.assertEqual(trace[-1]['exit'], 'degenerate')
        zero = ((0,) * 4,) * 3
        trace = []
        query(hull(pts), p, trace=trace, statics=zero)
        self.assertNotEqual(trace[-1]['exit'], 'degenerate')

    def test_nan_point_lane_propagates(self):
        mem = hull(CUBE)
        dist, h, p = convex_point_query(mem, rows_of(), SHAPE, [0x7FC00000, bits(3.0), 0, 0])
        self.assertEqual(dist[0] & 0x7F800000, 0x7F800000)

    def test_statics_default(self):
        self.assertEqual(DEFAULT_STATICS, ((0x33D6BF95,) * 4,) * 3)


class ComposedSphereTest(unittest.TestCase):
    def test_sphere_touching_hull_face_through_bound_query(self):
        mem = hull(CUBE)
        geom = b''.join(struct.pack('<4f', *r, 0.0) for r in list(IDENT) + [(1.5, 0.0, 0.0)])
        geom += b''.join(struct.pack('<4f', *r, 0.0) for r in list(IDENT) + [(0.0, 0.0, 0.0)])
        geom += struct.pack('<QQ', SA, SHAPE) + bytes(8)
        sa = bytearray(0x200); struct.pack_into('<f', sa, 0x40, 0.75)
        struct.pack_into('<Q', mem.regions[SHAPE], 0x100, PLB)
        plb = bytearray(0x40); struct.pack_into('<Q', plb, 8, PLANES); struct.pack_into('<H', plb, 0x22, 0)
        for base, raw in ((GEOM, geom), (SA, sa), (PLB, plb), (PLANES, bytes(0x14)), (OUT, b'\xa5' * 0x30)):
            mem.add(base, bytearray(raw))
        n = sphere_convex_tester(mem, GEOM, OUT, 500, point_query=bind_point_query(mem))
        self.assertEqual(n, 1)
        rec = struct.unpack('<12f', bytes(mem.view(OUT, 0x30)))
        self.assertAlmostEqual(rec[3], -0.25, places=5)              # depth = dist - radius
        self.assertAlmostEqual(rec[0], -1.0, places=5)               # normal from sphere toward hull
        far = bytearray(geom); struct.pack_into('<f', far, 0x30, 9.0)
        mem.view(GEOM, len(far))[:] = far
        self.assertEqual(sphere_convex_tester(mem, GEOM, OUT, 500, point_query=bind_point_query(mem)), 0)


if __name__ == '__main__':
    unittest.main()
