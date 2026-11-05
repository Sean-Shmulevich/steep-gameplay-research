"""Kind-3 (box) narrow-phase testers (3,3), (3,4), (3,5): entry wrappers, the box-box and
box-hull cores, and the shared clip / reduce drivers that bound their record counts.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase box testers" (this work) and "Narrow-phase tester table and sphere-sphere tester" (tester table, geom block,
record layout). Static reads of the routines named below; native comparison in
analysis/command-executor-audit/check_pose_narrowphase_kind3.py.

Kinds (from the fields the routines read):
- 3 box: half extents x, y, z at shape+0x40/+0x44/+0x48 (agrees with the box layout of
  engine.pose_grid_box_contact / pose_box_resource_bounds).
- 4 capsule: half-height at shape+0x40, radius at shape+0x44, segment along local Y from
  (0,-h,0) to (0,+h,0) (box-capsule core 0x19d9160 and sphere-capsule core 0x19d53b0).
- 5 convex polyhedron: shape+0x100 points at a hull descriptor in the same layout that
  0x19db710 builds for the box (HULL_* constants below), passed to the generic
  polyhedron SAT 0x190f700.

Recovered behaviour restated here (register-level, over flat memory):

- 0x19d8cd0 (3,3) and 0x19dbba0 (3,5) are thunks: core(geom, out, capacity).
- 0x19db670 (3,4) masks and copies both frames to its stack and calls
  0x19d9160(shapeA, &frameA, shapeB, &frameB, out, capacity).
- 0x19d9160 box-capsule core (never reads capacity): axis points p0/p1 = frameB applied
  to (0,-h,0)/(0,+h,0); segment-box distance 0x18eab80. If dist > 2^-23 (lanes 0..2):
  n = normalised (P_axis - P_box); face = 0x19db080(frame, n); plane = 0x19da3f0; if
  0.997 < |plane.n . n| the four box side planes 0x19da100 clip the segment (unrolled,
  two points with tags 0x80000000|face and 0x81000000|face; any pass leaving fewer than
  two points falls through) and each surviving point with s = n.p - d <= r gives one
  record (at most 2). Otherwise (or after a failed clip) one record if dist - r <= 0
  (all four lanes). If dist <= 2^-23: the box becomes the 0x19db710 hull and the
  capsule-hull selector 0x19daf90 picks 0x19daa60 (kind 0, at most 2 records) or
  0x19da4e0 (kind 2, at most 1); any other kind returns 0.
- 0x19d6900 box-box core: SAT 0x19d8550 (true = separated -> 0); if geom+0x91 is set the
  edge query 0x19d7540 may produce one record (feature 0xff, written without a
  capacity check); otherwise face clipping: 0x19d6200 (side planes), 0x19d5d30
  (incident polygon), clip driver 0x1996bf0 (rdx 8 into an 8-point buffer, 4 planes;
  the per-plane clip 0x19980f0 never reads rdx, so 8 is not enforced), reduce driver
  0x19984f0 (flag geom+0x90), then an emission loop that stops when the record count
  reaches `capacity` and keeps only points with depth < 0.
- 0x19db710 box-hull core: builds the box as an 8-vertex/6-face/12-edge hull on its
  stack (edge table is a function-local magic static at 0x143336930), runs the SAT
  0x190f700, then dispatches: 0 -> face contact 0x18e4060 (box face reference),
  1 -> 0x18e4060 with the roles swapped and flip=1, 2 -> edge contact 0x18e3aa0,
  anything else -> 0.
- 0x18e4060 face contact: reference plane to world, incident face = minimum dot of the
  incident hull's face normals with the reference normal (strictly smaller replaces,
  first index wins ties), polygon 0x18e3980, side planes 0x18e3450, clip driver
  0x1996bf0 (rdx 0x80, unread), reduce driver 0x19984f0, then an emission loop that stops
  at `capacity` and emits every surviving point (no depth sign test, feature 0).
- 0x1996bf0 clip driver: clips through the planes with 0x19980f0 (ping-pong buffers of
  0x80 points); any pass with fewer than 3 points returns 0. The last pass writes the
  caller's buffer with the caller's output cap. The last plane used is
  max(1, nplanes - 1) (nplanes 1 reuses plane index 1). 0x19980f0 (supplied) ignores
  its rdx capacity: each pass can emit up to two points per input point.
- 0x19984f0 reduce driver: n = 0x19986e0(...), n = 0x1998e80(depths, points, n, 1e-4);
  if flag and n > 4 (signed), 0x19989d0 picks 4 indices and points/depths 0..3 are
  gathered (all four loaded before any store) and 4 is returned.

Supplied services (called through `services(rva, mem, rcx, rdx, r8, r9, xmm3=None)`,
returning rax; stack arguments are in memory at the native addresses): 0x19d8550,
0x19d7540, 0x19d6200, 0x19d5d30, 0x19980f0, 0x19986e0, 0x1998e80, 0x19989d0, 0x190f700,
0x18e3aa0, 0x18e3980, 0x18e3450, and the box-capsule leaves 0x18eab80, 0x19db080,
0x19da3f0, 0x19da100, 0x19daf90, 0x19daa60, 0x19da4e0. The CRT
services of the native code (__chkstk 0x1c45120, _Init_thread_header/footer
0x1c44fb0/0x1c44f50) have no counterpart: the model writes the constant edge table each
call instead of running the once-only guard.

Authored choices: the model lays out its locals and stack arguments at the native stack
offsets below `sp` (the rsp at the tester entry, pointing at the return address) so the
supplied services receive the same addresses; saved registers, return addresses and
xmm spills are not written. Float lanes follow engine.pose_contact_payload_update
(exact double then one float32 rounding, no FTZ/DAZ, nan_rule 'sse' or 'x87').
"""
import struct

from engine.pose_contact_payload_update import XYZ_MASK, _add, _mul, _sub
from engine.pose_narrowphase_dispatch import _div, _le, _lt, _sqrt

IMAGE_BASE = 0x140000000
MASK_VA = IMAGE_BASE + 0x3336890
SIGN_MASK = 0x80000000                       # 16-byte constant at RVA 0x1df3310
REDUCE_THRESHOLD_BITS = 0x38D1B717           # float32 at RVA 0x1df404c (1e-4)
BOX_EDGE_TABLE_VA = IMAGE_BASE + 0x3336930   # magic static of 0x19db710
BOX_EDGE_GUARD_VA = IMAGE_BASE + 0x3336990
BOX_FACE_INDEX_VA = IMAGE_BASE + 0x29CA810   # .rdata u16[24]
RECORD_STRIDE = 0x30
RECORD_TAIL = 0xFFFF0000
EDGE_FEATURE = 0xFF

# Entry / core / helper RVAs.
BOX_BOX_ENTRY_RVA, BOX_BOX_CORE_RVA = 0x19D8CD0, 0x19D6900
BOX_CAPSULE_ENTRY_RVA, BOX_CAPSULE_CORE_RVA = 0x19DB670, 0x19D9160
BOX_HULL_ENTRY_RVA, BOX_HULL_CORE_RVA = 0x19DBBA0, 0x19DB710
FACE_CONTACT_RVA = 0x18E4060
CLIP_DRIVER_RVA = 0x1996BF0
REDUCE_DRIVER_RVA = 0x19984F0
# Supplied leaves.
BOX_SAT_RVA, BOX_EDGE_RVA, BOX_PLANES_RVA, BOX_POLYGON_RVA = 0x19D8550, 0x19D7540, 0x19D6200, 0x19D5D30
CLIP_PLANE_RVA = 0x19980F0
DEPTHS_RVA, PRUNE_RVA, PICK4_RVA = 0x19986E0, 0x1998E80, 0x19989D0
HULL_SAT_RVA, HULL_EDGE_RVA, HULL_POLYGON_RVA, HULL_PLANES_RVA = 0x190F700, 0x18E3AA0, 0x18E3980, 0x18E3450
SUPPLIED_RVAS = (BOX_SAT_RVA, BOX_EDGE_RVA, BOX_PLANES_RVA, BOX_POLYGON_RVA, CLIP_PLANE_RVA,
                 DEPTHS_RVA, PRUNE_RVA, PICK4_RVA, HULL_SAT_RVA, HULL_EDGE_RVA,
                 HULL_POLYGON_RVA, HULL_PLANES_RVA,
                 0x18EAB80, 0x19DB080, 0x19DA3F0, 0x19DA100, 0x19DAF90, 0x19DAA60, 0x19DA4E0)

# Hull descriptor (0x26 bytes used): +0 vertices (f32 x,y,z), +8 faces (0x14 bytes:
# plane n.xyz, d, u16 corner count, u16 first corner), +0x10 edges (u16 v0, v1, f0, f1),
# +0x18 face corner list (u16 vertex), +0x20 u16 vertex count, +0x22 u16 face count,
# +0x24 u16 edge count. Values as 0x19db710 stores them for a box.
BOX_EDGES = ((4, 0, 3, 0), (5, 1, 0, 1), (6, 2, 1, 2), (7, 3, 2, 3), (4, 5, 0, 5), (5, 6, 1, 5),
             (6, 7, 2, 5), (7, 4, 3, 5), (0, 1, 0, 4), (1, 2, 1, 4), (2, 3, 2, 4), (3, 0, 3, 4))
BOX_FACE_CORNERS = (0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7, 2, 1, 0, 3, 7, 4, 5, 6)
# (normal lane bits, extent index for d); first corner = 4*face, corner count 4.
_ONE, _NEG_ONE = 0x3F800000, 0xBF800000
BOX_FACES = (((_ONE, 0, 0), 0), ((0, 0, _NEG_ONE), 2), ((_NEG_ONE, 0, 0), 0),
             ((0, 0, _ONE), 2), ((0, _NEG_ONE, 0), 1), ((0, _ONE, 0), 1))
# Vertex sign pattern (+1 keeps the extent, -1 flips its sign bit).
BOX_VERTEX_SIGNS = ((1, -1, 1), (1, -1, -1), (-1, -1, -1), (-1, -1, 1),
                    (1, 1, 1), (1, 1, -1), (-1, 1, -1), (-1, 1, 1))


# --- small helpers -------------------------------------------------------------------

def _lanes(mem, address):
    return list(struct.unpack('<4I', bytes(mem.view(address, 16))))


def _and(v, m):
    return [a & b for a, b in zip(v, m)]


def _put_lanes(mem, address, lanes):
    mem.view(address, 4 * len(lanes))[:] = struct.pack('<%dI' % len(lanes), *lanes)


def _mask(mem, mask):
    return struct.unpack('<4I', mask)


def _hadd2(v, rule):
    """haddps v,v twice: (v0 + v1) + (v2 + v3)."""
    return _add(_add(v[0], v[1], rule), _add(v[2], v[3], rule), rule)


def _write_record(mem, rec, normal, depth, first, second, feature):
    """movss lane stores of one 0x30-byte record (normal, depth, point 1, feature, point 2,
    tail). Lanes +0x1c and +0x2c are the dword stores."""
    _put_lanes(mem, rec, normal[:3])
    mem.set_d(rec + 0x0C, depth)
    _put_lanes(mem, rec + 0x10, first[:3])
    _put_lanes(mem, rec + 0x20, second[:3])
    mem.set_d(rec + 0x2C, RECORD_TAIL)
    mem.set_d(rec + 0x1C, feature)


def _emit(mem, out, count, normal, depth, point, feature, flip, rule):
    """Shared record body of 0x19d6900 and 0x18e4060: t = p - n*d; flip negates the
    normal and puts p first, otherwise t is first."""
    nd = [_mul(n, depth, rule) for n in normal]
    t = [_sub(p, x, rule) for p, x in zip(point, nd)]
    rec = out + RECORD_STRIDE * count
    if flip:
        _write_record(mem, rec, [n ^ SIGN_MASK for n in normal], depth, point, t, feature)
    else:
        _write_record(mem, rec, normal, depth, t, point, feature)


def _call(services, mem, rsp, rva, rcx, rdx, r8, r9, stack=(), xmm3=None):
    """Store stack arguments (offset from rsp, struct format, value) then call a service."""
    for off, fmt, value in stack:
        mem.put(fmt, rsp + off, value)
    return services(rva, mem, rcx & 0xFFFFFFFFFFFFFFFF, rdx & 0xFFFFFFFFFFFFFFFF,
                    r8 & 0xFFFFFFFFFFFFFFFF, r9 & 0xFFFFFFFFFFFFFFFF, xmm3) & 0xFFFFFFFFFFFFFFFF


def _i32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


# --- shared drivers --------------------------------------------------------------------

def clip_polygon(mem, services, sp, poly, count, out_cap, planes, nplanes):
    """0x1996bf0(poly, count, out_cap, planes, nplanes); sp = entry rsp. Returns rax.

    nplanes is read as a signed dword from the stack slot sp+0x28 by the native code; the
    model takes it as an argument and also stores it there (callers already did).
    """
    rsp = sp - 0x18 - 0x1030
    buf_a, buf_b = rsp + 0x30, rsp + 0x830
    plane = planes
    n = _call(services, mem, rsp, CLIP_PLANE_RVA, buf_a, 0x80, poly, count & 0xFFFFFFFF,
              [(0x20, '<Q', plane)]) & 0xFFFFFFFF
    plane += 0x10
    if _i32(n) < 3:
        return 0
    cur, other = buf_a, buf_b
    last = _i32(nplanes) - 1
    k = 1
    if last > k:
        while True:
            n = _call(services, mem, rsp, CLIP_PLANE_RVA, other, 0x80, cur, n,
                      [(0x20, '<Q', plane)]) & 0xFFFFFFFF
            plane += 0x10
            if _i32(n) < 3:
                return 0
            cur, other = other, cur
            k += 1
            if k >= last:
                break
    n = _call(services, mem, rsp, CLIP_PLANE_RVA, poly, out_cap & 0xFFFFFFFF, cur, n,
              [(0x20, '<Q', plane)])
    return 0 if _i32(n) < 3 else n & 0xFFFFFFFF


def reduce_contacts(mem, services, sp, depths, points, r8, plane, flag):
    """0x19984f0(depths, points, count, plane, flag); r8 is the full register the caller
    passed (count zero-extended). Returns rax."""
    rsp = sp - 0x08 - 0xA0
    n = _call(services, mem, rsp, DEPTHS_RVA, depths, points, r8, plane)
    n = _call(services, mem, rsp, PRUNE_RVA, depths, points, n & 0xFFFFFFFF, 0,
              xmm3=REDUCE_THRESHOLD_BITS)
    if not (flag & 0xFF) or _i32(n) <= 4:
        return n
    mem.set_d(sp + 0x28, n)                       # count stored over the flag slot
    _call(services, mem, rsp, PICK4_RVA, rsp + 0x30, points, sp + 0x28, 0x10,
          [(0x20, '<Q', plane)])
    idx = [mem.d(rsp + 0x30 + 4 * k) for k in range(4)]
    picked = [bytes(mem.view(points + 0x10 * i, 16)) for i in idx]
    picked_d = [mem.d(depths + 4 * i) for i in idx]
    for k in range(4):
        mem.view(points + 0x10 * k, 16)[:] = picked[k]
    for k in range(4):
        mem.set_d(depths + 4 * k, picked_d[k])
    return 4


# --- (3,3) box-box ---------------------------------------------------------------------

def box_box_core(mem, services, sp, geom, out, capacity, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d6900(geom, out, capacity); sp = entry rsp. Returns the record count."""
    m = _mask(mem, mask)
    rsp = sp - 0x28 - 0x420
    rbp = rsp + 0x100
    sat = rsp + 0x70
    shape_a, shape_b = mem.q(geom + 0x80), mem.q(geom + 0x88)
    half_b_ptr = shape_b + 0x40
    cap = capacity & 0xFFFFFFFF
    sep = _call(services, mem, rsp, BOX_SAT_RVA, sat, geom, shape_a + 0x40, geom + 0x40,
                [(0x20, '<Q', half_b_ptr)])
    if sep & 0xFF:
        return 0
    if mem.b(geom + 0x91) != 0:
        st = [(0x20, '<Q', half_b_ptr), (0x28, '<Q', rsp + 0x50), (0x30, '<Q', rsp + 0x60),
              (0x38, '<Q', rbp + 0x10), (0x40, '<Q', rbp + 0x20)]
        if not (_call(services, mem, rsp, BOX_EDGE_RVA, sat, geom, shape_a + 0x40, geom + 0x40, st) & 0xFF):
            n = _lanes(mem, rbp + 0x10)
            _write_record(mem, out, n, mem.d(rbp + 0x20), _lanes(mem, rsp + 0x50),
                          _lanes(mem, rsp + 0x60), EDGE_FEATURE)
            return 1                                  # no capacity check on this path
    for k in range(5):
        mem.set_d(rbp + 0xCC + 0x10 * k, 0)
    frame_a = [_and(_lanes(mem, geom + 0x10 * r), m) for r in range(4)]
    frame_b = [_and(_lanes(mem, geom + 0x40 + 0x10 * r), m) for r in range(4)]
    half_a = _and(_lanes(mem, shape_a + 0x40), m)
    half_b = _and(_lanes(mem, half_b_ptr), m)

    def store(fa_at, fb_at):
        for r in range(4):
            _put_lanes(mem, fa_at + 0x10 * r, frame_a[r])
            _put_lanes(mem, fb_at + 0x10 * r, frame_b[r])
        _put_lanes(mem, rsp + 0x50, half_a)
        _put_lanes(mem, rsp + 0x60, half_b)

    store(rbp - 0x30, rbp - 0x70)
    _call(services, mem, rsp, BOX_PLANES_RVA, rbp + 0xC0, sat, rbp - 0x30, rsp + 0x50,
          [(0x20, '<Q', rbp - 0x70), (0x28, '<Q', rsp + 0x60)])
    mem.set_d(rbp + 0xB0, 0)
    store(rbp - 0x70, rbp - 0x30)
    _call(services, mem, rsp, BOX_POLYGON_RVA, rbp + 0x30, sat, rbp - 0x70, rsp + 0x50,
          [(0x20, '<Q', rbp - 0x30), (0x28, '<Q', rsp + 0x60)])
    mem.set_d(rsp + 0x20, 4)
    n = clip_polygon(mem, services, rsp - 8, rbp + 0x30, mem.d(rbp + 0xB0), 8, rbp + 0xC0, 4)
    flag = mem.b(geom + 0x90)
    mem.set_b(rsp + 0x20, flag)
    count = reduce_contacts(mem, services, rsp - 8, rbp + 0x110, rbp + 0x30, n & 0xFFFFFFFF,
                            rbp + 0x100, flag) & 0xFFFFFFFF
    mem.set_d(rbp + 0xB0, count)
    flip = mem.b(sat + 0x11) > 2
    normal = _and(_lanes(mem, sat), m)
    written = 0
    for i in range(count):
        if written >= cap:
            break
        depth = mem.d(rbp + 0x110 + 4 * i)
        if not _lt(depth, 0):
            continue
        point = _and(_lanes(mem, rbp + 0x30 + 0x10 * i), m)
        feature = mem.d(rbp + 0x3C + 0x10 * i)
        _emit(mem, out, written, normal, depth, point, feature, flip, nan_rule)
        written += 1
    return written


def box_box_tester(mem, geom, out, capacity=500, *, services, sp, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d8cd0(tester, geom, out, capacity): thunk to 0x19d6900 (same rsp)."""
    return box_box_core(mem, services, sp, geom, out, capacity, mask=mask, nan_rule=nan_rule)


# --- (3,4) box-capsule -------------------------------------------------------------------

GJK_EPS = 0x34000000          # float32 lanes at RVA 0x1eeb1f0 (2^-23)
PARALLEL_COS = 0x3F7F3B64     # float32 lanes at RVA 0x29cc100 (0.997)
ABS_MASK = 0x7FFFFFFF         # 16-byte constant at RVA 0x291a450
ONE = 0x3F800000              # 16-byte constant at RVA 0x1e252f0
TAG_FIRST, TAG_SECOND = 0x80000000, 0x81000000
# Supplied leaves of 0x19d9160.
SEG_GJK_RVA = 0x18EAB80          # (out dist/P_box/P_seg, &{box frame, extents}, &points[2], 16)
BOX_FACE_PICK_RVA = 0x19DB080    # (box frame, &direction) -> face index
BOX_FACE_PLANE_RVA = 0x19DA3F0   # (out plane, box frame, box shape, face)
BOX_SIDE_PLANES_RVA = 0x19DA100  # (out 4 planes + count, box frame, box shape, face)
CAPSULE_HULL_SAT_RVA = 0x19DAF90  # (out sel, box frame, hull desc, &p0, &p1)
CAPSULE_FACE_RVA = 0x19DAA60     # selection kind 0
CAPSULE_EDGE_RVA = 0x19DA4E0     # selection kind 2


def _v(op, a, b, rule):
    return [op(x, y, rule) for x, y in zip(a, b)]


def _bc(x):
    return [x] * 4


def _all(pred, a, b, n):
    return all(pred(x, y) for x, y in list(zip(a, b))[:n])


def _mdot(a, b, m, rule):
    """(a*b) & M then haddps twice; a is the destination operand. Returns 4 equal lanes."""
    return _bc(_hadd2(_and(_v(_mul, a, b, rule), m), rule))


def _segment_clip_pass(points, plane, m, rule):
    """One unrolled plane of 0x19d9160 (passes at 19d93ca, 19d960f, 19d98c6, 19d9a1a).

    points: two (raw 4-lane bits incl. the tag word in lane 3). plane: raw 4 lanes
    (n.xyz, d). Keeps a point when dist <= 0 (all 4 lanes) with its raw xyz and tag,
    then appends the crossing when d1*d0 < 0 (lanes 0..2) with the tag of point 0 when
    0 < d0, else of point 1. Distances use the masked point, lane 3 (tag) included.
    """
    n = _and(plane, m)
    d = _bc(plane[3])
    q0, q1 = _and(points[0], m), _and(points[1], m)
    d0 = _v(_sub, _mdot(n, q0, m, rule), d, rule)
    d1 = _v(_sub, _mdot(n, q1, m, rule), d, rule)
    zero = _bc(0)
    out = []
    if _all(_le, d0, zero, 4):
        out.append(list(points[0]))
    if _all(_le, d1, zero, 4):
        out.append(list(points[1]))
    if _all(_lt, _v(_mul, d1, d0, rule), zero, 3):
        t = _v(_div, d0, _v(_sub, d0, d1, rule), rule)
        c = _v(_add, _v(_mul, _v(_sub, q1, q0, rule), t, rule), q0, rule)
        tag = points[0][3] if _all(_lt, zero, d0, 3) else points[1][3]
        out.append(c[:3] + [tag])
    return out


def box_capsule_core(mem, services, c, shape_box, frame_box, shape_cap, frame_cap, out, *,
                     mask=XYZ_MASK, nan_rule='sse'):
    """0x19d9160(shapeBox, &frameBox, shapeCapsule, &frameCapsule, out, capacity); c = the
    core's entry rsp. The capacity slot is never read. Returns eax (0, 1, 2, or the
    deep-path emitter's count)."""
    m = _mask(mem, mask)
    rule = nan_rule
    rsp, rbp = c - 0x318, c - 0x218
    h, r = mem.d(shape_cap + 0x40), mem.d(shape_cap + 0x44)
    ext = _and(_lanes(mem, shape_box + 0x40), m)
    f = [_lanes(mem, frame_cap + 0x10 * k) for k in range(4)]
    zero = _bc(0)
    # Axis end points (0,-h,0) and (0,+h,0) in world space (operand order as native).
    p0 = _v(_add, _v(_add, _v(_add, _v(_mul, zero, f[0], rule), f[3], rule),
                     _v(_mul, _bc(h ^ SIGN_MASK), f[1], rule), rule), _v(_mul, zero, f[2], rule), rule)
    t = _v(_add, _v(_add, _v(_mul, zero, f[0], rule), f[3], rule), _v(_mul, _bc(h), f[1], rule), rule)
    p1 = _v(_add, _v(_mul, zero, f[2], rule), t, rule)
    radius = _bc(r)
    _put_lanes(mem, rbp - 0x50, radius)
    _put_lanes(mem, rbp, ext)
    _put_lanes(mem, rbp - 0x60, p0)
    _put_lanes(mem, rsp + 0x40, p0)
    for k in range(4):
        _put_lanes(mem, rbp - 0x40 + 0x10 * k, _lanes(mem, frame_box + 0x10 * k))
    _put_lanes(mem, rbp + 0x120, p1)
    _put_lanes(mem, rsp + 0x50, p1)
    _call(services, mem, rsp, SEG_GJK_RVA, rbp + 0x130, rbp - 0x40, rsp + 0x40, 0x10)
    dist = _lanes(mem, rbp + 0x130)
    if not _all(_lt, _bc(GJK_EPS), dist, 3):
        return _box_capsule_deep(mem, services, rsp, rbp, shape_box, frame_box, out)
    on_box, on_axis = _lanes(mem, rbp + 0x140), _lanes(mem, rbp + 0x150)
    delta = _v(_sub, on_axis, on_box, rule)
    length = _sqrt(_hadd2(_and(_v(_mul, delta, delta, rule), m), rule))
    n = _v(_mul, delta, _bc(_div(ONE, length, rule)), rule)
    _put_lanes(mem, rbp - 0x50, n)
    face = _call(services, mem, rsp, BOX_FACE_PICK_RVA, frame_box, rbp - 0x50, 0, 0) & 0xFFFFFFFF
    _call(services, mem, rsp, BOX_FACE_PLANE_RVA, rbp - 0x60, frame_box, shape_box, face)
    plane = _lanes(mem, rbp - 0x60)
    cosine = [x & ABS_MASK for x in _mdot(_and(plane, m), n, m, rule)]
    if _all(_lt, _bc(PARALLEL_COS), cosine, 3):
        for k in range(4):
            mem.set_d(rbp - 0x34 + 0x10 * k, 0)
        mem.set_d(rbp, 0)
        # r8/r9 survive 0x19da3f0 (it writes neither), so the side-plane call sees them.
        _call(services, mem, rsp, BOX_SIDE_PLANES_RVA, rbp - 0x40, frame_box, shape_box, face)
        tag = face & 0xFFF
        pts = [p0[:3] + [tag | TAG_FIRST], p1[:3] + [tag | TAG_SECOND]]
        for k in range(4):
            pts = _segment_clip_pass(pts, _lanes(mem, rbp - 0x40 + 0x10 * k), m, rule)
            if len(pts) != 2:
                break                     # 0 or 1 point: the single-record path below
        else:
            nrm = _and(plane, m)
            d = _bc(plane[3])
            written = 0
            for p in pts:
                a = _and(p, m)
                s = _v(_sub, _mdot(a, nrm, m, rule), d, rule)
                if not _all(_le, s, radius, 4):
                    continue
                on_face = _v(_sub, a, _v(_mul, s, nrm, rule), rule)
                on_cap = _v(_sub, a, _v(_mul, radius, nrm, rule), rule)
                _write_record(mem, out + RECORD_STRIDE * written, nrm, _sub(s[0], r, rule),
                              on_face, on_cap, p[3])
                written += 1
            return written
    depth = _v(_sub, dist, radius, rule)
    if not _all(_le, depth, zero, 4):
        return 0
    on_cap = _v(_sub, on_axis, _v(_mul, radius, n, rule), rule)
    _write_record(mem, out, n, depth[0], on_box, on_cap, 0)
    return 1


def _box_capsule_deep(mem, services, rsp, rbp, shape_box, frame_box, out):
    """0x19d9d0d: GJK distance not above 2^-23. The box becomes the same hull 0x19db710
    builds (edge table magic static 0x143336930), then the capsule-hull axis selector
    0x19daf90 and its emitters 0x19daa60 (kind 0) / 0x19da4e0 (kind 2); others give 0."""
    half = [mem.d(shape_box + 0x40 + 4 * k) for k in range(3)]
    mem.view(BOX_EDGE_TABLE_VA, 0x60)[:] = box_edge_table()
    desc = rbp + 0x10
    build_box_hull(mem, desc, rbp + 0x38, rbp + 0x98, half)
    _call(services, mem, rsp, CAPSULE_HULL_SAT_RVA, rsp + 0x40, frame_box, desc, rbp - 0x60,
          [(0x20, '<Q', rbp + 0x120)])
    kind = mem.d(rsp + 0x40)
    if kind not in (0, 2):
        return 0
    st = [(0x20, '<Q', rbp + 0x120), (0x28, '<Q', rbp - 0x50), (0x30, '<Q', rsp + 0x40),
          (0x38, '<B', 0)]
    rva = CAPSULE_FACE_RVA if kind == 0 else CAPSULE_EDGE_RVA
    return _call(services, mem, rsp, rva, out, frame_box, desc, rbp - 0x60, st) & 0xFFFFFFFF


def box_capsule_tester(mem, geom, out, capacity=500, *, services, sp, mask=XYZ_MASK, nan_rule='sse'):
    """0x19db670(tester, geom, out, capacity): masked frame copies (frameB at rsp+0x30,
    frameA at rsp+0x70), out and capacity in the stack argument slots, then
    0x19d9160(shapeA, &frameA, shapeB, &frameB, out, capacity)."""
    m = _mask(mem, mask)
    rsp = sp - 0xB8
    for r in range(4):
        _put_lanes(mem, rsp + 0x30 + 0x10 * r, _and(_lanes(mem, geom + 0x40 + 0x10 * r), m))
        _put_lanes(mem, rsp + 0x70 + 0x10 * r, _and(_lanes(mem, geom + 0x10 * r), m))
    mem.put('<Q', rsp + 0x20, out)
    mem.put('<I', rsp + 0x28, capacity & 0xFFFFFFFF)
    return box_capsule_core(mem, services, rsp - 8, mem.q(geom + 0x80), rsp + 0x70,
                            mem.q(geom + 0x88), rsp + 0x30, out, mask=mask, nan_rule=nan_rule)


# --- (3,5) box-hull --------------------------------------------------------------------

def box_edge_table():
    """The 24 dwords 0x19db710 stores at 0x143336930 (12 edges of u16 v0, v1, f0, f1)."""
    return b''.join(struct.pack('<4H', *e) for e in BOX_EDGES)


def build_box_hull(mem, desc, vertices, faces, half_bits):
    """The box hull 0x19db710 builds: half_bits = raw x, y, z extent words. Writes the
    vertices, faces and descriptor (bytes +0x26/+0x27 untouched)."""
    for v, signs in enumerate(BOX_VERTEX_SIGNS):
        _put_lanes(mem, vertices + 12 * v, [h if s > 0 else h ^ SIGN_MASK for h, s in zip(half_bits, signs)])
    for k, (normal, axis) in enumerate(BOX_FACES):
        mem.view(faces + 0x14 * k, 0x14)[:] = struct.pack('<4IHH', *normal, half_bits[axis], 4, 4 * k)
    mem.view(desc, 0x26)[:] = struct.pack('<4QHHH', vertices, faces, BOX_EDGE_TABLE_VA,
                                          BOX_FACE_INDEX_VA, 8, 6, 12)


def face_contact(mem, services, sp, out, capacity, frame_ref, hull_ref, frame_inc, hull_inc,
                 face, reduce_flag, flip, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x18e4060; sp = entry rsp. Stack arguments are read from sp+0x28.. by native code;
    the model takes them as parameters (its callers store them). Returns the count."""
    m = _mask(mem, mask)
    rule = nan_rule
    rsp = sp - 0x18 - 0x1270
    rbp = sp - 0x1188
    face = _i32(face)
    faces_ref = mem.q(hull_ref + 8)
    plane = list(struct.unpack('<4I', bytes(mem.view(faces_ref + 0x14 * face, 16))))
    _put_lanes(mem, rsp + 0x30, plane)
    nloc = _and(plane, m)
    fr = [_lanes(mem, frame_ref + 0x10 * r) for r in range(4)]
    x1 = [_mul(a, nloc[1], rule) for a in fr[1]]
    x0 = [_mul(a, nloc[0], rule) for a in fr[0]]
    x2 = [_mul(a, nloc[2], rule) for a in fr[2]]
    x1 = [_add(a, b, rule) for a, b in zip(x1, x0)]
    world_n = [_add(a, b, rule) for a, b in zip(x2, x1)]
    tn = _and([_mul(a, b, rule) for a, b in zip(fr[3], world_n)], m)
    world_d = _add(_hadd2(tn, rule), plane[3], rule)
    _put_lanes(mem, rsp + 0x30, world_n[:3] + [world_d])
    wn = _and(world_n[:3] + [world_d], m)
    fi = [_lanes(mem, frame_inc + 0x10 * r) for r in range(3)]
    p = [[_mul(a, b, rule) for a, b in zip(fi[r], wn)] for r in range(3)]
    local = [_add(_add(p[r][0], p[r][1], rule), _add(p[r][2], p[r][3], rule), rule) for r in range(3)]
    local = _and(local + [local[2]], m)
    faces_inc = mem.q(hull_inc + 8)
    nfaces = mem.w(hull_inc + 0x22)

    def score(i):
        n = _and(_lanes(mem, faces_inc + 0x14 * i), m)
        return _hadd2(_and([_mul(a, b, rule) for a, b in zip(n, local)], m), rule)

    best, best_i = score(0), 0
    for i in range(1, nfaces):
        s = score(i)
        if _lt(s, best):
            best, best_i = s, i
    mem.set_d(rbp + 0x940, 0)
    for k in range(0x80):
        mem.set_d(rbp + 0x95C + 0x10 * k, 0)
    mem.set_d(rbp + 0x1150, 0)
    _call(services, mem, rsp, HULL_POLYGON_RVA, rbp + 0x140, frame_inc, hull_inc, face & 0xFFFFFFFF,
          [(0x20, '<I', best_i), (0x28, '<B', flip & 0xFF)])
    _call(services, mem, rsp, HULL_PLANES_RVA, rbp + 0x950, frame_ref, hull_ref, face & 0xFFFFFFFF)
    nplanes = mem.d(rbp + 0x1150)
    mem.set_d(rsp + 0x20, nplanes)
    n = clip_polygon(mem, services, rsp - 8, rbp + 0x140, mem.d(rbp + 0x940), 0x80, rbp + 0x950, nplanes)
    mem.set_b(rsp + 0x20, reduce_flag & 0xFF)
    count = reduce_contacts(mem, services, rsp - 8, rsp + 0x40, rbp + 0x140, n & 0xFFFFFFFF,
                            rsp + 0x30, reduce_flag) & 0xFFFFFFFF
    mem.set_d(rbp + 0x940, count)
    written = 0
    normal = _and(_lanes(mem, rsp + 0x30), m)
    for i in range(max(0, _i32(count))):
        if written >= (capacity & 0xFFFFFFFF):
            break
        depth = mem.d(rsp + 0x40 + 4 * i)
        point = _and(_lanes(mem, rbp + 0x140 + 0x10 * i), m)
        _emit(mem, out, written, normal, depth, point, 0, flip & 0xFF, rule)
        written += 1
    return written


def box_hull_core(mem, services, sp, geom, out, capacity, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x19db710(geom, out, capacity); sp = entry rsp. Returns the record count."""
    m = _mask(mem, mask)
    rsp = sp - 0x228
    rbp = rsp + 0x100
    shape_a = mem.q(geom + 0x80)
    half = [mem.d(shape_a + 0x40 + 4 * k) for k in range(3)]
    mem.view(BOX_EDGE_TABLE_VA, 0x60)[:] = box_edge_table()
    desc, verts, faces = rsp + 0x60, rbp - 0x78, rbp - 0x18
    build_box_hull(mem, desc, verts, faces, half)
    for r in range(4):
        _put_lanes(mem, rbp + 0xB0 + 0x10 * r, _and(_lanes(mem, geom + 0x10 * r), m))
        _put_lanes(mem, rbp + 0x70 + 0x10 * r, _and(_lanes(mem, geom + 0x40 + 0x10 * r), m))
    hull_b = mem.q(mem.q(geom + 0x88) + 0x100)
    edge_flag, reduce_flag = mem.b(geom + 0x91), mem.b(geom + 0x90)
    _call(services, mem, rsp, HULL_SAT_RVA, rsp + 0x50, rbp + 0xB0, desc, rbp + 0x70,
          [(0x20, '<Q', hull_b), (0x28, '<B', edge_flag)])
    kind = mem.d(rsp + 0x50)
    common = dict(mask=mask, nan_rule=nan_rule)
    if kind == 0:
        st = [(0x20, '<Q', rbp + 0x70), (0x28, '<Q', hull_b), (0x30, '<I', mem.d(rsp + 0x54)),
              (0x38, '<B', reduce_flag), (0x40, '<B', 0)]
        for off, fmt, v in st:
            mem.put(fmt, rsp + off, v)
        return face_contact(mem, services, rsp - 8, out, capacity, rbp + 0xB0, desc, rbp + 0x70,
                            hull_b, mem.d(rsp + 0x54), reduce_flag, 0, **common)
    if kind == 1:
        st = [(0x20, '<Q', rbp + 0xB0), (0x28, '<Q', desc), (0x30, '<I', mem.d(rsp + 0x58)),
              (0x38, '<B', reduce_flag), (0x40, '<B', 1)]
        for off, fmt, v in st:
            mem.put(fmt, rsp + off, v)
        return face_contact(mem, services, rsp - 8, out, capacity, rbp + 0x70, hull_b, rbp + 0xB0,
                            desc, mem.d(rsp + 0x58), reduce_flag, 1, **common)
    if kind == 2:
        return _call(services, mem, rsp, HULL_EDGE_RVA, out, capacity & 0xFFFFFFFF, rbp + 0xB0, desc,
                     [(0x20, '<Q', rbp + 0x70), (0x28, '<Q', hull_b), (0x30, '<Q', rsp + 0x50)])
    return 0


def box_hull_tester(mem, geom, out, capacity=500, *, services, sp, mask=XYZ_MASK, nan_rule='sse'):
    """0x19dbba0(tester, geom, out, capacity): thunk to 0x19db710 (same rsp)."""
    return box_hull_core(mem, services, sp, geom, out, capacity, mask=mask, nan_rule=nan_rule)


TESTERS = {(3, 3): box_box_tester, (3, 4): box_capsule_tester, (3, 5): box_hull_tester}
# Record-count bounds (see LINK_SOLVER.md "Narrow-phase box testers"). 'reduce' is geom+0x90
# set (0x18dd400 always sets it). None = bounded only by the clipped polygon (the per-plane
# clip ignores its capacity argument). 'honours_capacity' is whether `capacity` limits it.
MAX_RECORDS = {
    (3, 3): {'face_reduce': 4, 'face_no_reduce': None, 'edge': 1,
             'honours_capacity': {'face': True, 'edge': False}},
    (3, 4): {'clip': 2, 'single': 1, 'deep_kind0': 2, 'deep_kind2': 1, 'honours_capacity': False},
    (3, 5): {'face_reduce': 4, 'face_no_reduce': None, 'edge': 1,
             'honours_capacity': {'face': True, 'edge': 'edge emitter 0x18e3aa0: 0 when capacity is 0'}},
}
