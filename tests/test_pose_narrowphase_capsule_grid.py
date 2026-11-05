import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_capsule_grid as mod
from engine.pose_narrowphase_dispatch import TESTER_TABLE
from engine.pose_narrowphase_kind45 import bc, vadd, vsub, mdot

# Authored synthetic layout and fixtures (not game data).
GEOM, GRID, CAPS, SAMPLES, PROF, OUT = 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x8000
CAPS_PROF = PROF + 0x100
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
LYING_X = ((0, -1, 0), (1, 0, 0), (0, 0, 1))      # capsule local Y along world X
FILL = 0xA5


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def f(b):
    return struct.unpack('<f', struct.pack('<I', b))[0]


def vec(*xs):
    return [bits(x) for x in xs] + [0] * (4 - len(xs))


def frame(t, rows=IDENT):
    return b''.join(struct.pack('<3fI', *v, 0) for v in list(rows) + [t])


def scene(capsule_t, capsule_rows=IDENT, half=0.5, radius=0.25, cells=(3, 3), heights=None,
          prelim=0, filtering=0, kind40=2, masks=((1, 1), (1, 1)), swap=True, out_records=40):
    cw, ch = cells
    w, h = cw + 1, ch + 1
    heights = heights or [0.0] * (w * h)
    res = bytearray(0xC0)
    struct.pack_into('<Q', res, 0x20, PROF)
    struct.pack_into('<I', res, 0x40, kind40)
    struct.pack_into('<Q', res, 0x48, SAMPLES)
    struct.pack_into('<2H', res, 0x68, w, h)
    struct.pack_into('<2f', res, 0x70, 1.0, 1.0)
    struct.pack_into('<3f', res, 0x7C, 0.0, 0.0, -5.0)
    struct.pack_into('<3f', res, 0x88, float(cw), float(ch), 5.0)
    struct.pack_into('<2H', res, 0x9C, cw, ch)
    caps = bytearray(0x80)
    struct.pack_into('<Q', caps, 0x20, CAPS_PROF)
    struct.pack_into('<2f', caps, 0x40, half, radius)
    prof = bytearray(0x200)
    struct.pack_into('<2Q', prof, 0x48, *masks[0])
    struct.pack_into('<2Q', prof, 0x148, *masks[1])
    cap_frame, grid_frame = frame(capsule_t, capsule_rows), frame((0, 0, 0))
    if swap:
        geom = cap_frame + grid_frame + struct.pack('<QQ', CAPS, GRID)
    else:
        geom = grid_frame + cap_frame + struct.pack('<QQ', GRID, CAPS)
    geom = bytearray(geom + bytes([prelim, 0, filtering]))
    return PoseFlatMemory({GEOM: geom, GRID: res, CAPS: caps, PROF: prof,
                           SAMPLES: struct.pack('<%df' % len(heights), *heights),
                           OUT: bytes([FILL]) * (0x30 * out_records)})


def record(mem, k):
    raw = bytes(mem.view(OUT + 0x30 * k, 0x30))
    words = struct.unpack('<12I', raw)
    return dict(normal=[f(x) for x in words[0:3]], depth=f(words[3]), pa=[f(x) for x in words[4:7]],
                tag=words[7], pb=[f(x) for x in words[8:11]], tri=words[11], words=words)


class CapsuleGridTesterTest(unittest.TestCase):

    def test_table_entries(self):
        self.assertEqual(TESTER_TABLE[(4, 7)][:2], (0x29CB530, mod.CAPSULE_GRID_ENTRY_RVA))
        self.assertEqual(TESTER_TABLE[(7, 4)][:2], (0x29CB378, mod.GRID_CAPSULE_ENTRY_RVA))

    def test_resting_lying_capsule_two_endpoint_records(self):
        # Axis from (1.25,1.5,0.15) to (2.25,1.5,0.15), radius 0.25 over z = 0: 0.1 deep.
        mem = scene((1.75, 1.5, 0.15), LYING_X)
        n = mod.capsule_grid_tester(mem, GEOM, OUT, 500)
        self.assertEqual(n, 2)
        for k, x in enumerate((1.25, 2.25)):
            r = record(mem, k)
            self.assertEqual(r['normal'], [0.0, 0.0, -1.0])            # capsule -> terrain after the flip
            self.assertAlmostEqual(r['depth'], -0.1, places=6)
            self.assertAlmostEqual(r['pa'][2], -0.1, places=6)         # capsule surface point
            self.assertEqual(r['pb'], [x, 1.5, 0.0])                   # projection on the terrain
            self.assertEqual(r['tag'], 0)
            self.assertIn(r['tri'] >> 1, range(9))

    def test_wrapper_is_forward_plus_reverse(self):
        a = scene((1.6, 1.4, 0.1), LYING_X)
        b = scene((1.6, 1.4, 0.1), LYING_X, swap=False)
        n = mod.capsule_grid_tester(a, GEOM, OUT, 500)
        m = mod.grid_capsule_tester(b, GEOM, OUT, 500)
        self.assertEqual(n, m)
        self.assertGreater(n, 0)
        for k in range(n):
            ra, rb = record(a, k)['words'], record(b, k)['words']
            self.assertEqual(ra[0:3], tuple(x ^ 0x80000000 for x in rb[0:3]))
            self.assertEqual(ra[3], rb[3])
            self.assertEqual(ra[4:7], rb[8:11])
            self.assertEqual(ra[8:11], rb[4:7])
            self.assertEqual((ra[7], ra[11]), (rb[7], rb[11]))

    def test_capacity_is_honoured(self):
        full = scene((1.75, 1.5, 0.15), LYING_X)
        self.assertEqual(mod.capsule_grid_tester(full, GEOM, OUT, 500), 2)
        one = scene((1.75, 1.5, 0.15), LYING_X)
        self.assertEqual(mod.capsule_grid_tester(one, GEOM, OUT, 1), 1)
        self.assertEqual(bytes(one.view(OUT, 0x30)), bytes(full.view(OUT, 0x30)))
        self.assertEqual(bytes(one.view(OUT + 0x30, 0x30)), bytes([FILL]) * 0x30)
        zero = scene((1.75, 1.5, 0.15), LYING_X)
        self.assertEqual(mod.capsule_grid_tester(zero, GEOM, OUT, 0), 0)
        self.assertEqual(bytes(zero.view(OUT, 0x60)), bytes([FILL]) * 0x60)

    def test_same_side_core_capacity_argument(self):
        tri = mod.triangle_block(vec(0, 0, 0), vec(4, 0, 0), vec(0, 4, 0), 'sse')
        p0, p1 = vec(1, 1, 0.1), vec(2, 1, 0.1)
        d = [mdot(tri[6], vsub(p, tri[0], 'sse'), 'sse') for p in (p0, p1)]
        both = mod.same_side_contacts([p0, p1], bits(0.5), bits(0.25), d, tri, 500, 7, 'sse')
        one = mod.same_side_contacts([p0, p1], bits(0.5), bits(0.25), d, tri, 1, 7, 'sse')
        self.assertEqual((len(both), len(one)), (2, 1))
        self.assertEqual(one[0], both[0])

    def test_no_contact_from_a_triangle_under_the_middle_of_the_axis(self):
        # Same-side triangles only report endpoints inside their prism: a capsule lying
        # 0.1 deep with both endpoints beyond the single-cell grid gets nothing.
        mem = scene((0.5, 0.5, 0.15), LYING_X, half=2.0, cells=(1, 1))
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 500), 0)

    def test_separated_capsule(self):
        mem = scene((1.75, 1.5, 0.3), LYING_X)
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 500), 0)

    def test_exact_touch_is_a_contact(self):
        mem = scene((1.75, 1.5, 0.25), LYING_X)
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 500), 2)
        self.assertEqual(record(mem, 0)['depth'], 0.0)

    def test_crossing_capsule_pierce_records(self):
        # Standing capsule through z = 0: every triangle the axis pierces gives depth -(|d| + r)
        # using the endpoint nearer the plane (here the lower one, 0.2 below). The other half
        # of the cell is crossed but not pierced: its record comes from the diagonal edge
        # (axis 0.212 from it, radius 0.25).
        mem = scene((1.3, 1.6, 0.3), ((1, 0, 0), (0, 0, 1), (0, -1, 0)))
        trace = {}
        n = mod.capsule_grid_tester(mem, GEOM, OUT, 500, trace=trace)
        self.assertEqual((n, trace.get('pierce'), trace.get('edge')), (2, 1, 1))
        edge = record(mem, 0)
        self.assertEqual((edge['tri'], edge['normal'][2]), (8, -0.0))
        self.assertAlmostEqual(edge['depth'], 0.3 / 2 ** 0.5 - 0.25, places=5)
        r = record(mem, 1)
        self.assertEqual(r['tri'], 9)
        self.assertAlmostEqual(r['depth'], -(0.2 + 0.25), places=6)
        self.assertEqual(r['normal'], [-0.0, -0.0, -1.0])
        self.assertAlmostEqual(r['pb'][2], 0.0, places=6)

    def test_crossing_edge_path_and_separation(self):
        tri = mod.triangle_block(vec(0, 0, 0), vec(1, 0, 0), vec(0, 1, 0), 'sse')
        p0, d = vec(1.0, 1.0, -0.5), vec(0, 0, 1)
        p1 = vadd(d, p0, 'sse')
        dist = [mdot(tri[6], vsub(p, tri[0], 'sse'), 'sse') for p in (p0, p1)]
        recs, path = mod.crossing_contacts([p0, p1], (p0, d), bits(0.8), dist, tri, 3, 'sse')
        self.assertEqual(path, 'edge')
        words = struct.unpack('<12I', recs[0])
        self.assertAlmostEqual(f(words[3]), (0.5 ** 0.5) - 0.8, places=6)
        self.assertEqual(words[11], 3)
        recs, path = mod.crossing_contacts([p0, p1], (p0, d), bits(0.5), dist, tri, 3, 'sse')
        self.assertEqual((recs, path), ([], 'edge_separated'))

    def test_pierce_test_rejects_parallel_segment(self):
        tri = mod.triangle_block(vec(0, 0, 0), vec(1, 0, 0), vec(0, 1, 0), 'sse')
        hit, _ = mod.segment_pierces_triangle(tri, vec(0.2, 0.2, 0.1), vec(1, 0, 0), 'sse')
        self.assertFalse(hit)
        hit, t = mod.segment_pierces_triangle(tri, vec(0.2, 0.2, -0.1), vec(0, 0, 1), 'sse')
        self.assertTrue(hit)
        self.assertAlmostEqual(f(t[0]), 0.1, places=6)

    def test_preliminary_at_capacity_zero_returns_one_and_flips_record_zero(self):
        mem = scene((1.5, 1.5, 0.0), LYING_X, prelim=1)
        before = bytes(mem.view(OUT, 0x30))
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 0), 1)
        after = struct.unpack('<12I', bytes(mem.view(OUT, 0x30)))
        b = struct.unpack('<12I', before)
        self.assertEqual(after[0:3], tuple(x ^ 0x80000000 for x in b[0:3]))
        self.assertEqual(after[4:7], b[8:11])

    def test_preliminary_record(self):
        mem = scene((1.5, 1.5, -0.1), LYING_X, prelim=1)
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 500), 1)
        r = record(mem, 0)
        self.assertEqual(r['normal'], [-0.0, -0.0, -1.0])
        self.assertAlmostEqual(r['depth'], -0.1 - 0.25, places=6)

    def test_profile_rejection(self):
        mem = scene((1.75, 1.5, 0.15), LYING_X, masks=((1, 0), (1, 0)))
        trace = {}
        self.assertEqual(mod.capsule_grid_tester(mem, GEOM, OUT, 500, trace=trace), 0)
        self.assertGreater(trace['profile_rejected'], 0)

    def test_filter_needs_flag_and_kind_two(self):
        # Rough terrain so the filter's vertex/edge tests have something to reject.
        hs = [0.0, 0.3, 0.0, 0.2, 0.4, 0.0, 0.1, 0.3, 0.0, 0.2, 0.0, 0.3, 0.1, 0.0, 0.2, 0.0]
        results = {}
        for filtering, kind in ((0, 2), (1, 2), (1, 0)):
            mem = scene((1.5, 1.5, 0.1), ((0, -1, 0), (0.6, 0.8, 0), (0, 0, 1)), half=1.4, radius=0.3,
                        heights=hs, filtering=filtering, kind40=kind)
            trace = {}
            results[(filtering, kind)] = (mod.capsule_grid_tester(mem, GEOM, OUT, 500, trace=trace),
                                          trace.get('filtered_out', 0))
        self.assertEqual(results[(0, 2)], results[(1, 0)])
        self.assertEqual(results[(1, 2)], (2, 2))                  # two of four records rejected
        self.assertEqual(results[(1, 2)][0] + results[(1, 2)][1], results[(0, 2)][0])

    def test_zero_half_height_is_a_sphere_axis(self):
        rel = mod.relative_capsule_frame([vec(*r) for r in IDENT] + [vec(0, 0, 0)],
                                         [vec(*r) for r in IDENT] + [vec(1, 2, 3)], 'sse')
        p0, d, p1 = mod.capsule_axis(rel, bits(0.0), 'sse')
        self.assertEqual(p0[:3], p1[:3])
        self.assertEqual([f(x) for x in p0[:3]], [1.0, 2.0, 3.0])

    def test_local_bounds(self):
        rel = [vec(1, 0, 0), vec(0, 0.6, 0.8), vec(0, -0.8, 0.6), vec(1, 2, 3)]
        lo_hi = [f(x) for x in mod.capsule_local_bounds(bits(1.0), bits(0.5), rel, 'sse')]
        expected = [0.5, 2 - 1.1, 3 - 1.3, 1.5, 2 + 1.1, 3 + 1.3]
        for a, b in zip(lo_hi, expected):
            self.assertAlmostEqual(a, b, places=6)

    def test_world_transform_of_records(self):
        # Rotated, translated terrain frame: records come back in world coordinates.
        mem = scene((1.75, 1.5, 0.15), LYING_X)
        ref = scene((1.75, 1.5, 0.15), LYING_X)
        rows = ((0, 1, 0), (-1, 0, 0), (0, 0, 1))
        t = (10.0, 20.0, 30.0)
        geom = mem.view(GEOM, 0x80)
        cap_world = [(-v[1], v[0], v[2]) for v in LYING_X]      # LYING_X rotated by the terrain rows
        c = (1.75, 1.5, 0.15)
        cw = (t[0] - c[1], t[1] + c[0], t[2] + c[2])
        geom[0:0x40] = frame(cw, cap_world)
        geom[0x40:0x80] = frame(t, rows)
        n = mod.capsule_grid_tester(mem, GEOM, OUT, 500)
        self.assertEqual(n, mod.capsule_grid_tester(ref, GEOM, OUT, 500))
        for k in range(n):
            a, b = record(mem, k), record(ref, k)
            self.assertAlmostEqual(a['depth'], b['depth'], places=6)
            self.assertAlmostEqual(a['pb'][0], t[0] - b['pb'][1], places=5)
            self.assertAlmostEqual(a['pb'][1], t[1] + b['pb'][0], places=5)
            self.assertAlmostEqual(a['pb'][2], t[2] + b['pb'][2], places=5)


if __name__ == '__main__':
    unittest.main()
