import math
import struct
import unittest
from types import SimpleNamespace

from engine.pose_pair_link_worker import PoseFlatMemory
from engine import pose_narrowphase_slot8 as mod
from engine.pose_narrowphase_dispatch import TESTER_TABLE, table_cell_offset
from engine.pose_flagged_neighbor_create import create_pose_flagged_neighbor
from engine.pose_flagged_neighbor_update import update_pose_flagged_neighbor

# Authored synthetic layout and fixtures (not game data). Shape objects carry the image
# vtable addresses only as identifiers; no image is loaded.
B = mod.IMAGE_BASE
GEOM, TESTER, SA, SB, VA, VB = 0x1000, 0x1800, 0x2000, 0x2200, 0x3000, 0x3400
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
VT = {'sphere': 0x29C9BE8, 'box': 0x29C9AC8, 'capsule': 0x29C9B58, 'hull': 0x29C9D80}
KIND = {'sphere': 2, 'box': 3, 'capsule': 4, 'hull': 5}


def bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def frame(t, rows=IDENT, lane3=0):
    return b''.join(struct.pack('<3fI', *v, lane3) for v in list(rows) + [t])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, s, 0), (-s, c, 0), (0, 0, 1))


def shape(kind, *values, verts=None, at=None, centre=(0, 0, 0)):
    raw = bytearray(0x110)
    struct.pack_into('<QH', raw, 0, B + VT[kind], 0)
    struct.pack_into('<H', raw, 0x28, 0x8000 | KIND[kind])
    if kind == 'hull':
        struct.pack_into('<QI', raw, 0x40, at, len(verts) + 1)
        struct.pack_into('<3f', raw, 0x64, *centre)
    else:
        struct.pack_into('<%df' % len(values), raw, 0x40, *values)
    return raw


def box_verts(e):
    return [(sx * e[0], sy * e[1], sz * e[2]) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def run(cell, sa, sb, ta, tb, rows_a=IDENT, rows_b=IDENT, extra=None, lane3=0, **kw):
    regions = {GEOM: bytearray(frame(ta, rows_a, lane3) + frame(tb, rows_b, lane3) + struct.pack('<QQ', SA, SB)),
               TESTER: bytearray(struct.pack('<Q', B + TESTER_TABLE[cell][0])),
               SA: sa, SB: sb}
    regions.update(extra or {})
    mem = PoseFlatMemory(regions)
    return mod.pose_tester_overlap(mem, TESTER, GEOM, **kw)


def hull_regions(verts, at):
    raw = bytearray(12 * (len(verts) + 1))
    for i, v in enumerate(verts):
        struct.pack_into('<3f', raw, 12 * i, *v)
    return {at: raw}


class SlotTable(unittest.TestCase):
    def test_every_cell_has_slots_and_a_vtable(self):
        self.assertEqual(set(mod.SLOT_TABLE), set(TESTER_TABLE))
        self.assertEqual(len(mod.SLOT_TABLE), 32)

    def test_non_terrain_cells_share_forwarders(self):
        for cell, (s1, s2, s4, fwd) in mod.SLOT_TABLE.items():
            terrain = 6 in cell or 7 in cell
            if not terrain and fwd is None:
                self.assertEqual((s2, s4), (mod.SHARED_SLOT2_RVA, mod.SHARED_SLOT4_RVA), cell)

    def test_swapped_cells_point_at_their_mirror(self):
        for cell, (_s1, _s2, _s4, fwd) in mod.SLOT_TABLE.items():
            if fwd is not None:
                self.assertEqual(fwd, (cell[1], cell[0]))
                self.assertIsNone(mod.SLOT_TABLE[fwd][3])

    def test_portal_body_groups(self):
        portal = sorted(c for c in mod.SLOT_TABLE if mod.slot8_body(c)[0] == mod.PORTAL_RVA)
        self.assertEqual(portal, [(2, 5), (3, 4), (3, 5), (4, 3), (4, 5), (5, 2), (5, 3), (5, 4), (5, 5)])

    def test_terrain_cells_raise(self):
        sa = shape('sphere', 1.0)
        with self.assertRaises(mod.TerrainSlot8Unavailable):
            run((2, 6), sa, sa, (0, 0, 0), (0, 0, 0))
        self.assertEqual(len(mod.TERRAIN_SLOT8), 8)


class Primitives(unittest.TestCase):
    def test_sphere_sphere_touch_is_overlap(self):
        a, b = shape('sphere', 1.0), shape('sphere', 0.5)
        self.assertEqual(run((2, 2), a, b, (0, 0, 0), (1.5, 0, 0)), 1)
        self.assertEqual(run((2, 2), a, b, (0, 0, 0), (1.5000002, 0, 0)), 0)

    def test_sphere_sphere_nan_radius_misses(self):
        a = shape('sphere', float('nan'))
        self.assertEqual(run((2, 2), a, shape('sphere', 1.0), (0, 0, 0), (0, 0, 0)), 0)

    def test_sphere_box_uses_clamped_excess(self):
        a, b = shape('sphere', 0.5), shape('box', 1.0, 2.0, 3.0)
        self.assertEqual(run((2, 3), a, b, (1.4, 0, 0), (0, 0, 0)), 1)
        self.assertEqual(run((2, 3), a, b, (1.6, 0, 0), (0, 0, 0)), 0)
        self.assertEqual(run((2, 3), a, b, (0.3, 1.0, -2.0), (0, 0, 0)), 1)      # inside: excess 0
        # corner: excess (0.4, 0.4, 0) -> 0.32 > 0.25
        self.assertEqual(run((2, 3), a, b, (1.4, 2.4, 0), (0, 0, 0)), 0)

    def test_box_sphere_swap_matches_forward(self):
        a, b = shape('sphere', 0.5), shape('box', 1.0, 2.0, 3.0)
        for t in ((1.4, 0, 0), (1.6, 0, 0), (1.3, 2.3, 0)):
            self.assertEqual(run((3, 2), b, a, (0, 0, 0), t), run((2, 3), a, b, t, (0, 0, 0)))

    def test_sphere_capsule_axis_and_cap(self):
        s, c = shape('sphere', 0.25), shape('capsule', 1.0, 0.5)
        self.assertEqual(run((2, 4), s, c, (0.7, 0.9, 0), (0, 0, 0)), 1)
        self.assertEqual(run((2, 4), s, c, (0.8, 0.0, 0), (0, 0, 0)), 0)
        self.assertEqual(run((2, 4), s, c, (0, 1.74, 0), (0, 0, 0)), 1)
        self.assertEqual(run((2, 4), s, c, (0, 1.76, 0), (0, 0, 0)), 0)

    def test_capsule_capsule_crossing_and_parallel(self):
        a, b = shape('capsule', 1.0, 0.25), shape('capsule', 1.0, 0.25)
        cross = rot_z(math.pi / 2)
        self.assertEqual(run((4, 4), a, b, (0, 0, 0), (0, 0, 0.49), rows_b=cross), 1)
        self.assertEqual(run((4, 4), a, b, (0, 0, 0), (0, 0, 0.51), rows_b=cross), 0)
        trace = []
        self.assertEqual(run((4, 4), a, b, (0, 0, 0), (0.45, 0.5, 0), trace=trace), 1)
        self.assertIn('parallel', trace)

    def test_capsule_capsule_zero_length_parallel_nan(self):
        # hB = 0 gives e = 0; parallel sD = e, so f == 0 reaches 0/0 and the test fails
        a, b = shape('capsule', 1.0, 0.25), shape('capsule', 0.0, 0.25)
        self.assertEqual(run((4, 4), a, b, (0, 0, 0), (0.1, 0, 0)), 0)

    def test_box_box_face_and_edge_axes(self):
        a, b = shape('box', 1, 1, 1), shape('box', 1, 1, 1)
        self.assertEqual(run((3, 3), a, b, (0, 0, 0), (1.99, 0, 0)), 1)
        self.assertEqual(run((3, 3), a, b, (0, 0, 0), (2.01, 0, 0)), 0)
        r = rot_z(math.pi / 4)
        trace = []
        self.assertEqual(run((3, 3), a, b, (0, 0, 0), (2.3, 0, 0), rows_b=r, trace=trace), 1)
        self.assertEqual(run((3, 3), a, b, (0, 0, 0), (2.5, 0, 0), rows_b=r), 0)

    def test_fourth_lane_junk_is_masked(self):
        a, b = shape('box', 1, 1, 1), shape('box', 1, 1, 1)
        for cell in ((3, 3), (3, 4)):
            other = shape('capsule', 0.5, 0.25) if cell == (3, 4) else b
            self.assertEqual(run(cell, a, other, (0, 0, 0), (1.5, 0, 0), lane3=0x7FC00000),
                             run(cell, a, other, (0, 0, 0), (1.5, 0, 0)))


class Portal(unittest.TestCase):
    def test_box_capsule_separation_and_overlap(self):
        box, cap = shape('box', 1, 1, 1), shape('capsule', 1.0, 0.25)
        self.assertEqual(run((3, 4), box, cap, (0, 0, 0), (1.2, 0, 0)), 1)
        self.assertEqual(run((3, 4), box, cap, (0, 0, 0), (1.3, 0, 0)), 0)
        self.assertEqual(run((3, 4), box, cap, (0, 0, 0), (0, 2.2, 0)), 1)
        self.assertEqual(run((3, 4), box, cap, (0, 0, 0), (0, 2.3, 0)), 0)

    def test_capsule_box_is_the_swapped_box_capsule(self):
        box, cap = shape('box', 1, 1, 1), shape('capsule', 1.0, 0.25)
        for t in ((1.2, 0, 0), (1.3, 0, 0), (0.9, 1.9, 0.3), (0, 2.3, 0)):
            self.assertEqual(run((4, 3), cap, box, t, (0, 0, 0)), run((3, 4), box, cap, (0, 0, 0), t))

    def test_coincident_centres_hit_without_support(self):
        trace = []
        hull = shape('hull', verts=box_verts((1, 1, 1)), at=VB)
        self.assertEqual(run((5, 5), hull, shape('hull', verts=box_verts((1, 1, 1)), at=VB), (3, 3, 3), (3, 3, 3),
                             extra=hull_regions(box_verts((1, 1, 1)), VB), trace=trace), 1)
        self.assertEqual(trace, ['centres_coincide'])

    def test_hull_matches_box_support(self):
        e = (0.5, 1.0, 1.5)
        hull = shape('hull', verts=box_verts(e), at=VB)
        box = shape('box', *e)
        extra = hull_regions(box_verts(e), VB)
        sph = shape('sphere', 0.5)
        for t in ((0.9, 0, 0), (1.1, 0, 0), (0.7, 1.3, 1.8), (0, 0, 2.05)):
            self.assertEqual(run((2, 5), sph, hull, t, (0, 0, 0), extra=extra),
                             run((2, 3), sph, box, t, (0, 0, 0)), t)

    def test_hull_centre_offset_is_read(self):
        e = (1, 1, 1)
        verts = box_verts(e)
        hull = shape('hull', verts=verts, at=VB, centre=(0.25, 0, 0))
        mem = PoseFlatMemory({SB: hull})
        self.assertEqual(mod.shape_centre(mem, SB), [bits(0.25), 0, 0, 0])

    def test_nan_frame_never_terminates(self):
        box, cap = shape('box', 1, 1, 1), shape('capsule', 1.0, 0.25)
        with self.assertRaises(mod.PortalIterationLimit):
            run((3, 4), box, cap, (0, 0, 0), (float('nan'), 0.5, 0), max_iterations=64)

    def test_support_functions(self):
        mem = PoseFlatMemory({SA: shape('sphere', 2.0), SB: shape('capsule', 1.0, 0.5),
                              0x2400: shape('box', 1, 2, 3)})
        self.assertEqual(mod.shape_support(mem, SA, [bits(3), bits(4), 0, 0]),
                         [bits(1.2), bits(1.6), 0, 0])
        self.assertEqual(mod.shape_support(mem, SA, [0, 0, 0, 0]), [bits(2.0), 0, 0, 0])
        self.assertEqual(mod.shape_support(mem, SB, [0, bits(-1.0), 0, 0])[:3], [0, bits(-1.5), 0])
        self.assertEqual(mod.shape_support(mem, 0x2400, [bits(-1.0), 0x80000000, 0, 0])[:3],
                         [bits(-1.0), bits(2.0), bits(3.0)])


class FlaggedAdapter(unittest.TestCase):
    def _world(self, rows, t):
        return [x for r in rows for x in r] + list(t)

    def test_update_and_create_forms_agree(self):
        disp = 0x9000
        raw = bytearray(0x208)
        regions = {disp: raw, SA: shape('box', 1, 1, 1), SB: shape('capsule', 1.0, 0.25)}
        for i, cell in enumerate(sorted(TESTER_TABLE)):
            obj = 0xA000 + 0x10 * i
            regions[obj] = bytearray(struct.pack('<Q', B + TESTER_TABLE[cell][0]))
            struct.pack_into('<Q', raw, table_cell_offset(*cell), obj)
        mem = PoseFlatMemory(regions)
        log = []
        svc = mod.bind_pose_flagged_tester_services(mem, log=log)
        tester = svc.select_tester(disp, SB, SA)
        self.assertEqual(mod.tester_cell(mem, tester), (4, 3))
        for t in ((1.2, 0, 0), (1.3, 0, 0)):
            u = svc.test_update(tester, self._world(IDENT, t), self._world(IDENT, (0, 0, 0)), SB, SA)
            c = svc.test_create(tester, ((IDENT, t), (IDENT, (0, 0, 0)), SB, SA))
            self.assertEqual(u, c)
        self.assertEqual([r for _t, _c, r in log], [1, 1, 0, 0])

    def test_binds_into_create_pose_flagged_neighbor(self):
        mem, owner, pair = _flagged_fixture()
        svc = mod.bind_pose_flagged_tester_services(mem)
        services = SimpleNamespace(select_collider=svc.select_collider, test_overlap=svc.test_create,
                                   allocator=_Alloc(mem), next_serial=lambda: 7)
        record = create_pose_flagged_neighbor(mem, owner, pair, services)
        self.assertTrue(record)
        self.assertEqual(mem.d(record + 0x50), 1)                  # only (0, 0) overlaps
        self.assertEqual(mem.d(mem.q(record + 0x48)), 0)

    def test_binds_into_update_pose_flagged_neighbor(self):
        mem, owner, pair = _flagged_fixture()
        svc = mod.bind_pose_flagged_tester_services(mem)
        record = 0x60000
        mem.add(record, bytearray(0x80))
        mem.set_q(record + 0x48, 0x61000)
        mem.add(0x61000, bytearray(struct.pack('<HH', 1, 0) + bytes(12)))
        mem.set_d(record + 0x50, 1)
        mem.set_d(record + 0x54, 4)
        nodes = mem.q(mem.q(owner) + 0x38)
        mem.set_q(nodes + 0x10, record)
        services = SimpleNamespace(select_tester=svc.select_tester, test_overlap=svc.test_update,
                                   allocator=_Alloc(mem))
        update_pose_flagged_neighbor(mem, owner, pair, 0, services)
        self.assertEqual(mem.d(record + 0x50), 1)
        self.assertEqual(struct.unpack('<HH', bytes(mem.view(0x61000, 4))), (0, 0))   # (1,0) out, (0,0) in
        self.assertEqual(mem.d(record + 0x58), 2)


class _Alloc:
    def __init__(self, mem):
        self.mem, self.heap = mem, 0x80000

    def allocate(self, n, align, tag):
        p = self.heap
        self.heap += (n + 0x1F) & ~0xF
        self.mem.add(p, bytearray(n))
        return p

    def reallocate(self, old, n, align, tag):
        p = self.allocate(n, align, tag)
        return p

    def release(self, p):
        pass


def _flagged_fixture():
    """Two bodies; A has one box and one far box, B one capsule (all authored)."""
    P, O, PAIR, NODES, DISP = 0x40000, 0x41000, 0x42000, 0x43000, 0x44000
    mem = PoseFlatMemory()
    raw = bytearray(0x208)
    for i, cell in enumerate(sorted(TESTER_TABLE)):
        obj = 0x45000 + 0x10 * i
        mem.add(obj, bytearray(struct.pack('<Q', B + TESTER_TABLE[cell][0])))
        struct.pack_into('<Q', raw, table_cell_offset(*cell), obj)
    mem.add(DISP, raw)
    filt = 0x46000
    mem.add(filt, bytearray(0x60))
    mem.set_q(filt + 0x48, 1)
    mem.set_q(filt + 0x50, 1)
    shapes = [0x47000, 0x47200, 0x47400]
    for at, sh in zip(shapes, (shape('box', 1, 1, 1), shape('box', 1, 1, 1), shape('capsule', 1.0, 0.25))):
        struct.pack_into('<Q', sh, 0x20, filt)
        mem.add(at, sh)
    locals_ = [0x48000, 0x48100, 0x48200]
    for at, t in zip(locals_, ((0, 0, 0), (10, 0, 0), (0, 0, 0))):
        mem.add(at, bytearray(frame(t)))
    kind = 0x49000
    mem.add(kind, bytearray(0x60))
    mem.set_q(kind + 0x20, 0x111)
    for bi, (n, t) in enumerate(((2, (0, 0, 0)), (1, (1.2, 0, 0)))):
        body = 0x4A000 + 0x100 * bi
        mem.add(body, bytearray(0x100))
        mem.view(body + 0x40, 0x40)[:] = frame(t)
        mem.set_q(body + 0x30, kind)
        mem.set_q(body + 0xB8, 0x4B000 + 0x1000 * bi)
        mem.put('<H', body + 0xC0, n)
        ea = bytearray(n * 0x48)
        for j in range(n):
            k = j if bi == 0 else 2
            struct.pack_into('<QQ', ea, j * 0x48 + 0x10, shapes[k], locals_[k])
            struct.pack_into('<QQII', ea, j * 0x48 + 0x28, 1, 1, 1, 1)
            ea[j * 0x48 + 0x44] = 0x0C
        mem.add(0x4B000 + 0x1000 * bi, ea)
    mem.add(NODES, bytearray(32))
    prov = bytearray(0x200)
    struct.pack_into('<Q', prov, 0x38, NODES)
    struct.pack_into('<Q', prov, 0x68, DISP)
    mem.add(P, prov)
    own = bytearray(0x80)
    struct.pack_into('<Q', own, 0, P)
    mem.add(O, own)
    mem.add(PAIR, bytearray(struct.pack('<QQQ', 0x4A000, 0x4A100, 5)))
    return mem, O, PAIR


if __name__ == '__main__':
    unittest.main()
