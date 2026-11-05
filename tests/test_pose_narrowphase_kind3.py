"""Tests for engine.pose_narrowphase_kind3 (box testers (3,3), (3,4), (3,5)).

The supplied leaves are replaced by small authored stubs, so these tests exercise the
model's own control flow (paths, record fields, tags, capacity handling, reduction),
not the leaves. Native agreement is in
native/snow_host/pose_narrowphase_kind3_validation.json.
"""
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_kind3 as mod
from engine.pose_narrowphase_dispatch import TESTER_TABLE

# Authored synthetic layout.
GEOM, SA, SB, OUT = 0x1000, 0x2000, 0x3000, 0x8000
STACK_LO, SP = 0x40000, 0x7F000
DATA = mod.BOX_EDGE_TABLE_VA - 0xB0             # covers the mask (0x143336890) and edge table
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
CAP_RSP = SP - 0xB8 - 8 - 0x318                  # rsp inside 0x19d9160
CAP_RBP = CAP_RSP + 0x100


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def f4(*v):
    return struct.pack('<4f', *v)


def frame(t, rows=IDENT):
    return b''.join(f4(*r, 0) for r in rows) + f4(*t, 0)


def world(frame_a, frame_b, sa=b'', sb=b'', flags=b'\x01\x00\x01'):
    shape_a = bytearray(0x200); shape_a[0x40:0x40 + len(sa)] = sa
    shape_b = bytearray(0x200); shape_b[0x40:0x40 + len(sb)] = sb
    geom = frame_a + frame_b + struct.pack('<QQ', SA, SB) + flags + bytes(5)
    data = bytearray(0x200)
    return PoseFlatMemory({GEOM: bytearray(geom), SA: shape_a, SB: shape_b,
                           OUT: bytearray(b'\xa5' * 0x30 * 8),
                           STACK_LO: bytearray(SP + 0x100 - STACK_LO), DATA: data})


def record(mem, i=0):
    raw = bytes(mem.view(OUT + 0x30 * i, 0x30))
    f = struct.unpack('<12f', raw)
    w = struct.unpack('<12I', raw)
    return dict(n=f[0:3], depth=f[3], pa=f[4:7], tag=w[7], pb=f[8:11], tail=w[11])


class Stubs:
    """services(rva, mem, rcx, rdx, r8, r9, xmm3) dispatching to authored handlers."""

    def __init__(self, **handlers):
        self.handlers = {getattr(mod, k): v for k, v in handlers.items()}
        self.calls = []

    def __call__(self, rva, mem, rcx, rdx, r8, r9, xmm3=None):
        self.calls.append((rva, rcx, rdx, r8, r9))
        fn = self.handlers.get(rva)
        if fn is None:
            raise AssertionError('unexpected leaf %#x' % rva)
        return fn(mem, rcx, rdx, r8, r9) or 0

    def rvas(self):
        return [c[0] for c in self.calls]


def close(test, got, want, places=5):
    for g, x in zip(got, want):
        test.assertAlmostEqual(g, x, places=places)


# --- (3,4) box-capsule ------------------------------------------------------------------

UNIT_BOX = f4(1, 1, 1, 0)
AXIS_X = ((0, -1, 0), (1, 0, 0), (0, 0, 1))       # capsule local Y -> world X


def capsule_world(h, r, height=1.2):
    return world(frame((0, 0, 0)), frame((0, height, 0), AXIS_X), UNIT_BOX, struct.pack('<2f', h, r))


def capsule_stubs(dist, p_box, p_axis, face=5, plane=(0, 1, 0, 1), sides=None, sat=None, emit=2):
    def gjk(mem, rcx, rdx, r8, r9):
        mem.view(rcx, 0x30)[:] = f4(dist, dist, dist, dist) + f4(*p_box, 0) + f4(*p_axis, 0)

    def plane_fn(mem, rcx, rdx, r8, r9):
        mem.view(rcx, 16)[:] = f4(*plane)

    def side_fn(mem, rcx, rdx, r8, r9):
        planes = sides or [(1, 0, 0, 1), (-1, 0, 0, 1), (0, 0, 1, 1), (0, 0, -1, 1)]
        mem.view(rcx, 0x40)[:] = b''.join(f4(*p) for p in planes)
        mem.set_d(rcx + 0x40, 4)

    def sat_fn(mem, rcx, rdx, r8, r9):
        mem.view(rcx, 12)[:] = struct.pack('<3i', sat, 0, 0)

    return Stubs(SEG_GJK_RVA=gjk, BOX_FACE_PICK_RVA=lambda *a: face, BOX_FACE_PLANE_RVA=plane_fn,
                 BOX_SIDE_PLANES_RVA=side_fn, CAPSULE_HULL_SAT_RVA=sat_fn,
                 CAPSULE_FACE_RVA=lambda *a: emit, CAPSULE_EDGE_RVA=lambda *a: 1)


class BoxCapsuleTests(unittest.TestCase):
    def run_tester(self, mem, stubs, capacity=500):
        return mod.box_capsule_tester(mem, GEOM, OUT, capacity, services=stubs, sp=SP)

    def test_axis_points_reach_the_distance_query(self):
        m = capsule_world(0.5, 0.3)
        s = capsule_stubs(0.2, (0, 1, 0), (0, 1.2, 0))
        seen = {}
        inner = s.handlers[mod.SEG_GJK_RVA]
        def gjk(mem, rcx, rdx, r8, r9):
            seen['ext'] = bytes(mem.view(rdx + 0x40, 16))          # {frame rows, extents}
            return inner(mem, rcx, rdx, r8, r9)
        s.handlers[mod.SEG_GJK_RVA] = gjk
        self.run_tester(m, s)
        rva, rcx, rdx, r8, r9 = s.calls[0]
        self.assertEqual((rva, rcx, rdx, r8, r9),
                         (mod.SEG_GJK_RVA, CAP_RBP + 0x130, CAP_RBP - 0x40, CAP_RSP + 0x40, 0x10))
        close(self, struct.unpack('<3f', bytes(m.view(r8, 12))), (-0.5, 1.2, 0))
        close(self, struct.unpack('<3f', bytes(m.view(r8 + 0x10, 12))), (0.5, 1.2, 0))
        self.assertEqual(seen['ext'], UNIT_BOX[:12] + bytes(4))       # extents & mask

    def test_parallel_face_clip_two_records_with_tags(self):
        m = capsule_world(0.5, 0.3)
        s = capsule_stubs(0.2, (0, 1, 0), (0, 1.2, 0))
        self.assertEqual(self.run_tester(m, s, capacity=0), 2)    # capacity never read
        a, b = record(m, 0), record(m, 1)
        self.assertEqual((a['tag'], b['tag'], a['tail']), (0x80000005, 0x81000005, 0xFFFF0000))
        close(self, a['n'], (0, 1, 0)); self.assertAlmostEqual(a['depth'], -0.1, places=5)
        close(self, a['pa'], (-0.5, 1.0, 0)); close(self, a['pb'], (-0.5, 0.9, 0))
        close(self, b['pa'], (0.5, 1.0, 0))
        self.assertEqual(bytes(m.view(OUT + 0x60, 0x30)), b'\xa5' * 0x30)

    def test_clip_crossings_take_the_outside_point_tag(self):
        m = capsule_world(1.5, 0.3)
        s = capsule_stubs(0.2, (0, 1, 0), (0, 1.2, 0))
        self.assertEqual(self.run_tester(m, s), 2)
        a, b = record(m, 0), record(m, 1)
        close(self, a['pa'], (1.0, 1.0, 0)); close(self, b['pa'], (-1.0, 1.0, 0))
        self.assertEqual((a['tag'], b['tag']), (0x81000005, 0x80000005))

    def test_face_records_filter_on_plane_distance_not_gjk_distance(self):
        m = capsule_world(0.5, 0.3, height=1.4)        # s = 0.4 > r: no record although dist <= r
        s = capsule_stubs(0.1, (0, 1, 0), (0, 1.1, 0))
        self.assertEqual(self.run_tester(m, s), 0)

    def test_failed_clip_falls_back_to_single_record(self):
        m = capsule_world(0.5, 0.3)
        sides = [(1, 0, 0, -2), (-1, 0, 0, 1), (0, 0, 1, 1), (0, 0, -1, 1)]   # whole segment outside
        s = capsule_stubs(0.2, (0, 1, 0), (0, 1.2, 0), sides=sides)
        self.assertEqual(self.run_tester(m, s), 1)
        r = record(m)
        self.assertEqual(r['tag'], 0)
        close(self, r['n'], (0, 1, 0)); self.assertAlmostEqual(r['depth'], -0.1, places=5)
        close(self, r['pa'], (0, 1, 0)); close(self, r['pb'], (0, 0.9, 0))

    def test_tilted_axis_uses_single_record_and_separation(self):
        m = capsule_world(0.5, 0.3)
        s = capsule_stubs(0.2, (0, 1, 0), (0, 1.2, 0), plane=(1, 0, 0, 1))
        self.assertEqual(self.run_tester(m, s), 1)
        self.assertNotIn(mod.BOX_SIDE_PLANES_RVA, s.rvas())
        m = capsule_world(0.5, 0.3)
        s = capsule_stubs(0.5, (0, 1, 0), (0, 1.5, 0), plane=(1, 0, 0, 1))
        self.assertEqual(self.run_tester(m, s), 0)

    def test_deep_path_builds_box_hull_and_dispatches(self):
        for kind, want, rva in ((0, 2, mod.CAPSULE_FACE_RVA), (2, 1, mod.CAPSULE_EDGE_RVA), (1, 0, None), (3, 0, None)):
            m = capsule_world(0.5, 0.3, height=0.5)
            s = capsule_stubs(0.0, (0, 0.5, 0), (0, 0.5, 0), sat=kind)
            self.assertEqual(self.run_tester(m, s), want)
            self.assertEqual(s.rvas()[-1], rva or mod.CAPSULE_HULL_SAT_RVA)
            self.assertNotIn(mod.BOX_FACE_PICK_RVA, s.rvas())
        desc = CAP_RBP + 0x10
        self.assertEqual(struct.unpack('<4QHHH', bytes(m.view(desc, 0x26))),
                         (CAP_RBP + 0x38, CAP_RBP + 0x98, mod.BOX_EDGE_TABLE_VA, mod.BOX_FACE_INDEX_VA, 8, 6, 12))
        self.assertEqual(bytes(m.view(mod.BOX_EDGE_TABLE_VA, 0x60)), mod.box_edge_table())
        self.assertEqual(struct.unpack('<3f', bytes(m.view(CAP_RBP + 0x38, 12))), (1, -1, 1))

    def test_clip_pass_rules(self):
        m = struct.unpack('<4I', mod.XYZ_MASK)
        p0 = [bits(-1), 0, 0, 0x80000001]
        p1 = [bits(1), 0, 0, 0x81000001]
        plane = [bits(1), 0, 0, 0]                       # keep x <= 0
        out = mod._segment_clip_pass([p0, p1], plane, m, 'sse')
        self.assertEqual(out, [p0, [0, 0, 0, 0x81000001]])
        nan = [0x7FC00000, 0, 0, 0x80000001]
        self.assertEqual(mod._segment_clip_pass([nan, p0], plane, m, 'sse'), [p0])


# --- (3,3) box-box ----------------------------------------------------------------------

BB_RSP = SP - 0x28 - 0x420
BB_RBP = BB_RSP + 0x100
BB_SAT = BB_RSP + 0x70


def box_box_stubs(points, depths, separated=0, flip_byte=0, edge=None):
    def sat(mem, rcx, rdx, r8, r9):
        mem.view(rcx, 16)[:] = f4(0, 1, 0, 0)
        mem.set_b(rcx + 0x11, flip_byte)
        return separated

    def edge_fn(mem, rcx, rdx, r8, r9):
        if edge is None:
            return 1
        mem.view(BB_RBP + 0x10, 16)[:] = f4(1, 0, 0, 0)
        mem.set_d(BB_RBP + 0x20, bits(-0.25))
        mem.view(BB_RSP + 0x50, 16)[:] = f4(1, 2, 3, 0)
        mem.view(BB_RSP + 0x60, 16)[:] = f4(4, 5, 6, 0)
        return 0

    def polygon(mem, rcx, rdx, r8, r9):
        for i, p in enumerate(points):
            mem.view(rcx + 0x10 * i, 16)[:] = f4(*p) + b''
        mem.set_d(rcx + 0x80, len(points))

    def clip(mem, rcx, rdx, r8, r9):                     # identity clip: copies the polygon
        mem.view(rcx, 0x10 * r9)[:] = bytes(mem.view(r8, 0x10 * r9))
        return r9

    def depth_fn(mem, rcx, rdx, r8, r9):
        for i, d in enumerate(depths):
            mem.set_d(rcx + 4 * i, bits(d))
        return r8

    def pick4(mem, rcx, rdx, r8, r9):
        mem.view(rcx, 16)[:] = struct.pack('<4I', 5, 0, 2, 1)

    return Stubs(BOX_SAT_RVA=sat, BOX_EDGE_RVA=edge_fn, BOX_PLANES_RVA=lambda *a: 0,
                 BOX_POLYGON_RVA=polygon, CLIP_PLANE_RVA=clip, DEPTHS_RVA=depth_fn,
                 PRUNE_RVA=lambda mem, rcx, rdx, r8, r9: r8, PICK4_RVA=pick4)


class BoxBoxTests(unittest.TestCase):
    PTS = [(0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 1, 0), (0, 0, 1, 0), (2, 0, 0, 0), (3, 0, 0, 0)]

    def run_tester(self, s, capacity=500, flags=b'\x00\x00\x01'):
        m = world(frame((0, 0, 0)), frame((0, 1.5, 0)), UNIT_BOX, UNIT_BOX, flags)
        n = mod.box_box_tester(m, GEOM, OUT, capacity, services=s, sp=SP)
        return m, n

    def test_separated_axis_returns_zero(self):
        _, n = self.run_tester(box_box_stubs(self.PTS[:4], [-1] * 4, separated=1))
        self.assertEqual(n, 0)

    def test_edge_path_ignores_capacity(self):
        s = box_box_stubs(self.PTS[:4], [-1] * 4, edge=True)
        m, n = self.run_tester(s, capacity=0, flags=b'\x00\x01\x01')
        self.assertEqual(n, 1)
        r = record(m)
        self.assertEqual((r['tag'], r['tail'], r['depth']), (0xFF, 0xFFFF0000, -0.25))
        self.assertEqual((r['pa'], r['pb']), ((1, 2, 3), (4, 5, 6)))
        self.assertNotIn(mod.BOX_PLANES_RVA, s.rvas())

    def test_face_path_depth_filter_and_capacity(self):
        s = box_box_stubs(self.PTS[:4], [-0.5, 0.25, -0.25, 0.0])
        m, n = self.run_tester(s)
        self.assertEqual(n, 2)                                   # only depth < 0 (0.0 dropped)
        close(self, record(m, 0)['pb'], (0, 0, 0)); close(self, record(m, 0)['pa'], (0, 0.5, 0))
        close(self, record(m, 1)['pb'], (1, 0, 1))
        s = box_box_stubs(self.PTS[:4], [-0.5, -0.5, -0.5, -0.5])
        m, n = self.run_tester(s, capacity=3)
        self.assertEqual(n, 3)
        self.assertEqual(bytes(m.view(OUT + 0x90, 0x30)), b'\xa5' * 0x30)

    def test_flip_negates_normal_and_swaps_points(self):
        s = box_box_stubs(self.PTS[:4], [-0.5, 1, 1, 1], flip_byte=3)
        m, n = self.run_tester(s)
        r = record(m)
        self.assertEqual((n, r['n']), (1, (-0.0, -1.0, -0.0)))
        close(self, r['pa'], (0, 0, 0)); close(self, r['pb'], (0, 0.5, 0))

    def test_reduce_flag_gathers_four(self):
        s = box_box_stubs(self.PTS, [-1, -2, -3, -4, -5, -6])
        m, n = self.run_tester(s, flags=b'\x01\x00\x01')
        self.assertEqual(n, 4)
        self.assertEqual([record(m, i)['depth'] for i in range(4)], [-6, -1, -3, -2])
        self.assertIn(mod.PICK4_RVA, s.rvas())
        s = box_box_stubs(self.PTS, [-1, -2, -3, -4, -5, -6])
        m, n = self.run_tester(s, flags=b'\x00\x00\x01')
        self.assertEqual(n, 6)                                   # no reduce: 6 > 4 records
        self.assertNotIn(mod.PICK4_RVA, s.rvas())

    def test_clip_driver_stops_below_three_points(self):
        s = box_box_stubs(self.PTS[:2], [-1, -1])
        m, n = self.run_tester(s)
        self.assertEqual(n, 0)
        self.assertEqual(s.rvas().count(mod.CLIP_PLANE_RVA), 1)


# --- (3,5) box-hull and shared data ------------------------------------------------------

class BoxHullAndTableTests(unittest.TestCase):
    def test_entries_agree_with_tester_table(self):
        self.assertEqual(TESTER_TABLE[(3, 3)][1], mod.BOX_BOX_ENTRY_RVA)
        self.assertEqual(TESTER_TABLE[(3, 4)][1], mod.BOX_CAPSULE_ENTRY_RVA)
        self.assertEqual(TESTER_TABLE[(3, 5)][1], mod.BOX_HULL_ENTRY_RVA)
        self.assertEqual(set(mod.TESTERS), {(3, 3), (3, 4), (3, 5)})

    def test_box_hull_layout(self):
        m = PoseFlatMemory({0x100: bytearray(0x400)})
        mod.build_box_hull(m, 0x100, 0x200, 0x300, [bits(1), bits(2), bits(3)])
        self.assertEqual(struct.unpack('<3f', bytes(m.view(0x200 + 12 * 6, 12))), (-1, 2, -3))
        n = struct.unpack('<4fHH', bytes(m.view(0x300 + 0x14 * 4, 0x14)))
        self.assertEqual(n, (0, -1, 0, 2, 4, 16))
        # every edge joins two faces that both list the edge's vertices
        for v0, v1, f0, f1 in mod.BOX_EDGES:
            for f in (f0, f1):
                self.assertTrue({v0, v1} <= set(mod.BOX_FACE_CORNERS[4 * f:4 * f + 4]))

    def test_box_hull_dispatch(self):
        def run(kind):
            m = world(frame((0, 0, 0)), frame((0, 1.5, 0)), UNIT_BOX, b'', b'\x01\x00\x01')
            m.view(SB + 0x100, 8)[:] = struct.pack('<Q', 0x2100)
            calls = Stubs(HULL_SAT_RVA=lambda mem, rcx, *a: mem.set_d(rcx, kind),
                          HULL_EDGE_RVA=lambda *a: 1)
            calls.handlers[mod.HULL_POLYGON_RVA] = lambda *a: 0
            return mod.box_hull_tester(m, GEOM, OUT, 500, services=calls, sp=SP), calls.rvas()
        self.assertEqual(run(2), (1, [mod.HULL_SAT_RVA, mod.HULL_EDGE_RVA]))
        self.assertEqual(run(3), (0, [mod.HULL_SAT_RVA]))

    def test_max_records_table(self):
        self.assertEqual(mod.MAX_RECORDS[(3, 4)]['clip'], 2)
        self.assertFalse(mod.MAX_RECORDS[(3, 4)]['honours_capacity'])
        self.assertIsNone(mod.MAX_RECORDS[(3, 3)]['face_no_reduce'])


if __name__ == '__main__':
    unittest.main()
