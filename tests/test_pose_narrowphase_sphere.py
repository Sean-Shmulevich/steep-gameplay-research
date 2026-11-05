import struct
import unittest

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_sphere as mod
from engine.pose_narrowphase_dispatch import TESTER_TABLE
from engine.pose_narrowphase_sphere import (
    bind_sphere_testers, flip_contact_records, sphere_box_tester, sphere_capsule_tester,
    sphere_convex_tester, swapped_geom, FLT_MAX)

# Authored synthetic layout.
GEOM, SA, SB, VERT, PLB, PLANES, OUT = 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x8000
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def frame(t, rows=IDENT, w=7.0):
    return b''.join(struct.pack('<4f', *v, w) for v in list(rows) + [t])


def world(ta, tb, sa=b'', sb=b'', rows_b=IDENT, planes=()):
    shape_a = bytearray(0x200); shape_a[0x40:0x40 + len(sa)] = sa
    shape_b = bytearray(0x200); shape_b[0x40:0x40 + len(sb)] = sb
    struct.pack_into('<Q', shape_b, 0x100, PLB)
    plb = bytearray(0x40)
    struct.pack_into('<QQH', plb, 0, 0, PLANES, 0)
    struct.pack_into('<H', plb, 0x22, len(planes))
    pl = b''.join(struct.pack('<4fI', *p, 0) for p in planes) or bytes(0x14)
    geom = frame(ta) + frame(tb, rows_b) + struct.pack('<QQ', SA, SB) + b'\x01\x02\x03' + bytes(5)
    return PoseFlatMemory({GEOM: bytearray(geom), SA: shape_a, SB: shape_b, PLB: plb,
                           PLANES: bytearray(pl), OUT: bytearray(b'\xa5' * 0x90)})


def record(mem, i=0):
    raw = bytes(mem.view(OUT + 0x30 * i, 0x30))
    f = struct.unpack('<12f', raw)
    w = struct.unpack('<12I', raw)
    return dict(n=f[0:3], depth=f[3], pa=f[4:7], fa=w[7], pb=f[8:11], fb=w[11])


def close(test, got, want, places=5):
    for g, x in zip(got, want):
        test.assertAlmostEqual(g, x, places=places)


class SphereBoxTests(unittest.TestCase):
    BOX = struct.pack('<4f', 1, 1, 1, 99)

    def test_separated_contact_fields(self):
        m = world((1.3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT), 1)
        r = record(m)
        close(self, r['n'], (-1, 0, 0)); self.assertAlmostEqual(r['depth'], -0.2, places=6)
        close(self, r['pa'], (0.8, 0, 0)); close(self, r['pb'], (1, 0, 0))
        self.assertEqual((r['fa'], r['fb']), (0, 0xFFFF0000))
        self.assertEqual(bytes(m.view(OUT + 0x30, 0x60)), b'\xa5' * 0x60)   # one record only

    def test_inside_picks_least_margin_face_and_sign(self):
        m = world((-0.5, 0.1, 0), (0, 0, 0), struct.pack('<f', 0.25), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT), 1)
        r = record(m)
        close(self, r['n'], (1, 0, 0))                     # -(outward -x face normal)
        self.assertAlmostEqual(r['depth'], -0.75, places=6)    # -(margin + r)
        close(self, r['pb'], (-1, 0.1, 0)); close(self, r['pa'], (-0.25, 0.1, 0))

    def test_near_surface_zone_uses_inside_branch(self):
        # dist^2 = 2.5e-5 <= 1e-4: the centre 5e-3 outside the face is treated as inside.
        m = world((1.005, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        sphere_box_tester(m, GEOM, OUT)
        self.assertAlmostEqual(record(m)['depth'], -0.495, places=5)
        m = world((1.02, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        sphere_box_tester(m, GEOM, OUT)
        self.assertAlmostEqual(record(m)['depth'], -0.48, places=5)

    def test_rotated_box_frame_rows(self):
        rows = ((0, 1, 0), (-1, 0, 0), (0, 0, 1))          # box x axis is world +y
        m = world((0, 2.2, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<4f', 2, 0.5, 0.5, 0), rows)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT), 1)
        close(self, record(m)['pb'], (0, 2, 0)); close(self, record(m)['n'], (0, -1, 0))

    def test_no_contact_and_capacity_ignored(self):
        m = world((3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT, 0), 0)
        self.assertEqual(bytes(m.view(OUT, 0x90)), b'\xa5' * 0x90)
        m = world((1.3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT, 0), 1)     # capacity 0 still writes

    def test_touching_counts_and_nan_radius_does_not(self):
        m = world((1.5, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT), 1)           # dist^2 <= r^2
        m = world((1.3, 0, 0), (0, 0, 0), struct.pack('<I', 0x7FC00000), self.BOX)
        self.assertEqual(sphere_box_tester(m, GEOM, OUT), 0)

    def test_null_shape_raises(self):
        m = world((0, 0, 0), (0, 0, 0))
        m.view(GEOM + 0x88, 8)[:] = bytes(8)
        with self.assertRaises(ValueError):
            sphere_box_tester(m, GEOM, OUT)


class SphereCapsuleTests(unittest.TestCase):
    def test_side_contact(self):
        m = world((0.8, 0.5, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<2f', 1, 0.5))
        self.assertEqual(sphere_capsule_tester(m, GEOM, OUT), 1)
        r = record(m)
        close(self, r['n'], (-1, 0, 0)); self.assertAlmostEqual(r['depth'], -0.2, places=6)
        close(self, r['pa'], (0.3, 0.5, 0)); close(self, r['pb'], (0.5, 0.5, 0))

    def test_segment_clamped_to_end_cap(self):
        m = world((0, 1.6, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<2f', 1, 0.5))
        sphere_capsule_tester(m, GEOM, OUT)
        r = record(m)
        close(self, r['n'], (0, -1, 0)); close(self, r['pb'], (0, 1.5, 0))

    def test_strict_radius_test(self):
        m = world((1, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<2f', 1, 0.5))
        self.assertEqual(sphere_capsule_tester(m, GEOM, OUT), 0)       # dist^2 == rsum^2 fails

    def test_degenerate_centre_on_axis(self):
        m = world((0, 0.25, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<2f', 1, 0.5))
        self.assertEqual(sphere_capsule_tester(m, GEOM, OUT), 1)
        r = record(m)
        self.assertEqual(struct.unpack('<I', bytes(m.view(OUT + 0xC, 4)))[0], 0)   # depth +0.0
        close(self, r['n'], (1, 0, 0))            # (Dy, -Dx, 0) normalised, D = (0, 2, 0)
        close(self, r['pa'], (0.5, 0.25, 0)); close(self, r['pb'], (-0.5, 0.25, 0))

    def test_degenerate_axis_choice_tilted(self):
        # D = (0, 0, 2) (frame row 1 is world z): min(|Dx|,|Dy|) < |Dz| and |Dy| !< |Dx|.
        rows = ((1, 0, 0), (0, 0, 1), (0, -1, 0))
        m = world((0, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), struct.pack('<2f', 1, 0.5), rows)
        sphere_capsule_tester(m, GEOM, OUT)
        close(self, record(m)['n'], (0, 1, 0))    # (0, Dz, -Dy)

    def test_zero_half_height_behaves_like_a_sphere(self):
        m = world((1, 0, 0), (0, 0, 0), struct.pack('<f', 0.6), struct.pack('<2f', 0, 0.6))
        self.assertEqual(sphere_capsule_tester(m, GEOM, OUT), 1)       # t = 0/0 -> minps -> 1
        close(self, record(m)['n'], (-1, 0, 0)); self.assertAlmostEqual(record(m)['depth'], -0.2, places=6)


def query(dist, on_hull, on_point):
    def q(frame_rows, shape, point):
        q.calls.append((frame_rows, shape, point))
        return [[bits(dist)] * 4, [bits(x) for x in on_hull] + [0], [bits(x) for x in on_point] + [0]]
    q.calls = []
    return q


CUBE = [(1, 0, 0, 1), (-1, 0, 0, 1), (0, 1, 0, 1), (0, -1, 0, 1), (0, 0, 1, 1), (0, 0, -1, 1)]


class SphereConvexTests(unittest.TestCase):
    def test_shallow_uses_query_points(self):
        m = world((1.3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), planes=CUBE)
        q = query(0.3, (1, 0, 0), (1.3, 0, 0))
        self.assertEqual(sphere_convex_tester(m, GEOM, OUT, point_query=q), 1)
        r = record(m)
        close(self, r['n'], (-1, 0, 0)); self.assertAlmostEqual(r['depth'], -0.2, places=6)
        close(self, r['pa'], (0.8, 0, 0)); close(self, r['pb'], (1, 0, 0))
        rows, shape, point = q.calls[0]
        self.assertEqual(shape, SB); self.assertEqual(point, [bits(1.3), 0, 0, 0])
        self.assertEqual(rows[0], [bits(1), 0, 0, 0])            # masked rows

    def test_separated_beyond_radius(self):
        m = world((3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), planes=CUBE)
        self.assertEqual(sphere_convex_tester(m, GEOM, OUT, point_query=query(2, (1, 0, 0), (3, 0, 0))), 0)

    def test_deep_picks_largest_signed_distance_plane(self):
        m = world((0.7, 0.2, 0), (0, 0, 0), struct.pack('<f', 0.5), planes=CUBE)
        self.assertEqual(sphere_convex_tester(m, GEOM, OUT, point_query=query(0, (0.7, 0.2, 0), (0.7, 0.2, 0))), 1)
        r = record(m)
        close(self, r['n'], (-1, 0, 0)); self.assertAlmostEqual(r['depth'], -0.8, places=6)
        close(self, r['pb'], (1, 0.2, 0)); close(self, r['pa'], (0.2, 0.2, 0))

    def test_deep_plane_in_box_frame(self):
        rows = ((0, 1, 0), (-1, 0, 0), (0, 0, 1))
        m = world((0.1, 2.6, 0), (0, 2, 0), struct.pack('<f', 0.5), rows_b=rows, planes=CUBE)
        sphere_convex_tester(m, GEOM, OUT, point_query=query(0, (0, 0, 0), (0, 0, 0)))
        close(self, record(m)['n'], (0, -1, 0)); close(self, record(m)['pb'], (0.1, 3, 0))

    def test_deep_without_planes(self):
        m = world((0.1, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), planes=())
        sphere_convex_tester(m, GEOM, OUT, point_query=query(0, (0, 0, 0), (0, 0, 0)))
        w = struct.unpack('<12I', bytes(m.view(OUT, 0x30)))
        self.assertEqual(w[0:3], (0x80000000,) * 3)
        self.assertEqual(w[3], FLT_MAX | 0x80000000)            # -(FLT_MAX + r) rounds to -FLT_MAX
        self.assertEqual(w[8:11], (bits(0.1), 0, 0))


class FlipAndSwapTests(unittest.TestCase):
    def test_flip_negates_normal_and_exchanges_points(self):
        raw = bytearray()
        for i in range(3):
            raw += struct.pack('<4f', 1 + i, 0, -0.0, -0.5) + struct.pack('<3fI', 2, 3, 4, 77) + struct.pack('<3fI', 5, 6, 7, 99)
        m = PoseFlatMemory({OUT: bytearray(raw)})
        flip_contact_records(m, OUT, OUT + 0x60)
        for i in range(2):
            r = record(m, i)
            self.assertEqual(r['n'], (-1 - i, -0.0, 0.0)); self.assertEqual(r['depth'], -0.5)
            self.assertEqual(r['pa'], (5, 6, 7)); self.assertEqual(r['pb'], (2, 3, 4))
            self.assertEqual((r['fa'], r['fb']), (77, 99))
        self.assertEqual(bytes(m.view(OUT + 0x60, 0x30)), bytes(raw[0x60:]))
        self.assertEqual(struct.unpack('<I', bytes(m.view(OUT + 4, 4)))[0], 0x80000000)

    def test_swapped_geom_layout(self):
        raw = bytes(range(0x80)) + struct.pack('<QQ', 0xA, 0xB) + b'\x01\x02\x03'
        g = swapped_geom(raw, lane3=0xEEEEEEEE)
        self.assertEqual(g[0:12], raw[0x40:0x4C]); self.assertEqual(g[0x40:0x4C], raw[0:12])
        self.assertEqual(g[12:16], b'\xee' * 4)
        self.assertEqual(struct.unpack_from('<QQ', g, 0x80), (0xB, 0xA)); self.assertEqual(g[0x90:0x93], b'\x01\x02\x03')

    def test_box_sphere_swap_is_forward_then_flip(self):
        # (3,2): shape A is the box, B the sphere.
        box = struct.pack('<4f', 1, 1, 1, 0)
        m = world((0, 0, 0), (1.3, 0, 0), box, struct.pack('<f', 0.5))
        fwd = world((1.3, 0, 0), (0, 0, 0), struct.pack('<f', 0.5), box)
        testers = bind_sphere_testers(point_query=None)
        self.assertEqual(testers[(3, 2)](m, GEOM, OUT, 500), 1)
        self.assertEqual(sphere_box_tester(fwd, GEOM, OUT), 1)
        a, b = record(m), record(fwd)
        close(self, a['n'], [-x for x in b['n']]); self.assertEqual(a['depth'], b['depth'])
        self.assertEqual(a['pa'], b['pb']); self.assertEqual(a['pb'], b['pa'])
        close(self, a['n'], (1, 0, 0))                          # still from A (box) toward B (sphere)

    def test_table_agrees_with_dispatch_module(self):
        self.assertEqual(TESTER_TABLE[(2, 3)][1], mod.SPHERE_BOX_ENTRY_RVA)
        self.assertEqual(TESTER_TABLE[(2, 4)][1], mod.SPHERE_CAPSULE_ENTRY_RVA)
        self.assertEqual(TESTER_TABLE[(2, 5)][1], mod.SPHERE_CONVEX_ENTRY_RVA)
        for pair, (entry, forward) in mod.SWAP_ENTRIES.items():
            self.assertEqual(TESTER_TABLE[pair][1:], (entry, forward))
        self.assertEqual(set(bind_sphere_testers(point_query=None)), {(2, 3), (2, 4), (2, 5), (3, 2), (4, 2), (5, 2)})


if __name__ == '__main__':
    unittest.main()
