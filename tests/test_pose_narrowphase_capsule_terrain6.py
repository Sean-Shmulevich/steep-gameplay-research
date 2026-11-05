"""Tests for engine.pose_narrowphase_capsule_terrain6 with authored kind-6 fixtures.

The tree query is an authored stub (every triangle in index order, truncated to the
capacity), not the native 0x1952b20; native agreement is in
native/snow_host/pose_narrowphase_capsule_terrain6_validation.json.
"""
import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_capsule_terrain6 as mod

GEOM, CAPS, TERR, MESH, FILT = 0x1000, 0x2000, 0x3000, 0x4000, 0x5000
VERTS, INDS, GROUPS, FBYTES, OUT = 0x10000, 0x20000, 0x28000, 0x2C000, 0x30000
OUT_RECORDS = 64


def fb(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def bf(b):
    return struct.unpack('<f', struct.pack('<I', b))[0]


def frame(rows=((1, 0, 0), (0, 1, 0), (0, 0, 1)), t=(0, 0, 0)):
    return b''.join(struct.pack('<3fI', *r, 0) for r in list(rows) + [t])


def grid(nx, nz, spacing=1.0, height=0.0):
    verts = [(x * spacing, height, z * spacing) for z in range(nz) for x in range(nx)]
    tris = []
    for j in range(nz - 1):
        for i in range(nx - 1):
            a, b, c, d = j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i
            tris += [(a, d, c), (a, c, b)]          # both wound for a +Y normal
    return verts, tris


def build(verts, tris, groups=None, *, h=1.0, r=0.25, cap_rows=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
          cap_t=(0, 0, 0), ter_rows=((1, 0, 0), (0, 1, 0), (0, 0, 1)), ter_t=(0, 0, 0), mode=0,
          scale=(1, 1, 1), flag90=1, flag92=1, filters=None):
    groups = groups if groups is not None else list(range(len(tris)))
    geom = bytearray(0x98)
    geom[0:0x40] = frame(cap_rows, cap_t)
    geom[0x40:0x80] = frame(ter_rows, ter_t)
    struct.pack_into('<QQ', geom, 0x80, CAPS, TERR)
    geom[0x90], geom[0x92] = flag90, flag92
    caps = bytearray(0x80)
    struct.pack_into('<2f', caps, 0x40, h, r)
    struct.pack_into('<Q', caps, 0x20, FILT)
    terr = bytearray(0x100)
    struct.pack_into('<H', terr, 0x28, 6)
    struct.pack_into('<I', terr, 0x40, mode)
    struct.pack_into('<Q', terr, 0x48, MESH)
    struct.pack_into('<3f', terr, 0x70, *scale)
    filt = bytearray(0x400)
    struct.pack_into('<QQ', filt, 0x48, 0b01, 0b01)          # capsule masks
    struct.pack_into('<QQ', filt, 0x148, 0b01, 0b01)         # admits
    struct.pack_into('<QQ', filt, 0x248, 0b10, 0b10)         # rejects
    struct.pack_into('<2Q', filt, 0x380, FILT + 0x100, FILT + 0x200)
    fbytes = bytearray(len(tris) + 8)
    if filters is not None:
        struct.pack_into('<I', terr, 0x68, 1)
        struct.pack_into('<QQ', terr, 0x50, FILT + 0x380, 0)
        struct.pack_into('<Q', terr, 0x60, FBYTES)
        fbytes[:len(filters)] = bytes(filters)
    mesh = bytearray(0x100)
    struct.pack_into('<Q', mesh, 0x30, VERTS)
    struct.pack_into('<Q', mesh, 0x40, INDS)
    struct.pack_into('<I', mesh, 0x48, len(tris))
    struct.pack_into('<Q', mesh, 0x70, GROUPS)
    vraw = struct.pack('<%df' % (3 * len(verts)), *[c for v in verts for c in v]) + bytes(16)
    iraw = struct.pack('<%dH' % (3 * len(tris)), *[i for t in tris for i in t]) + bytes(8)
    graw = struct.pack('<%dH' % len(groups), *groups) + bytes(8)
    return PoseFlatMemory({GEOM: geom, CAPS: caps, TERR: terr, MESH: mesh, FILT: filt, VERTS: vraw, INDS: iraw,
                           GROUPS: graw, FBYTES: fbytes, OUT: bytearray(b'\xee' * (0x30 * OUT_RECORDS))})


def all_query(mem, calls=None):
    count = struct.unpack('<I', bytes(mem.view(MESH + 0x48, 4)))[0]

    def query(tree, aabb, cap):
        assert tree == MESH + 0x80
        if calls is not None:
            calls.append((aabb, cap))
        return list(range(count))[:cap]
    return query


def records(mem, n):
    out = []
    for i in range(n):
        w = struct.unpack('<12I', bytes(mem.view(OUT + 0x30 * i, 0x30)))
        out.append(dict(n=[bf(x) for x in w[0:3]], depth=bf(w[3]), pa=[bf(x) for x in w[4:7]], tag=w[7],
                        pb=[bf(x) for x in w[8:11]], feature=w[11]))
    return out


def run(mem, cap=500, **kw):
    return mod.capsule_terrain_tester(mem, GEOM, OUT, cap, query=kw.pop('query', all_query(mem)), **kw)


# A capsule lying along X on the plane y=0, axis at height 0.2 (radius 0.25 -> 0.05 deep).
LYING = dict(cap_rows=((0, -1, 0), (1, 0, 0), (0, 0, 1)), h=0.4, r=0.25)


class Helpers(unittest.TestCase):
    def test_inverse_of_rotation_is_transpose(self):
        rows = [[0, fb(1.0), 0, 0], [fb(-1.0), 0, 0, 0], [0, 0, fb(1.0), 0]]
        inv = mod.inverse3(rows, 'sse')
        self.assertEqual([[bf(x) for x in r[:3]] for r in inv], [[0, -1, 0], [1, 0, 0], [0, 0, 1]])
        self.assertTrue(all(r[3] == 0 for r in inv))

    def test_relative_axis_and_bounds_upright(self):
        ident = [[fb(1.0), 0, 0, 0], [0, fb(1.0), 0, 0], [0, 0, fb(1.0), 0], [0, 0, 0, 0]]
        cap = [[fb(1.0), 0, 0, 0], [0, fb(1.0), 0, 0], [0, 0, fb(1.0), 0], [fb(2.0), fb(3.0), fb(-1.0), 0]]
        rel, p0, d, p1 = mod.relative_capsule(ident, cap, fb(0.5), 'sse')
        self.assertEqual([bf(x) for x in p0[:3]], [2.0, 2.5, -1.0])
        self.assertEqual([bf(x) for x in d[:3]], [0.0, 1.0, 0.0])
        self.assertEqual([bf(x) for x in p1[:3]], [2.0, 3.5, -1.0])
        box = mod.capsule_bounds(fb(0.5), fb(0.25), rel, 'sse')
        self.assertEqual([bf(x) for x in box], [1.75, 2.25, -1.25, 2.25, 3.75, -0.75])

    def test_query_bounds_divide_by_scale(self):
        q = mod.query_bounds([fb(x) for x in (1, 2, 4, 2, 4, 8)], [fb(2.0), fb(4.0), fb(-4.0)], 'sse')
        self.assertEqual([bf(x) for x in q], [0.5, 0.5, -1.0, 1.0, 1.0, -2.0])

    def test_nearest_edges_ties_go_later(self):
        e = [mod.bc(fb(x)) for x in (1.0, 1.0, 1.0)]
        self.assertEqual(mod.nearest_edges(e, 1), [2])
        self.assertEqual(mod.nearest_edges(e, 2), [1, 0])
        e = [mod.bc(fb(x)) for x in (0.5, 2.0, 1.0)]
        self.assertEqual(mod.nearest_edges(e, 1), [0])
        self.assertEqual(mod.nearest_edges(e, 2), [0, 2])

    def test_segment_hit(self):
        tri = mod.triangle_block([[0, 0, 0, 0], [0, 0, fb(1.0), 0], [fb(1.0), 0, 0, 0]], 'sse')
        down = [0, fb(-1.0), 0, 0]
        self.assertTrue(mod.segment_hits_triangle(tri, [fb(0.2), fb(0.5), fb(0.2), 0], down, 'sse'))
        self.assertFalse(mod.segment_hits_triangle(tri, [fb(0.8), fb(0.5), fb(0.8), 0], down, 'sse'))
        self.assertFalse(mod.segment_hits_triangle(tri, [fb(0.2), fb(1.5), fb(0.2), 0], down, 'sse'))


class Tester(unittest.TestCase):
    def test_lying_capsule_on_one_triangle_two_records(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        mem = build(verts, [(0, 1, 2)], [9], cap_t=(0, 0.2, 0), **LYING)
        n = run(mem)
        self.assertEqual(n, 2)
        for rec in records(mem, n):
            self.assertEqual(rec['n'], [0.0, -1.0, 0.0])           # from capsule (A) toward terrain
            self.assertAlmostEqual(rec['depth'], -0.05, places=6)
            self.assertAlmostEqual(rec['pb'][1], 0.0, places=6)     # B point (after flip) on the plane
            self.assertAlmostEqual(rec['pa'][1], -0.05, places=6)   # A point on the capsule surface
            self.assertEqual(rec['feature'], (0 << 16) | 9)
            self.assertEqual(rec['tag'], 0)

    def test_capacity_honoured(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        for cap, want in ((0, 0), (1, 1), (2, 2), (500, 2)):
            mem = build(verts, [(0, 1, 2)], cap_t=(0, 0.2, 0), **LYING)
            self.assertEqual(run(mem, cap), want)
            if cap == 0:
                self.assertEqual(bytes(mem.view(OUT, 0x30)), b'\xee' * 0x30)

    def test_more_than_four_from_many_triangles(self):
        verts, tris = grid(9, 3, spacing=0.5)
        mem = build(verts, tris, cap_t=(2.0, 0.2, 0.5), h=1.6, r=0.25,
                    cap_rows=((0, -1, 0), (1, 0, 0), (0, 0, 1)))
        n = run(mem)
        self.assertGreater(n, 4)
        recs = records(mem, n)
        self.assertEqual(len({r['feature'] >> 16 for r in recs}), len({r['feature'] & 0xFFFF for r in recs}))
        self.assertTrue(all(r['n'][1] < -0.99 for r in recs))
        self.assertLessEqual(run(build(verts, tris, cap_t=(2.0, 0.2, 0.5), h=1.6, r=0.25,
                                       cap_rows=((0, -1, 0), (1, 0, 0), (0, 0, 1))), 3), 3)

    def test_crossing_capsule_one_record(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        mem = build(verts, [(0, 1, 2)], cap_t=(0, 0.3, 0), h=0.5, r=0.1)
        self.assertEqual(run(mem), 1)
        rec = records(mem, 1)[0]
        # nearest end (y = -0.2) is 0.2 below the plane: depth = -0.2 - 0.1
        self.assertAlmostEqual(rec['depth'], -0.3, places=6)
        self.assertEqual(rec['n'], [0.0, -1.0, 0.0])

    def test_separated_gives_zero(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        mem = build(verts, [(0, 1, 2)], cap_t=(0, 1.0, 0), **LYING)
        self.assertEqual(run(mem), 0)

    def test_collision_filter_rejects(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        self.assertEqual(run(build(verts, [(0, 1, 2)], cap_t=(0, 0.2, 0), filters=[1], **LYING)), 0)
        self.assertEqual(run(build(verts, [(0, 1, 2)], cap_t=(0, 0.2, 0), filters=[0], **LYING)), 2)

    def test_mode1_backface_filter(self):
        verts = [(-2, 0, -2), (2, 0, 0), (-2, 0, 2)]           # wound for a -Y normal
        kw = dict(cap_t=(0, 0.2, 0), **LYING)
        self.assertEqual(run(build(verts, [(0, 1, 2)], mode=0, **kw)), 2)
        self.assertEqual(run(build(verts, [(0, 1, 2)], mode=1, **kw)), 0)
        self.assertEqual(run(build(verts, [(0, 1, 2)], mode=1, flag92=0, **kw)), 2)

    def test_mode2_uses_supplied_filter(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        mem = build(verts, [(0, 1, 2)], mode=2, cap_t=(0, 0.2, 0), **LYING)
        seen = []
        n = run(mem, edge_filter=lambda m, shape, tri, at, count: seen.append((shape, tri, count)) or 1)
        self.assertEqual((n, seen), (1, [(TERR, 0, 2)]))

    def test_query_overflow_requery(self):
        verts, tris = grid(10, 9, spacing=0.3)               # 144 triangles
        mem = build(verts, tris, cap_t=(1.0, 3.0, 1.0))
        calls = []
        run(mem, query=all_query(mem, calls))
        self.assertEqual([c[1] for c in calls], [0x80, 144])
        self.assertEqual(calls[0][0], calls[1][0])
        calls = []
        verts, tris = grid(5, 5)
        mem = build(verts, tris, cap_t=(1.0, 3.0, 1.0))
        run(mem, query=all_query(mem, calls))
        self.assertEqual([c[1] for c in calls], [32])

    def test_key_pass_keeps_deepest_normal(self):
        mem = PoseFlatMemory({OUT: bytearray(0x30 * 4)})
        rows = [((0, 1, 0), -0.1, 5), ((0.1, 0.99, 0), -0.3, 5), ((0, 1, 0), -0.2, 6), ((0.1, 0.99, 0), -0.05, 5)]
        for i, (n, d, key) in enumerate(rows):
            mem.view(OUT + 0x30 * i, 0x30)[:] = struct.pack('<3fI12xI12xI', *n, fb(d), i, key | (i << 16))
        n = mod.key_pass(mem, OUT, 4, 'sse')
        kept = sorted(struct.unpack_from('<I', bytes(mem.view(OUT + 0x30 * i, 0x30)), 0x1C)[0] for i in range(n))
        self.assertEqual(kept, [1, 2, 3])     # key 5: deepest (-0.3) has (0.1, 0.99, 0); record 0 removed

    def test_key_pass_nan_depth_is_taken(self):
        mem = PoseFlatMemory({OUT: bytearray(0x30 * 2)})
        mem.view(OUT, 0x30)[:] = struct.pack('<3fI12xI12xI', 0, 1, 0, fb(-0.5), 0, 1)
        mem.view(OUT + 0x30, 0x30)[:] = struct.pack('<3fI12xI12xI', 1, 0, 0, 0x7FC00000, 1, 1)
        self.assertEqual(mod.key_pass(mem, OUT, 2, 'sse'), 1)
        self.assertEqual(struct.unpack_from('<I', bytes(mem.view(OUT, 0x30)), 0x1C)[0], 1)

    def test_no_key_pass_without_flag(self):
        verts, tris = grid(9, 3, spacing=0.5)
        kw = dict(cap_t=(2.0, 0.2, 0.5), h=1.6, r=0.25, cap_rows=((0, -1, 0), (1, 0, 0), (0, 0, 1)))
        a = run(build(verts, tris, [1] * len(tris), **kw))
        b = run(build(verts, tris, [1] * len(tris), flag90=0, **kw))
        self.assertGreaterEqual(b, a)

    def test_swap_and_terrain_frame(self):
        verts = [(-2, 0, -2), (-2, 0, 2), (2, 0, 0)]
        # terrain rotated 90 degrees about Z and moved; the capsule placed accordingly
        ter_rows = ((0, 1, 0), (-1, 0, 0), (0, 0, 1))
        mem = build(verts, [(0, 1, 2)], ter_rows=ter_rows, ter_t=(5, 0, 0), cap_t=(4.8, 0, 0),
                    cap_rows=((-1, 0, 0), (0, 1, 0), (0, 0, 1)), h=0.4, r=0.25)
        n = run(mem)
        self.assertEqual(n, 2)
        for rec in records(mem, n):
            self.assertAlmostEqual(rec['n'][0], 1.0, places=6)      # world: terrain normal is -X
            self.assertAlmostEqual(rec['pb'][0], 5.0, places=6)


if __name__ == '__main__':
    unittest.main()
