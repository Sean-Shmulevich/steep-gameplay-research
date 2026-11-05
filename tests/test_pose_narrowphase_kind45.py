import math
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_kind45 as mod
from engine.pose_narrowphase_dispatch import TESTER_TABLE

# Authored synthetic layout and fixtures (not game data).
GEOM, SA, SB, OUT = 0x1000, 0x2000, 0x3000, 0x8000
HULL_A, HULL_B = 0x10000, 0x14000
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
FILL = b'\xa5'


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def lanes(*xs):
    return [bits(x) for x in xs] + [0] * (4 - len(xs))


def frame(t, rows=IDENT):
    return b''.join(struct.pack('<3fI', *v, 0) for v in list(rows) + [t])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, s, 0), (-s, c, 0), (0, 0, 1))


def geom_block(ta, tb, rows_a=IDENT, rows_b=IDENT, sa=SA, sb=SB, reduce=1, edges=1):
    return bytearray(frame(ta, rows_a) + frame(tb, rows_b) + struct.pack('<QQ', sa, sb)
                     + bytes([reduce, edges, 1]))


def capsule_shape(half, radius):
    raw = bytearray(0x80)
    struct.pack_into('<2f', raw, 0x40, half, radius)
    return raw


def prism(n, radius, half):
    """Convex n-gon prism about local Y in the kind-5 descriptor layout (authored)."""
    th = [2 * math.pi * i / n for i in range(n)]
    verts = [[radius * math.cos(t), -half, radius * math.sin(t)] for t in th] + \
            [[radius * math.cos(t), half, radius * math.sin(t)] for t in th]
    faces = [list(range(n)), [n + i for i in range(n - 1, -1, -1)]]
    planes = [[0, -1, 0, half], [0, 1, 0, half]]
    ap = radius * math.cos(math.pi / n)
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, n + i, n + j, j])
        mid = th[i] + math.pi / n
        planes.append([math.cos(mid), 0, math.sin(mid), ap])
    edges = {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            edges.setdefault(tuple(sorted((f[k], f[(k + 1) % len(f)]))), []).append(fi)
    edge_list = []
    for (v0, v1), (f0, f1) in sorted(edges.items()):
        n0, n1 = planes[f0], planes[f1]
        d = [verts[v1][k] - verts[v0][k] for k in range(3)]
        c = [n0[1] * n1[2] - n0[2] * n1[1], n0[2] * n1[0] - n0[0] * n1[2], n0[0] * n1[1] - n0[1] * n1[0]]
        if sum(x * y for x, y in zip(c, d)) < 0:
            v0, v1 = v1, v0
        edge_list.append((v0, v1, f0, f1))
    return dict(vertices=verts, planes=planes, faces=faces, edges=edge_list)


def hull_regions(origin, hull):
    desc = origin + 0x200
    verts, planes, edges, faces = desc + 0x40, desc + 0x400, desc + 0x800, desc + 0xC00
    shape = bytearray(0x108)
    struct.pack_into('<Q', shape, 0x40, verts)
    struct.pack_into('<I', shape, 0x48, len(hull['vertices']))
    struct.pack_into('<Q', shape, 0x100, desc)
    d = bytearray(0x28)
    struct.pack_into('<4Q3H', d, 0, verts, planes, edges, faces, len(hull['vertices']),
                     len(hull['planes']), len(hull['edges']))
    flat, firsts = [], []
    for f in hull['faces']:
        firsts.append(len(flat))
        flat += f
    return {origin: shape, desc: d,
            verts: bytearray(b''.join(struct.pack('<3f', *v) for v in hull['vertices']) + bytes(4)),
            planes: bytearray(b''.join(struct.pack('<4fHH', *p, len(f), s)
                                       for p, f, s in zip(hull['planes'], hull['faces'], firsts))),
            edges: bytearray(b''.join(struct.pack('<4H', *e) for e in hull['edges'])),
            faces: bytearray(struct.pack('<%dH' % len(flat), *flat))}


def record(mem, i=0):
    raw = bytes(mem.view(OUT + 0x30 * i, 0x30))
    f = struct.unpack('<12f', raw)
    w = struct.unpack('<12I', raw)
    return dict(n=f[0:3], depth=f[3], pa=f[4:7], fa=w[7], pb=f[8:11], fb=w[11])


def close(test, got, want, places=5):
    for g, x in zip(got, want):
        test.assertAlmostEqual(g, x, places=places)


def untouched(mem, first):
    return bytes(mem.view(OUT + 0x30 * first, 0x30 * (8 - first))) == FILL * (0x30 * (8 - first))


def capsule_pair(ta, tb, rows_a=IDENT, rows_b=IDENT, a=(1.0, 0.3), b=(1.0, 0.3)):
    return PoseFlatMemory({GEOM: geom_block(ta, tb, rows_a, rows_b), SA: capsule_shape(*a),
                           SB: capsule_shape(*b), OUT: bytearray(FILL * 0x180)})


# B's local Y along world X: rows are B's basis vectors in world coordinates.
ROWS_X = ((0, -1, 0), (1, 0, 0), (0, 0, 1))


class CapsuleCapsuleTests(unittest.TestCase):
    def test_parallel_overlap_gives_two_tagged_records(self):
        m = capsule_pair((0, 0, 0), (0.5, 0, 0))
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 2)
        r0, r1 = record(m, 0), record(m, 1)
        for r, y, tag in ((r0, -1, mod.TAG_START), (r1, 1, mod.TAG_END)):
            close(self, r['n'], (1, 0, 0))
            self.assertAlmostEqual(r['depth'], -0.1, places=6)
            close(self, r['pa'], (0.3, y, 0)); close(self, r['pb'], (0.2, y, 0))
            self.assertEqual((r['fa'], r['fb']), (tag, mod.FEATURE_WORD))
        self.assertTrue(untouched(m, 2))

    def test_capacity_is_never_read(self):
        for cap in (0, 1, 2, 500, 0xFFFFFFFF):
            m = capsule_pair((0, 0, 0), (0.5, 0, 0))
            self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT, cap), 2)

    def test_parallel_separated_writes_nothing(self):
        m = capsule_pair((0, 0, 0), (0.61, 0, 0))
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 0)
        self.assertTrue(untouched(m, 0))

    def test_parallel_offset_axis_clips_to_overlap(self):
        # B shifted along Y by 1.5: A's axis is clipped to B's slab [0.5, 2.5] -> y in [0.5, 1].
        m = capsule_pair((0, 0, 0), (0.5, 1.5, 0))
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 2)
        ys = sorted(record(m, i)['pa'][1] for i in range(2))
        close(self, ys, (0.5, 1.0))

    def test_crossed_capsules_one_record_tag_zero(self):
        m = capsule_pair((0, 0, 0), (0, 0, 0.5), rows_b=ROWS_X)
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 1)
        r = record(m)
        close(self, r['n'], (0, 0, 1)); self.assertAlmostEqual(r['depth'], -0.1, places=6)
        close(self, r['pa'], (0, 0, 0.3)); close(self, r['pb'], (0, 0, 0.2))
        self.assertEqual(r['fa'], 0)
        self.assertTrue(untouched(m, 1))

    def test_exact_touch_is_a_contact(self):
        m = capsule_pair((0, 0, 0), (0, 0, 0.5), rows_b=ROWS_X, a=(1.0, 0.25), b=(1.0, 0.25))
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 1)
        self.assertEqual(record(m)['depth'], 0.0)

    def test_coincident_axes_use_the_cross_product_normal(self):
        m = capsule_pair((0, 0, 0), (0, 0, 0), rows_b=ROWS_X)
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 1)
        r = record(m)
        self.assertAlmostEqual(abs(r['n'][2]), 1.0, places=6)
        self.assertAlmostEqual(r['depth'], -0.6, places=6)

    def test_nan_radius_rejects(self):
        m = capsule_pair((0, 0, 0), (0, 0, 0.5), rows_b=ROWS_X, a=(1.0, float('nan')))
        self.assertEqual(mod.capsule_capsule_tester(m, GEOM, OUT), 0)

    def test_null_shape_raises(self):
        m = capsule_pair((0, 0, 0), (0.5, 0, 0))
        m.view(GEOM + 0x80, 8)[:] = bytes(8)
        with self.assertRaises(ValueError):
            mod.capsule_capsule_tester(m, GEOM, OUT)


def capsule_hull_world(ta, rows_a=IDENT, half=0.5, radius=0.3, hull=None):
    regions = hull_regions(HULL_B, hull or prism(4, math.sqrt(2), 1.0))
    return PoseFlatMemory({GEOM: geom_block(ta, (0, 0, 0), rows_a, sb=HULL_B), SA: capsule_shape(half, radius),
                           OUT: bytearray(FILL * 0x180), **regions})


def fixed_gjk(dist, on_hull, on_axis):
    return lambda p0, p1: (lanes(dist, dist, dist, dist), lanes(*on_hull), lanes(*on_axis))


# prism(4, sqrt 2, 1) rotated so faces are at +-x, +-z: the square has corners on the axes,
# faces at 45 degrees with apothem 1. Rotate the capsule frame instead of the hull.
DIAG = ((math.sqrt(0.5), 0, math.sqrt(0.5)), (0, 1, 0), (-math.sqrt(0.5), 0, math.sqrt(0.5)))


class CapsuleHullTests(unittest.TestCase):
    def test_separated_by_distance(self):
        m = capsule_hull_world((0, 1.6, 0), rows_a=ROWS_X)
        n, path = mod.capsule_hull_tester(m, GEOM, OUT, gjk=fixed_gjk(0.31, (0, 1, 0), (0, 1.31, 0)))
        self.assertEqual((n, path), (0, 'separated'))
        self.assertTrue(untouched(m, 0))

    def test_face_parallel_capsule_gives_two_tagged_records(self):
        # Capsule along world X just above the top face (y = 1): gap 0.2, radius 0.3.
        m = capsule_hull_world((0, 1.2, 0), rows_a=ROWS_X)
        for cap in (0, 1, 500):
            n, path = mod.capsule_hull_tester(m, GEOM, OUT, cap, gjk=fixed_gjk(0.2, (0, 1, 0), (0, 1.2, 0)))
            self.assertEqual((n, path), (2, 'face'))
        r0, r1 = record(m, 0), record(m, 1)
        close(self, r0['n'], (0, -1, 0)); close(self, r1['n'], (0, -1, 0))
        self.assertAlmostEqual(r0['depth'], -0.1, places=6)
        self.assertEqual(r0['fa'] >> 24, 0x80); self.assertEqual(r1['fa'] >> 24, 0x81)
        self.assertEqual(r0['fa'] & 0xFFF, 1)              # top face is plane 1
        close(self, sorted([r0['pa'][0], r1['pa'][0]]), (-0.5, 0.5))
        close(self, r0['pb'], (r0['pa'][0], 1.0, 0))
        self.assertTrue(untouched(m, 2))

    def test_face_clip_to_face_extent(self):
        # Half-height 2 along X over the diamond top face, which spans x in [-sqrt 2, sqrt 2] at z = 0.
        m = capsule_hull_world((0, 1.2, 0), rows_a=ROWS_X, half=2.0)
        n, _ = mod.capsule_hull_tester(m, GEOM, OUT, gjk=fixed_gjk(0.2, (0, 1, 0), (0, 1.2, 0)))
        self.assertEqual(n, 2)
        close(self, sorted(record(m, i)['pa'][0] for i in range(2)), (-math.sqrt(2), math.sqrt(2)))

    def test_tilted_capsule_single_record(self):
        tilt = ((math.cos(0.3), math.sin(0.3), 0), (-math.sin(0.3), math.cos(0.3), 0), (0, 0, 1))
        m = capsule_hull_world((0, 1.5, 0), rows_a=tilt)
        # The path follows the supplied query normal, not the capsule axis: a normal 26.6 degrees
        # off the face normal fails the 0.997 parallel test.
        n, path = mod.capsule_hull_tester(m, GEOM, OUT, gjk=fixed_gjk(0.1, (0.2, 1, 0), (0.25, 1.1, 0)))
        self.assertEqual((n, path), (1, 'single'))
        r = record(m)
        close(self, r['n'], (-1 / math.sqrt(5), -2 / math.sqrt(5), 0)); self.assertAlmostEqual(r['depth'], -0.2, places=6)
        self.assertEqual(r['fa'], 0)
        close(self, r['pb'], (0.2, 1, 0))

    def test_penetrating_vertical_axis_uses_face_contact(self):
        # Axis along Y through the centre: both ends inside the slab only when short.
        m = capsule_hull_world((0, 0.5, 0), half=0.8, radius=0.2)
        n, path = mod.capsule_hull_tester(m, GEOM, OUT, gjk=fixed_gjk(0.0, (0, 0, 0), (0, 0, 0)))
        self.assertEqual(path, 'deep_face')
        self.assertLessEqual(n, 2)
        for i in range(n):
            r = record(m, i)
            self.assertEqual((r['fa'], r['fb']), (0, mod.FEATURE_WORD))
            self.assertLess(r['depth'], 0)
        self.assertTrue(untouched(m, n))

    def test_penetrating_edge_contact_depth_is_squared_distance(self):
        # Axis along Z just inside the vertical edge at the +x corner (x = sqrt 2).
        rows = ((1, 0, 0), (0, 0, 1), (0, -1, 0))      # capsule local Y -> world Z
        m = capsule_hull_world((1.35, 0.2, 0), rows_a=rows, half=1.0, radius=0.1)
        n, path = mod.capsule_hull_tester(m, GEOM, OUT, gjk=fixed_gjk(0.0, (0, 0, 0), (0, 0, 0)))
        self.assertEqual((n, path), (1, 'deep_edge'))
        r = record(m)
        normal = r['n']
        on_axis = [r['pa'][k] - 0.1 * normal[k] for k in range(3)]   # pA = P - r*N, N = -normal
        d2 = sum((r['pb'][k] - on_axis[k]) ** 2 for k in range(3))
        self.assertAlmostEqual(r['depth'], -(d2 + 0.1), places=5)
        self.assertEqual((r['fa'], r['fb']), (0, mod.FEATURE_WORD))
        self.assertTrue(untouched(m, 1))

    def test_face_query_returns_first_positive_plane(self):
        planes = [lanes(0, -1, 0, 1.0), lanes(0, 1, 0, 1.0), lanes(1, 0, 0, 1.0)]
        fr = [lanes(*row) for row in IDENT] + [lanes(0, 0, 0)]
        p0, p1 = lanes(2.0, 0.5, 0), lanes(3.0, 0.5, 0)
        score, idx = mod.hull_face_query(fr, planes, p0, p1, 'sse')
        self.assertEqual(idx, 2); self.assertEqual(score, bits(1.0))
        score, idx = mod.hull_face_query(fr, planes, lanes(0, 0, 0), lanes(0, 0.5, 0), 'sse')
        self.assertEqual((score, idx), (bits(-1.0), 1))    # first strictly greatest minimum (plane 2 ties)

    def test_edge_query_without_edges(self):
        fr = [lanes(*row) for row in IDENT] + [lanes(0, 0, 0)]
        self.assertEqual(mod.hull_edge_query(fr, [], [], [], lanes(0, 0, 0), lanes(0, 1, 0), 'sse'),
                         (mod.FACE_SCORE_INIT, 0xFFFFFFFF, 0xFFFFFFFF))

    def test_clip_never_produces_more_than_two_points(self):
        pts = [(lanes(-1, 0, 0)[:3], mod.TAG_START), (lanes(1, 0, 0)[:3], mod.TAG_END)]
        out = mod.clip_segment(pts, (lanes(1, 0, 0)[:3], bits(0.0)), 'sse')
        # kept p0, then the crossing, which takes the tag of the point it replaces (p1)
        self.assertEqual([t for _, t in out], [mod.TAG_START, mod.TAG_END])
        self.assertEqual(out[1][0][0], 0)


def hull_pair(top_a, rows_b=IDENT, n=4, reduce=1, cap_bytes=0x180):
    a = prism(n, 1.0, 0.5)
    b = prism(n, 1.0, 0.5)
    regions = {**hull_regions(HULL_A, a), **hull_regions(HULL_B, b)}
    return PoseFlatMemory({GEOM: geom_block((0, 0, 0), (0, top_a, 0), IDENT, rows_b, HULL_A, HULL_B, reduce),
                           OUT: bytearray(FILL * cap_bytes), **regions})


class HullHullTests(unittest.TestCase):
    def test_stacked_octagons_reduce_to_four(self):
        m = hull_pair(0.95, n=8, reduce=1)
        self.assertEqual(mod.hull_hull_tester(m, GEOM, OUT, 500), 4)
        self.assertTrue(untouched(m, 4))

    def test_reduction_off_exceeds_four(self):
        m = hull_pair(0.95, n=8, reduce=0)
        self.assertGreater(mod.hull_hull_tester(m, GEOM, OUT, 500), 4)

    def test_capacity_bounds_the_face_emitter(self):
        for cap, want in ((0, 0), (1, 1), (3, 3)):
            m = hull_pair(0.95, n=8, reduce=1)
            self.assertEqual(mod.hull_hull_tester(m, GEOM, OUT, cap), want)
            self.assertTrue(untouched(m, want))

    def test_separated_returns_zero(self):
        m = hull_pair(1.2, n=4)
        self.assertEqual(mod.hull_hull_tester(m, GEOM, OUT, 500), 0)
        self.assertTrue(untouched(m, 0))

    def test_face_records_point_from_a_to_b(self):
        m = hull_pair(0.95, n=4, rows_b=rot_z(0.0))
        n = mod.hull_hull_tester(m, GEOM, OUT, 500)
        self.assertGreater(n, 0)
        for i in range(n):
            r = record(m, i)
            self.assertAlmostEqual(abs(r['n'][1]), 1.0, places=5)
            self.assertAlmostEqual(r['depth'], -0.05, places=5)


class TableAgreementTests(unittest.TestCase):
    def test_entries_match_the_dispatch_table(self):
        self.assertEqual(TESTER_TABLE[(4, 4)][1:], (mod.CAPSULE_CAPSULE_ENTRY_RVA, None))
        self.assertEqual(TESTER_TABLE[(4, 5)][1:], (mod.CAPSULE_HULL_ENTRY_RVA, None))
        self.assertEqual(TESTER_TABLE[(5, 5)][1:], (mod.HULL_HULL_ENTRY_RVA, None))


if __name__ == '__main__':
    unittest.main()
