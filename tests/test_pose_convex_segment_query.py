import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_convex_point_query as pq
from engine import pose_convex_segment_query as mod
from engine.pose_convex_segment_query import (
    bind_segment_query, box_segment_query, box_support, convex_segment_query, segment_query_at,
    segment_support)

# Authored synthetic layout (not engine addresses).
SHAPE, VERTS, OUT, BLOCK, POINTS = 0x1000, 0x2000, 0x3000, 0x3100, 0x3200
IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
CUBE = [(sx, sy, sz) for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)]
QNAN_POS, QNAN_NEG1 = 0x7FC00000, 0xFFC00001
M = pq._m(pq.XYZ_MASK)


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def flt(b):
    return struct.unpack('<f', struct.pack('<I', b))[0]


def vec(*xs):
    return [bits(x) for x in xs]


def rows_of(t=(0.0, 0.0, 0.0), rows=IDENT):
    return [vec(*r, 0.0) for r in rows] + [vec(*t, 0.0)]


def hull(points):
    """Kind-5 shape with the constructor's n+1 count and a padding slot."""
    vert = bytearray(12 * (len(points) + 2))
    for i, p in enumerate(points):
        struct.pack_into('<3f', vert, 12 * i, *p)
    shape = bytearray(0x110)
    struct.pack_into('<QI', shape, 0x40, VERTS, len(points) + 1)
    return PoseFlatMemory({SHAPE: shape, VERTS: vert})


def seg(a, b):
    return vec(*a, 0.0), vec(*b, 0.0)


def query(mem, a, b, rows=None, iterations=16, **kw):
    dist, on_hull, on_seg = convex_segment_query(mem, rows or rows_of(), SHAPE, seg(a, b), iterations, **kw)
    return flt(dist[0]), [flt(x) for x in on_hull[:3]], [flt(x) for x in on_seg[:3]], dist


def box(half, a, b, rows=None, iterations=16, **kw):
    dist, on_box, on_seg = box_segment_query(rows or rows_of(), vec(*half, 0.0), seg(a, b), iterations, **kw)
    return flt(dist[0]), [flt(x) for x in on_box[:3]], [flt(x) for x in on_seg[:3]]


class SegmentSupportTest(unittest.TestCase):
    def test_strict_positive_dot_picks_the_second_point(self):
        s = seg((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        self.assertEqual(segment_support(s, vec(1.0, 0.0, 0.0, 0.0), M, 'sse'), 1)
        self.assertEqual(segment_support(s, vec(-1.0, 0.0, 0.0, 0.0), M, 'sse'), 0)
        self.assertEqual(segment_support(s, vec(0.0, 5.0, 0.0, 0.0), M, 'sse'), 0)   # 0 < 0 false
        self.assertEqual(segment_support(s, [QNAN_POS, 0, 0, 0], M, 'sse'), 0)      # NaN never picks 1

    def test_lane_three_is_masked(self):
        s = (vec(0.0, 0.0, 0.0, 0.0), vec(0.0, 0.0, 0.0, 9.0))
        self.assertEqual(segment_support(s, vec(0.0, 0.0, 0.0, 1.0), M, 'sse'), 0)


class HullQueryTest(unittest.TestCase):
    def test_separated_segment_parallel_to_a_face(self):
        d, h, p, _ = query(hull(CUBE), (3.0, -0.5, 0.25), (3.0, 0.5, 0.25))
        self.assertAlmostEqual(d, 2.0, places=5)
        self.assertAlmostEqual(h[0], 1.0, places=5)
        self.assertAlmostEqual(p[0], 3.0, places=5)
        self.assertAlmostEqual(h[1], p[1], places=5)

    def test_segment_crossing_the_hull_is_inside(self):
        trace = []
        d, h, p, _ = query(hull(CUBE), (-3.0, 0.1, 0.2), (3.0, 0.1, 0.2), trace=trace)
        self.assertEqual(d, 0.0)
        self.assertEqual(h, p)
        self.assertEqual(trace[-1]['count'], 4)

    def test_closest_points_edge_to_edge(self):
        # segment along z above the cube edge x=1,y=1: nearest pair is edge-edge
        d, h, p, _ = query(hull(CUBE), (2.0, 2.0, -0.5), (2.0, 2.0, 0.5))
        self.assertAlmostEqual(d, 2 ** 0.5, places=5)
        self.assertAlmostEqual(h[0], 1.0, places=5)
        self.assertAlmostEqual(h[1], 1.0, places=5)

    def test_zero_length_segment_matches_the_point_query(self):
        mem = hull(CUBE)
        for point in ((3.0, 0.25, -0.5), (3.0, 3.0, 0.5), (2.0, -3.0, 4.0), (0.1, 0.2, 0.3)):
            a = vec(*point, 0.0)
            want = pq.convex_point_query(mem, rows_of(), SHAPE, a)
            got = convex_segment_query(mem, rows_of(), SHAPE, (a, list(a)))
            self.assertAlmostEqual(flt(got[0][0]), flt(want[0][0]), places=5)

    def test_zero_iterations_returns_vertex_zero_and_p0(self):
        for it in (0, -1):
            trace = []
            d, h, p, _ = query(hull(CUBE), (5.0, 5.0, 5.0), (6.0, 5.0, 5.0), iterations=it, trace=trace)
            self.assertEqual(h, list(CUBE[0]))
            self.assertEqual(p, [5.0, 5.0, 5.0])
            self.assertEqual(trace, [{'exit': 'iterations', 'count': 1}])

    def test_repeat_needs_the_same_pair(self):
        # one-vertex hull: vertex 0 can be added again with the other segment end
        trace = []
        query(hull([(0.0, 0.0, 0.0)]), (5.0, 1.0, 0.0), (5.0, -1.0, 0.0), trace=trace)
        added = [(t['index'], t['segment']) for t in trace if 'index' in t]
        self.assertEqual(len(set(added)), len(added))
        self.assertIn(trace[-1]['exit'], ('repeat', 'no-progress', 'direction', 'degenerate'))

    def test_vertex_zero_third_product_order(self):
        # b2 lane x vertex z with two NaNs: native multiplies b2 first (first-operand rule)
        mem = hull([(1.0, 2.0, 0.0)])
        struct.pack_into('<I', mem.view(VERTS, 12), 8, QNAN_NEG1)
        rows = rows_of()
        rows[2][0] = QNAN_POS
        dist, on_hull, on_seg = convex_segment_query(mem, rows, SHAPE, seg((5.0, 5.0, 5.0), (6.0, 5.0, 5.0)), 0,
                                                     nan_rule='sse')
        self.assertEqual(on_hull[0], QNAN_POS)
        loop_order = pq._world_vertex(mem, VERTS, 0, rows, M, 'sse')
        self.assertEqual(loop_order[0], QNAN_NEG1)

    def test_degenerate_statics_parameter(self):
        # a hull edge perpendicular to w: both edge weights positive, |e.e| = 4e-6
        mem = hull([(0.0, -1e-3, 0.0), (0.0, 1e-3, 0.0)])
        trace = []
        query(mem, (5.0, 0.0, 0.0), (5.0, 0.0, 0.0), statics=((0x3F800000,) * 4,) * 3, trace=trace)
        self.assertEqual(trace[-1], {'exit': 'degenerate', 'count': 1})
        trace = []
        query(mem, (5.0, 0.0, 0.0), (5.0, 0.0, 0.0), trace=trace)       # 1e-7 statics: a real edge
        self.assertNotEqual(trace[-1]['exit'], 'degenerate')

    def test_memory_form_and_bind(self):
        mem = hull(CUBE)
        block = bytearray(0x50)
        struct.pack_into('<16I', block, 0, *sum(rows_of(t=(1.0, 0.0, 0.0)), []))
        struct.pack_into('<Q', block, 0x40, SHAPE)
        pts = bytearray(struct.pack('<8I', *vec(4.0, 0.0, 0.0, 0.0), *vec(4.0, 1.0, 0.0, 0.0)))
        mem.add(OUT, bytearray(0x30)); mem.add(BLOCK, block); mem.add(POINTS, pts)
        res = segment_query_at(mem, OUT, BLOCK, POINTS)
        self.assertEqual(bytes(mem.view(OUT, 0x30)), struct.pack('<12I', *res[0], *res[1], *res[2]))
        self.assertAlmostEqual(flt(res[0][0]), 2.0, places=5)
        gjk = bind_segment_query(mem, rows_of(t=(1.0, 0.0, 0.0)), SHAPE)
        self.assertEqual(gjk(vec(4.0, 0.0, 0.0, 0.0), vec(4.0, 1.0, 0.0, 0.0)), res)


class BoxQueryTest(unittest.TestCase):
    def test_support_code_and_vertex(self):
        half = vec(1.0, 2.0, 3.0, 0.0)
        self.assertEqual(box_support(half, vec(1.0, 1.0, 1.0)), (0, vec(1.0, 2.0, 3.0, 0.0)))
        code, v = box_support(half, vec(-1.0, 1.0, -1.0))
        self.assertEqual(code, 0x101)
        self.assertEqual(v, vec(-1.0, 2.0, -3.0, 0.0))
        # -0 and NaN are not negative (cmpltps)
        self.assertEqual(box_support(half, [0x80000000, QNAN_NEG1, 0])[0], 0)

    def test_box_distances(self):
        d, h, p = box((1.0, 1.0, 1.0), (3.0, -0.5, 0.25), (3.0, 0.5, 0.25))
        self.assertAlmostEqual(d, 2.0, places=5)
        d, h, p = box((1.0, 2.0, 3.0), (-5.0, 0.0, 0.0), (5.0, 0.0, 0.0))
        self.assertEqual(d, 0.0)
        d, h, p = box((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (2.0, 2.0, 2.0))
        self.assertEqual(h, [1.0, 1.0, 1.0])
        self.assertAlmostEqual(d, 3 ** 0.5, places=5)

    def test_box_matches_the_hull_query_on_its_corners(self):
        mem = hull([(sx * 1.0, sy * 2.0, sz * 0.5) for sx in (1, -1) for sy in (1, -1) for sz in (1, -1)])
        rows = rows_of(t=(0.5, -1.0, 2.0), rows=((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        for a, b in (((4.0, 0.0, 0.0), (4.0, 1.0, 1.0)), ((0.0, 5.0, 3.0), (1.0, -5.0, 3.0)),
                     ((0.3, 0.2, 2.1), (0.3, 0.2, 2.1))):
            hd = flt(convex_segment_query(mem, rows, SHAPE, seg(a, b))[0][0])
            bd = flt(box_segment_query(rows, vec(1.0, 2.0, 0.5, 0.0), seg(a, b))[0][0])
            self.assertAlmostEqual(hd, bd, places=4)


class ReuseTest(unittest.TestCase):
    def test_solvers_and_constants_are_the_point_query_objects(self):
        self.assertIs(mod._SOLVERS, pq._SOLVERS)
        self.assertIs(mod._direction, pq._direction)
        self.assertIs(mod.hull_support, pq.hull_support)
        self.assertEqual(mod.DIRECTION_EPSILON, 0x28800000)
        self.assertEqual(mod.PROGRESS_FACTOR, 0x3F7FFFEF)


if __name__ == '__main__':
    unittest.main()
