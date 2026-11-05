import struct
import unittest

from engine import pose_narrowphase_dispatch as np_
from engine.pose_pair_link_worker import PoseFlatMemory

GEOM, SA, SB, OUT, DISP, HEAP = 0x1000, 0x2000, 0x3000, 0x4000, 0x5000, 0x8000


def f(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def unf(words):
    return [struct.unpack('<f', struct.pack('<I', w))[0] for w in words]


def build(ta, tb, ra, rb, out_fill=b'\xaa'):
    geom = bytearray(0x98)
    for base in (0x00, 0x40):
        for r in range(3):
            struct.pack_into('<4f', geom, base + 0x10 * r, *[1.0 if k == r else 0.0 for k in range(4)])
    struct.pack_into('<3f', geom, 0x30, *ta)
    struct.pack_into('<3f', geom, 0x70, *tb)
    struct.pack_into('<QQ', geom, 0x80, SA, SB)
    sa, sb = bytearray(0x48), bytearray(0x48)
    struct.pack_into('<f', sa, 0x40, ra)
    struct.pack_into('<f', sb, 0x40, rb)
    return PoseFlatMemory({GEOM: geom, SA: sa, SB: sb, OUT: bytearray(out_fill * 0x60)})


def record(mem):
    return struct.unpack('<12I', bytes(mem.view(OUT, 0x30)))


class TesterTableTests(unittest.TestCase):
    def test_cell_offset_matches_selector_formula(self):
        self.assertEqual(np_.table_cell_offset(2, 2), 0x98)
        self.assertEqual(np_.table_cell_offset(7, 5), 0x1F0)
        self.assertEqual(np_.table_cell_offset(0x8002, 0x8003), np_.table_cell_offset(2, 3))

    def test_table_has_32_cells_and_null_terrain_pairs(self):
        self.assertEqual(len(np_.TESTER_TABLE), 32)
        for a in range(8):
            for b in range(8):
                filled = (a, b) in np_.TESTER_TABLE
                expect = a >= 2 and b >= 2 and not (a >= 6 and b >= 6)
                self.assertEqual(filled, expect, (a, b))

    def test_swapped_cells_point_at_forward_cells(self):
        swapped = {k: v[2] for k, v in np_.TESTER_TABLE.items() if v[2]}
        self.assertEqual(set(swapped), {(3, 2), (4, 2), (4, 3), (5, 2), (5, 3), (5, 4)})
        for (a, b), fwd in swapped.items():
            self.assertEqual(fwd, (b, a))

    def test_build_and_select(self):
        mem = PoseFlatMemory({DISP: bytearray(b'\x77' * 0x208), HEAP: bytearray(0x200), SA: bytearray(0x48),
                              SB: bytearray(0x48)})
        addrs = iter(range(HEAP, HEAP + 0x200, 0x10))
        calls = []

        def alloc(size, align, tag):
            calls.append((size, align, tag))
            a = next(addrs)
            return 0 if a == HEAP + 0x20 else a          # third allocation fails
        made = np_.build_pose_tester_table(mem, DISP, alloc)
        self.assertEqual(calls, [(8, 16, 10)] * 32)
        self.assertEqual(made[2], 0)
        mem.view(SA + 0x28, 2)[:] = struct.pack('<H', 2)
        mem.view(SB + 0x28, 2)[:] = struct.pack('<H', 2)
        tester = np_.select_pose_tester(mem, DISP, SA, SB)
        self.assertEqual(tester, HEAP)
        self.assertEqual(struct.unpack('<Q', bytes(mem.view(tester, 8)))[0], 0x140000000 + 0x29CB1C0)
        mem.view(SB + 0x28, 2)[:] = struct.pack('<H', 4)       # (2,4) is the third cell
        self.assertEqual(np_.select_pose_tester(mem, DISP, SA, SB), 0)
        mem.view(SA + 0x28, 2)[:] = struct.pack('<H', 0x8001)  # kind 1 row is null
        self.assertEqual(np_.select_pose_tester(mem, DISP, SA, SB), 0)

    def test_select_has_no_bound(self):
        mem = PoseFlatMemory({DISP: bytearray(0x208), SA: bytearray(0x48), SB: bytearray(0x48)})
        mem.view(SA + 0x28, 2)[:] = struct.pack('<H', 8)
        with self.assertRaises(KeyError):                       # reads past the 0x208-byte object
            np_.select_pose_tester(mem, DISP, SA, SB)


class SphereSphereTests(unittest.TestCase):
    def test_overlap_produces_one_record(self):
        mem = build((0, 0, 0), (1.5, 0, 0), 1.0, 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 1)
        r = record(mem)
        n, depth, pa, pb = unf(r[0:3]), unf([r[3]])[0], unf(r[4:7]), unf(r[8:11])
        self.assertEqual(n, [1.0, 0.0, 0.0])
        self.assertAlmostEqual(depth, -0.5, places=6)
        self.assertEqual(pa, [1.0, 0.0, 0.0])
        self.assertEqual(pb, [0.5, 0.0, 0.0])
        self.assertEqual(r[7], 0)
        self.assertEqual(r[11], 0xFFFF0000)
        self.assertEqual(bytes(mem.view(OUT + 0x30, 0x30)), b'\xaa' * 0x30)

    def test_separated_writes_nothing(self):
        mem = build((0, 0, 0), (2.5, 0, 0), 1.0, 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 0)
        self.assertEqual(bytes(mem.view(OUT, 0x60)), b'\xaa' * 0x60)

    def test_exact_touch_is_a_contact_with_zero_depth(self):
        mem = build((0, 0, 0), (0, 0, 2.0), 1.0, 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 1)
        r = record(mem)
        self.assertEqual(r[3], 0)                       # minps(0, 0) keeps +0
        self.assertEqual(unf(r[0:3]), [0.0, 0.0, 1.0])

    def test_coincident_centres_use_fallback_normal(self):
        mem = build((3, 4, 5), (3, 4, 5), 1.0, 2.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 1)
        r = record(mem)
        self.assertEqual(r[0:3], np_.FALLBACK_NORMAL[:3])
        self.assertEqual(unf(r[4:7]), [3.0, 4.0, 5.0])
        self.assertEqual(unf(r[8:11]), [3.0, 4.0, 5.0])
        self.assertEqual(unf([r[3]])[0], -3.0)

    def test_epsilon_is_strict(self):
        eps = struct.unpack('<f', struct.pack('<I', np_._mul(f(2.0), np_.SPHERE_EPSILON_BITS, 'sse')))[0]
        mem = build((0, 0, 0), (eps, 0, 0), 1.0, 1.0)
        np_.sphere_sphere_tester(mem, GEOM, OUT)
        self.assertEqual(record(mem)[0:3], np_.FALLBACK_NORMAL[:3])     # dist == eps: fallback
        mem = build((0, 0, 0), (eps * 2, 0, 0), 1.0, 1.0)
        np_.sphere_sphere_tester(mem, GEOM, OUT)
        self.assertEqual(unf(record(mem)[0:3]), [1.0, 0.0, 0.0])

    def test_capacity_is_ignored(self):
        mem = build((0, 0, 0), (1.0, 0, 0), 1.0, 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT, 0), 1)

    def test_nan_radius_rejects(self):
        mem = build((0, 0, 0), (0.5, 0, 0), float('nan'), 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 0)

    def test_infinite_radius_uses_fallback_and_negative_infinite_depth(self):
        mem = build((0, 0, 0), (1.0, 0, 0), float('inf'), 1.0)
        self.assertEqual(np_.sphere_sphere_tester(mem, GEOM, OUT), 1)
        r = record(mem)
        self.assertEqual(r[0:3], np_.FALLBACK_NORMAL[:3])               # eps = inf, never < dist
        self.assertEqual(r[3], 0xFF800000)                              # minps(1 - inf, 0) = -inf
        self.assertEqual(unf(r[4:7]), [0.0, 0.0, 0.0])

    def test_nan_depth_lane_becomes_zero(self):
        # inf - inf is NaN; minps returns its second operand (0) for a NaN first operand.
        dist = np_._sqrt(0x7F800000)
        self.assertEqual(np_._minps(np_._sub(dist, 0x7F800000, 'sse'), 0), 0)

    def test_null_shape_raises(self):
        mem = build((0, 0, 0), (1.0, 0, 0), 1.0, 1.0)
        mem.view(GEOM + 0x80, 8)[:] = bytes(8)
        with self.assertRaises(ValueError):
            np_.sphere_sphere_tester(mem, GEOM, OUT)


if __name__ == '__main__':
    unittest.main()
