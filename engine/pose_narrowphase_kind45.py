"""Narrow-phase testers for kind pairs (4,4), (4,5) and (5,5).

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase capsule and convex hull testers"
(static reads of the entries 0x19dcd40, 0x19ddbc0, 0x19dde00, the cores 0x19dbbc0,
0x19dd130, 0x19ddc60 and the penetrating capsule-hull helpers 0x19db470, 0x19db150,
0x19da4e0, 0x19daa60) and "Narrow-phase tester table and sphere-sphere tester"
(engine.pose_narrowphase_dispatch). Native comparison:
analysis/command-executor-audit/check_pose_narrowphase_kind45.py
-> native/snow_host/pose_narrowphase_kind45_validation.json. Every tester is reached
through slot 3 of the tester object as (tester, geom, out, capacity); 0x18dd400 passes
capacity 500 and sets geom+0x90 = 1.

Kind identification (from the fields the testers read; the names are our labels):

- kind 4: a capsule along its local Y axis. shape+0x40 is the half-height h and shape+0x44
  the radius r. Both testers build the axis segment (0,-h,0)..(0,+h,0) (constants
  (0,-1,0,0) at 0x1e4a920 and (0,1,0,0) at 0x1e25270 in 0x19dd130; (0,-h,0) plus
  direction (0,2h,0) in 0x19dbbc0) and inflate it by r.
- kind 5: a convex polyhedron. shape+0x100 points to the descriptor already used by the
  box/triangle producer helpers: +0 vertices (12-byte stride), +8 planes (20 bytes:
  nx,ny,nz,d, u16 face vertex count, u16 first face index), +0x10 edges (four u16: v0,
  v1, plane0, plane1), +0x18 u16 face index list, +0x20/+0x22/+0x24 u16 vertex, plane
  and edge counts.

Recovered behavior and the per-core record bounds:

- (4,4) capsule-capsule, core 0x19dbbc0: never reads its capacity argument; returns 0, 1
  or 2. Two records only from the near-parallel clip path, else at most one.
- (5,5) polyhedron pair, core 0x19ddc60: forwards capacity to the face emitter 0x18e4060
  (writes min(capacity, selected points)) and the edge emitter 0x18e3aa0 (0 when
  capacity is 0, else 1). The face path reduces to at most four points when geom+0x90
  is set; 0x18dd400 always sets it, so this tester returns at most four there.
  With geom+0x90 clear the count is bounded only by the clipped polygon (clip driver
  output cap 0x80) and capacity.
- (4,5) capsule-polyhedron, core 0x19dd130: never reads its capacity. Paths: separated
  0; shallow face clip 0..2; shallow single 1; penetrating face 0x19daa60 0..2;
  penetrating edge 0x19da4e0 exactly 1. So at most two records.

Supplied, not restated: the capsule-hull distance query 0x18f3710 (its 0x30-byte result is
an argument of capsule_hull_core). Reused models: 0x18e3450 side planes
(engine.pose_contact_side_planes, float model) on the penetrating face path; the (5,5)
tester composes engine.pose_contact_axis_selection (0x190f700),
engine.pose_contact_face_emit (0x18e4060) and engine.pose_contact_edge_emit (0x18e3aa0),
all float models, so (5,5) is exact for finite inputs only.

Float32 lane semantics follow engine.pose_contact_payload_update and
engine.pose_narrowphase_dispatch (exact double then one rounding, no FTZ/DAZ, default
NaN 0xffc00000, two-NaN choice by nan_rule). Operand order (destination first) is kept
for every lane operation because the emulator's two-NaN rule depends on it.

Authored choices: only the recovered runtime XYZ mask {-1,-1,-1,0} is modelled (the
mask at 0x3336890 is zero in the image and set by an initializer) and the comparison
vector at 0x33368c0 is zero. Function and argument names are ours.
"""
import struct

from engine.pose_contact_payload_update import XYZ_MASK, _add, _mul, _sub
from engine.pose_narrowphase_dispatch import _div, _le, _lt, _minps, _sqrt

RECORD_STRIDE = 0x30
SIGN = 0x80000000
ABS = 0x7FFFFFFF
ONE = 0x3F800000
EPS_SCALE = 0x36A7C5AC        # float32 at 0x1ef69e0, about 5e-6
PARALLEL_COS = 0x3F7F3B64     # float32 at 0x29cc100, 0.997
TINY = 0x3727C5AC             # float32 at 0x1e252b0, 1e-5
FEATURE_WORD = 0xFFFF0000     # record +0x2c
TAG_START = 0x80000000        # clip tags of the first capsule's two axis points
TAG_END = 0x81000000

CAPSULE_CAPSULE_ENTRY_RVA = 0x19DCD40
CAPSULE_CAPSULE_CORE_RVA = 0x19DBBC0
CAPSULE_HULL_ENTRY_RVA = 0x19DDBC0
CAPSULE_HULL_CORE_RVA = 0x19DD130
HULL_HULL_ENTRY_RVA = 0x19DDE00
HULL_HULL_CORE_RVA = 0x19DDC60


# --- 4-lane helpers (lists of four uint32 bit patterns) ----------------------------

def _v(op, a, b, r):
    return [op(x, y, r) for x, y in zip(a, b)]


def vadd(a, b, r): return _v(_add, a, b, r)
def vsub(a, b, r): return _v(_sub, a, b, r)
def vmul(a, b, r): return _v(_mul, a, b, r)
def vdiv(a, b, r): return _v(_div, a, b, r)
def vsqrt(a): return [_sqrt(x) for x in a]
def vxor(a, b): return [x ^ y for x, y in zip(a, b)]
def vmask(a): return [a[0], a[1], a[2], 0]          # andps with the runtime XYZ mask
def vabs(a): return [x & ABS for x in a]
def bc(x): return [x] * 4
def lt_all(a, b, n=3): return all(_lt(x, y) for x, y in list(zip(a, b))[:n])
def le_all(a, b, n=4): return all(_le(x, y) for x, y in list(zip(a, b))[:n])


def shuf(a, b, imm):
    return [a[imm & 3], a[(imm >> 2) & 3], b[(imm >> 4) & 3], b[(imm >> 6) & 3]]


def hsum(v, r):
    """haddps twice on a vector: (v0+v1)+(v2+v3) in all lanes."""
    return bc(_add(_add(v[0], v[1], r), _add(v[2], v[3], r), r))


def mdot(a, b, r):
    """(a*b) masked, then two haddps: a is the destination operand."""
    return hsum(vmask(vmul(a, b, r)), r)


def _rows(raw):
    return [vmask(list(struct.unpack_from('<4I', raw, 16 * k))) for k in range(4)]


def relative_basis(frame_b, frame_a, r):
    """0x19dcfc0(out, B, A): row i lane k = masked dot of A row i with B row k."""
    a, b = frame_a, frame_b
    orders = [[(a[0], b[0]), (b[1], a[0]), (b[2], a[0])],
              [(a[1], b[0]), (a[1], b[1]), (a[1], b[2])],
              [(a[2], b[0]), (a[2], b[1]), (a[2], b[2])]]
    return [[mdot(x, y, r)[0] for x, y in row] + [0] for row in orders]


def perpendicular(v):
    """0x19dce10: the tangent choice used by the four-record selector."""
    x, y, z = v[0], v[1], v[2]
    ax, ay, az = x & ABS, y & ABS, z & ABS
    m6 = _lt(_sub(ay, ax, 'sse'), 0)
    m9 = _lt(_sub(_minps(ax, ay), az, 'sse'), 0)
    # sub with a NaN operand returns that NaN; the comparison is then false either way,
    # so the two-NaN rule cannot change the result here.
    if not m9:
        return [y, x ^ SIGN, 0, 0]
    return [z, 0, x ^ SIGN, 0] if m6 else [0, z, y ^ SIGN, 0]


def _world(frame, p, r):
    """add(F2*z, add(add(F0*x, F3), F1*y)) with frame rows as destinations."""
    t = vadd(vadd(vmul(frame[0], bc(p[0]), r), frame[3], r), vmul(frame[1], bc(p[1]), r), r)
    return vadd(vmul(frame[2], bc(p[2]), r), t, r)


def _world_dir(frame, n, r):
    return vadd(vmul(frame[2], bc(n[2]), r), vadd(vmul(frame[1], bc(n[1]), r),
                                                    vmul(frame[0], bc(n[0]), r), r), r)


def _record(n, depth, pa, tag, pb):
    return struct.pack('<12I', n[0], n[1], n[2], depth, pa[0], pa[1], pa[2], tag,
                       pb[0], pb[1], pb[2], FEATURE_WORD)


def clip_segment(points, plane, r, span_first=False):
    """One plane of the two-point clip used by 0x19dbbc0, 0x19dd130 and 0x19daa60.

    points: up to two entries (xyz lane bits, u32 tag). plane: (normal xyz bits, d bits).
    Keeps points with dot(plane, p) - d <= 0 and appends the crossing point when the two
    signed distances have a negative product. Never produces more than two points.
    """
    n = vmask(list(plane[0]) + [0])
    d = bc(plane[1])
    if not points:
        return []
    if len(points) == 1:
        p = points[0]
        dist = vsub(mdot(vmask(list(p[0]) + [0]), n, r), d, r)   # point is the destination
        return [] if lt_all(bc(0), dist) else [p]
    (p0, t0), (p1, t1) = points
    q0, q1 = vmask(list(p0) + [0]), vmask(list(p1) + [0])
    d0 = vsub(mdot(n, q0, r), d, r)
    d1 = vsub(mdot(n, q1, r), d, r)
    out = []
    if le_all(d0, bc(0)):
        out.append(points[0])
    if le_all(d1, bc(0)):
        out.append(points[1])
    if lt_all(vmul(d1, d0, r), bc(0)):
        t = vdiv(d0, vsub(d0, d1, r), r)
        # 0x19dbbc0/0x19dd130 multiply t * (q1 - q0); 0x19daa60 multiplies (q1 - q0) * t.
        span = vsub(q1, q0, r)
        c = vadd(vmul(span, t, r) if span_first else vmul(t, span, r), q0, r)
        out.append((c[:3], t0 if lt_all(bc(0), d0) else t1))
    return out


# --- (4,4) capsule-capsule: core 0x19dbbc0 -----------------------------------------

def capsule_capsule_core(cap_a, frame_a, cap_b, frame_b, nan_rule='sse'):
    """0x19dbbc0 on lane bits. cap_x = (half-height bits, radius bits) from shape+0x40/+0x44;
    frames are masked 4-lane rows. Returns the list of 48-byte records (0, 1 or 2)."""
    r = nan_rule
    ha, ra = cap_a
    hb, rb = cap_b
    fb = frame_b
    eps = bc(_mul(_add(ra, rb, r), EPS_SCALE, r))
    r_a, r_b = bc(ra), bc(rb)
    two_ha, two_hb = bc(_add(ha, ha, r)), bc(_add(hb, hb, r))
    neg_tb = vxor(bc(SIGN), fb[3])
    t_a = [hsum(vmul(frame_a[3], fb[k], r), r)[0] for k in range(3)] + [0]
    # Not masked before the horizontal adds: lane 3 contributes 0 * -0 = -0.
    t_b = [hsum(vmul(fb[k], neg_tb, r), r)[0] for k in range(3)] + [0]
    origin = vadd(t_a, t_b, r)                                   # A origin in B space
    m = relative_basis(fb, frame_a, r)
    pa_local, da_local = [0, ha ^ SIGN, 0, 0], [0, two_ha[0], 0, 0]
    start_a = vadd(vmul(m[2], bc(pa_local[2]), r),
                   vadd(vadd(vmul(m[0], bc(pa_local[0]), r), origin, r),
                        vmul(m[1], bc(pa_local[1]), r), r), r)
    dir_a = vadd(vmul(m[2], bc(da_local[2]), r),
                 vadd(vmul(m[1], bc(da_local[1]), r), vmul(bc(da_local[0]), m[0], r), r), r)
    start_b, dir_b = [0, hb ^ SIGN, 0, 0], [0, two_hb[0], 0, 0]
    ba = vmask(vmul(dir_b, dir_a, r))                            # xmm10, reused below
    cosine = vabs(vdiv(hsum(ba, r), vmul(two_hb, two_ha, r), r))
    end_b = vadd(dir_b, start_b, r)
    if lt_all(bc(PARALLEL_COS), cosine):
        records = _capsule_parallel(start_a, dir_a, start_b, dir_b, end_b, two_hb,
                                    r_a, r_b, fb, r)
        if records is not None:
            return records
    return _capsule_general(start_a, dir_a, start_b, dir_b, ba, eps, r_a, r_b, fb, r)


def _closest_on_b(e, start_b, dir_b, end_b, r):
    s = mdot(dir_b, vsub(e, start_b, r), r)
    if le_all(s, bc(0)):
        return start_b
    length = mdot(dir_b, dir_b, r)
    if le_all(length, s):
        return end_b
    return vadd(start_b, vmul(vdiv(s, length, r), dir_b, r), r)


def _capsule_parallel(start_a, dir_a, start_b, dir_b, end_b, two_hb, r_a, r_b, fb, r):
    """Near-parallel branch: clip A's axis to B's slab; None falls to the general path."""
    u = vdiv(dir_b, two_hb, r)
    neg_u = vxor(bc(SIGN), u)
    plane1 = (neg_u[:3], mdot(neg_u, start_b, r)[0])
    plane2 = (u[:3], mdot(end_b, u, r)[0])
    pts = [(start_a[:3], TAG_START), (vadd(dir_a, start_a, r)[:3], TAG_END)]
    pts = clip_segment(pts, plane1, r)
    if len(pts) < 2:
        return None
    pts = clip_segment(pts, plane2, r)
    if len(pts) != 2:
        return None
    e = [vmask(list(p) + [0]) for p, _ in pts]
    tags = [t for _, t in pts]
    c = [_closest_on_b(x, start_b, dir_b, end_b, r) for x in e]
    off = [vsub(c[k], e[k], r) for k in range(2)]
    length = [vsqrt(mdot(o, o, r)) for o in off]
    big = [lt_all(bc(TINY), x) for x in length]
    if big[0] and big[1]:
        n = [vdiv(off[0], length[0], r), vdiv(off[1], length[1], r)]
    elif big[0]:
        n = [vdiv(off[0], length[0], r)] * 2
    elif big[1]:
        n = [vdiv(off[1], length[1], r)] * 2
    else:
        p = perpendicular(dir_a)
        p = vmul(p, vdiv(bc(ONE), vsqrt(mdot(p, p, r)), r), r)
        n = [p, p]
    rsum = vadd(r_b, r_a, r)
    records = []
    for k in range(2):
        if not le_all(length[k], rsum):
            continue
        pa = vadd(vmul(n[k], r_a, r), e[k], r)
        pb = vsub(c[k], vmul(n[k], r_b, r), r)
        records.append(_record(_world_dir(fb, n[k], r), vsub(length[k], rsum, r)[0],
                               _world(fb, pa, r), tags[k], _world(fb, pb, r)))
    return records


def _capsule_general(start_a, dir_a, start_b, dir_b, ba, eps, r_a, r_b, fb, r):
    w = vsub(start_a, start_b, r)
    a = hsum(vmask(vmul(dir_a, dir_a, r)), r)
    e = hsum(vmask(vmul(dir_b, dir_b, r)), r)
    f = hsum(vmask(vmul(w, dir_b, r)), r)
    d = hsum(vmask(vmul(w, dir_a, r)), r)
    c = hsum(ba, r)
    det = vsub(vmul(e, a, r), vmul(c, c, r), r)
    zero = bc(0)
    if le_all(vabs(det), vmul(a, bc(TINY), r)):
        s_num, t_num, s_den, t_den = zero, f, e, e
    else:
        s_num = vsub(vmul(f, c, r), vmul(d, e, r), r)
        t_num = vsub(vmul(f, a, r), vmul(d, c, r), r)
        if lt_all(s_num, zero):
            s_num, t_num, s_den, t_den = zero, f, det, e
        elif lt_all(det, s_num):
            s_num, t_num, s_den, t_den = det, vadd(f, c, r), det, e
        else:
            s_den, t_den = det, det
    neg_d = vxor(bc(SIGN), d)
    if lt_all(t_num, zero):
        tc = zero
        if lt_all(neg_d, zero):
            sc = zero
        elif lt_all(a, neg_d):
            sc = bc(ONE)
        else:
            sc = vdiv(neg_d, a, r)
    elif lt_all(t_den, t_num):
        tc = bc(ONE)
        x = vadd(c, neg_d, r)
        if lt_all(x, zero):
            sc = zero
        elif lt_all(a, x):
            sc = bc(ONE)
        else:
            sc = vdiv(x, a, r)
    else:
        sc = vdiv(s_num, s_den, r)
        tc = vdiv(t_num, t_den, r)
    s_dir = vmul(sc, dir_a, r)
    t_dir = vmul(tc, dir_b, r)
    ca = vadd(s_dir, start_a, r)
    delta = vsub(vadd(s_dir, w, r), t_dir, r)
    cb = vadd(t_dir, start_b, r)
    rsum = vadd(r_b, r_a, r)
    dist2 = hsum(vmask(vmul(delta, delta, r)), r)
    if not le_all(dist2, vmul(rsum, rsum, r)):
        return []
    axis = vsub(cb, ca, r)
    dist = vsqrt(dist2)
    if le_all(vabs(dist), eps):
        axis = vsub(vmul(shuf(dir_a, dir_a, 0xD2), shuf(dir_b, dir_b, 0xC9), r),
                    vmul(shuf(dir_a, dir_a, 0xC9), shuf(dir_b, dir_b, 0xD2), r), r)
        if le_all(vabs(axis), bc(TINY)):
            axis = perpendicular(dir_a)
    n = vmul(axis, vdiv(bc(ONE), vsqrt(mdot(axis, axis, r)), r), r)
    pa = vadd(ca, vmul(n, r_a, r), r)
    pb = vsub(cb, vmul(n, r_b, r), r)
    # Final transforms put the broadcast lane first for x/z terms (operand order only).
    wa = vadd(vmul(bc(pa[2]), fb[2], r),
              vadd(vadd(vmul(fb[0], bc(pa[0]), r), fb[3], r), vmul(fb[1], bc(pa[1]), r), r), r)
    wb = vadd(vmul(bc(pb[2]), fb[2], r),
              vadd(vadd(vmul(bc(pb[0]), fb[0], r), fb[3], r), vmul(fb[1], bc(pb[1]), r), r), r)
    wn = vadd(vmul(bc(n[2]), fb[2], r), vadd(vmul(fb[1], bc(n[1]), r),
                                             vmul(bc(n[0]), fb[0], r), r), r)
    return [_record(wn, vsub(dist, rsum, r)[0], wa, 0, wb)]


def _geom(mem, geom):
    raw = bytes(mem.view(geom, 0x93))
    shape_a, shape_b = struct.unpack_from('<QQ', raw, 0x80)
    return _rows(raw[:0x40]), _rows(raw[0x40:0x80]), shape_a, shape_b, raw


def capsule_capsule_tester(mem, geom, out, capacity=500, *, nan_rule='sse'):
    """0x19dcd40(tester, geom, out, capacity) over flat memory; returns the count.

    The entry masks both frames and passes shape+0x40 (null for a null shape, which
    faults natively; the model raises). capacity is forwarded and never read.
    """
    frame_a, frame_b, shape_a, shape_b, _ = _geom(mem, geom)
    if not shape_a or not shape_b:
        raise ValueError('null shape: the native core dereferences a null pointer')
    cap_a = struct.unpack('<2I', bytes(mem.view(shape_a + 0x40, 8)))
    cap_b = struct.unpack('<2I', bytes(mem.view(shape_b + 0x40, 8)))
    records = capsule_capsule_core(cap_a, frame_a, cap_b, frame_b, nan_rule)
    for i, rec in enumerate(records):
        mem.view(out + RECORD_STRIDE * i, RECORD_STRIDE)[:] = rec
    return len(records)


# --- kind 5 descriptor -----------------------------------------------------------------

def read_hull_descriptor(mem, desc):
    """Decode the descriptor at shape+0x100 into the dict used by the contact helpers."""
    verts, planes, edges, faces = (mem.q(desc + 8 * k) for k in range(4))
    nv, np_, ne = mem.w(desc + 0x20), mem.w(desc + 0x22), mem.w(desc + 0x24)
    out = dict(vertices=[], planes=[], edges=[], face_indices=[])
    for i in range(nv):
        out['vertices'].append(list(struct.unpack('<3f', bytes(mem.view(verts + 12 * i, 12)))))
    for i in range(np_):
        nx, ny, nz, d, count, first = struct.unpack('<4fHH', bytes(mem.view(planes + 20 * i, 20)))
        out['planes'].append([nx, ny, nz, d])
        out['face_indices'].append([mem.w(faces + 2 * (first + k)) for k in range(count)])
    for i in range(ne):
        out['edges'].append(struct.unpack('<4H', bytes(mem.view(edges + 8 * i, 8))))
    return out


def _float_frame(rows):
    return [list(struct.unpack('<3f', struct.pack('<3I', *row[:3]))) for row in rows]


# --- (5,5) polyhedron pair: thunk 0x19dde00 -> core 0x19ddc60 ----------------------------

def hull_hull_tester(mem, geom, out, capacity=500):
    """0x19dde00(tester, geom, out, capacity): returns the count.

    The thunk drops the tester and calls 0x19ddc60(geom, out, capacity). The core masks
    both frames, reads each shape's descriptor at shape+0x100 and runs the axis selector
    0x190f700 with edge queries enabled by geom+0x91. Selection kind 0 emits faces with A
    as reference (0x18e4060, flip 0), kind 1 with B as reference (flip 1), kind 2 the edge
    pair (0x18e3aa0) and kind 3 returns 0. geom+0x90 is the face emitter's reduce-to-four
    flag. Capacity bounds both emitters.
    """
    from engine.pose_contact_axis_selection import select_geometry_contact_axis
    from engine.pose_contact_face_emit import emit_face_contacts
    from engine.pose_contact_edge_emit import emit_edge_contact
    frame_a, frame_b, shape_a, shape_b, raw = _geom(mem, geom)
    fa, fb = _float_frame(frame_a), _float_frame(frame_b)
    a = read_hull_descriptor(mem, mem.q(shape_a + 0x100))
    b = read_hull_descriptor(mem, mem.q(shape_b + 0x100))
    reduce_flag, edge_flag = raw[0x90] != 0, raw[0x91] != 0
    sel = select_geometry_contact_axis(fa, a, fb, b, edge_enabled=edge_flag)
    capacity &= 0xFFFFFFFF
    kind = sel['kind']
    if kind == 3:
        return 0
    buf = bytearray(0x30 * max(1, min(capacity, 128)))   # authored scratch; native writes in place
    if kind == 2:
        n = emit_edge_contact(buf, capacity, fa, a, fb, b, sel)
    elif kind == 0:
        n = emit_face_contacts(buf, min(capacity, 128), fa, a, fb, b, sel['first'], reduce_flag, False)
    else:
        n = emit_face_contacts(buf, min(capacity, 128), fb, b, fa, a, sel['second'], reduce_flag, True)
    if n:
        mem.view(out, 0x30 * n)[:] = buf[:0x30 * n]
    return n


# --- (4,5) capsule-polyhedron: entry 0x19ddbc0 -> core 0x19dd130 --------------------------

GJK_EPS = 0x34000000          # float32 at 0x1eeb1f0, 2**-23
FACE_SCORE_INIT = 0xFF7FFFFF  # float32 at 0x1eba010, -FLT_MAX
NEG_Y = [0, 0xBF800000, 0, 0]  # 0x1e4a920
POS_Y = [0, ONE, 0, 0]         # 0x1e25270


def _world_bcast_first(frame, p, r):
    """add(bz*F2, add(add(bx*F0, F3), by*F1)) with the broadcast lanes as destinations."""
    t = vadd(vadd(vmul(bc(p[0]), frame[0], r), frame[3], r), vmul(bc(p[1]), frame[1], r), r)
    return vadd(vmul(bc(p[2]), frame[2], r), t, r)


def capsule_axis_points(half, frame_a, r):
    """0x19dd130 prologue: world endpoints of the capsule axis (0,-h,0) and (0,+h,0)."""
    h = bc(half)
    return (_world_bcast_first(frame_a, vmul(NEG_Y, h, r), r),
            _world_bcast_first(frame_a, vmul(POS_Y, h, r), r))


def _plane_world(frame, plane_bits, r):
    """Hull plane (nx,ny,nz,d bits) to world, as the core does after the face pick."""
    loc = vmask(list(plane_bits))
    n = vadd(vmul(bc(loc[2]), frame[2], r), vadd(vmul(bc(loc[1]), frame[1], r),
                                                 vmul(bc(loc[0]), frame[0], r), r), r)
    d = vadd(mdot(n, frame[3], r), bc(plane_bits[3]), r)
    return n, d[0]


def pick_hull_face(frame, planes, direction, r):
    """0x19dda40(out, frame, descriptor, direction): (score bits, index or 0xffffffff).

    Strictly greatest masked dot of each world plane normal with `direction`, starting
    from -FLT_MAX; the first maximum is kept.
    """
    best, index = bc(FACE_SCORE_INIT), 0xFFFFFFFF
    for i, p in enumerate(planes):
        loc = vmask(list(p))
        n = vadd(vmul(frame[2], bc(loc[2]), r), vadd(vmul(frame[1], bc(loc[1]), r),
                                                     vmul(frame[0], bc(loc[0]), r), r), r)
        d = vadd(mdot(frame[3], n, r), bc(p[3]), r)
        s = mdot(vmask(n[:3] + [d[0]]), direction, r)
        if lt_all(best, s):
            best, index = s, i
    return best[0], index


def hull_face_side_planes(vertices, planes, edges, face, frame, r):
    """0x18e3640: one world side plane per edge whose first or second plane is `face`.

    vertices: 4-lane bits (x,y,z,next word) per vertex, as the 16-byte loads see them.
    Returns (normal xyz bits, d bits) tuples in edge order.
    """
    nf = vmask(list(planes[face]))
    out = []
    for v0, v1, p0, p1 in edges:
        if p0 == face:
            a, b = vmask(vertices[v0]), vmask(vertices[v1])
            e = vsub(b, a, r)
        elif p1 == face:
            a, b = vmask(vertices[v0]), vmask(vertices[v1])
            e = vsub(a, b, r)
        else:
            continue
        s = vsub(vmul(shuf(e, e, 0xC9), shuf(nf, nf, 0xD2), r),
                 vmul(shuf(nf, nf, 0xC9), shuf(e, e, 0xD2), r), r)
        s = vmul(s, vdiv(bc(ONE), vsqrt(mdot(s, s, r)), r), r)
        d = mdot(s, a, r)[0]
        loc = vmask(s)
        w = vadd(vmul(frame[2], bc(loc[2]), r), vadd(vmul(frame[1], bc(loc[1]), r),
                                                     vmul(bc(loc[0]), frame[0], r), r), r)
        out.append((w[:3], vadd(mdot(frame[3], w, r), bc(d), r)[0]))
    return out


def capsule_hull_core(cap_a, frame_a, hull, frame_b, gjk, nan_rule='sse'):
    """0x19dd130 on lane bits; returns (records, path).

    cap_a: (half-height bits, radius bits) of the kind-4 shape. hull: dict from
    read_capsule_hull_inputs ('vertices' are the shape+0x40 rows, 'desc_vertices' the
    descriptor +0 rows, 'planes', 'edges', and float 'side_vertices'/'face_indices' for
    0x18e3450). gjk(p0, p1): the supplied result of 0x18f3710 for the two world axis
    points: (distance lanes, point lanes at +0x10, point lanes at +0x20) of its output.

    Paths: 'separated' (radius < distance, 0 records), 'face' (shallow, face-parallel
    axis clipped to the face, 0..2 records), 'single' (shallow, 1 record), and the
    penetrating paths 'deep_face' (0x19daa60, 0..2) and 'deep_edge' (0x19da4e0, 1).
    """
    r = nan_rule
    half, radius = cap_a
    rad = bc(radius)
    p0, p1 = capsule_axis_points(half, frame_a, r)
    dist, on_hull, on_axis = gjk(p0, p1)
    if lt_all(rad, dist):
        return [], 'separated'
    if not lt_all(bc(GJK_EPS), dist):
        return capsule_hull_deep(p0, p1, rad, hull, frame_b, r)
    d = vsub(on_hull, on_axis, r)
    n = vmul(d, vdiv(bc(ONE), vsqrt(mdot(d, d, r)), r), r)
    _, face = pick_hull_face(frame_b, hull['planes'], vxor(bc(SIGN), n), r)
    if face == 0xFFFFFFFF:
        raise ValueError('no hull planes: the native core indexes plane -1')
    plane_n, plane_d = _plane_world(frame_b, hull['planes'][face], r)
    if lt_all(bc(PARALLEL_COS), vabs(mdot(vmask(plane_n), n, r))):
        pts = [(p0[:3], (face & 0xFFF) | 0x80000000), (p1[:3], (face & 0xFFF) | 0x81000000)]
        for plane in hull_face_side_planes(hull['vertices'], hull['planes'], hull['edges'], face, frame_b, r):
            pts = clip_segment(pts, plane, r)
        if len(pts) == 2:
            nm = vmask(plane_n)
            neg = vxor(bc(SIGN), nm)
            records = []
            for k, ((p, tag), normal) in enumerate(zip(pts, (neg, n))):
                e = vmask(list(p) + [0])
                s = vsub(mdot(e, nm, r), bc(plane_d), r)
                if le_all(s, rad):
                    records.append(_record(normal, vsub(s, rad, r)[0], vadd(vmul(normal, rad, r), e, r),
                                           tag, vadd(vmul(normal, s, r), e, r)))
            return records, 'face'
    rec = _record(n, vsub(dist, rad, r)[0], vadd(vmul(n, rad, r), on_axis, r), 0, on_hull)
    return [rec], 'single'


# --- (4,5) penetrating path: 0x19db470, 0x19db150, 0x19da4e0, 0x19daa60 -------------------

EDGE_SCALE = 0x3F7AE148       # float32 at 0x1e7b7c0, 0.98
EDGE_BIAS = 0x3C23D70A        # float32 at 0x1df3d14, 0.01
EDGE_PARALLEL = 0x358637BD    # float32 at 0x1e93b80, 1e-6 (used negated)
EDGE_MIN_CROSS = 0x3A83126F   # float32 at 0x1ea9750, 1e-3
SELECT_ZERO = [0, 0, 0, 0]    # comparison vector 0x33368c0 (zero in the image)


def _world_plane_normal(frame, loc, r):
    """b2*z + (b0*x + b1*y): frame rows as destinations (0x19db470)."""
    return vadd(vmul(frame[2], bc(loc[2]), r),
                vadd(vmul(frame[0], bc(loc[0]), r), vmul(frame[1], bc(loc[1]), r), r), r)


def hull_face_query(frame, planes, p0, p1, r):
    """0x19db470(out, frameB, descriptor, &p0, &p1) -> (score bits, plane index or -1).

    Per plane: world plane (n, d'), s = minps(n.p0 - d', n.p1 - d'). The first plane with
    s > 0 (lanes 0..2) returns at once; otherwise the strictly greatest s from -FLT_MAX.
    """
    best, index = bc(FACE_SCORE_INIT), 0xFFFFFFFF
    for i, p in enumerate(planes):
        nw = _world_plane_normal(frame, vmask(list(p)), r)
        dw = vadd(mdot(frame[3], nw, r), bc(p[3]), r)
        plane = vmask(nw[:3] + [dw[0]])
        s0 = vsub(mdot(p0, plane, r), bc(dw[0]), r)
        s1 = vsub(mdot(p1, plane, r), bc(dw[0]), r)
        s = [_minps(x, y) for x, y in zip(s0, s1)]
        if lt_all(bc(0), s):
            return s[0], i
        if lt_all(best, s):
            best, index = s, i
    return best[0], index


def _hadd(a, b, r):
    return [_add(a[0], a[1], r), _add(a[2], a[3], r), _add(b[0], b[1], r), _add(b[2], b[3], r)]


def _local_point(frame, p, r):
    """Unmasked products, haddps(haddps(b0*d, b1*d), haddps(b2*d, b2*d)), then masked."""
    d = vsub(p, frame[3], r)
    x0, x1, x2 = (vmul(frame[k], d, r) for k in range(3))
    return vmask(_hadd(_hadd(x0, x1, r), _hadd(x2, x2, r), r))


def hull_edge_query(frame, vertices, planes, edges, p0, p1, r):
    """0x19db150(out, frameB, descriptor, &p0, &p1) -> (score bits, edge index, segment index).

    Works in hull-local space. An edge is a candidate when its two face normals lie on
    opposite sides of the segment direction (product of dots < -1e-6). Axis = (q0 - q1) x
    (v0 - v1), oriented away from the sum of the two face normals; separation =
    axis.q0 - axis.v0. Cross products shorter than 1e-3 score -FLT_MAX. The first
    positive separation returns at once; otherwise the strictly greatest. Nothing found:
    (-FLT_MAX, -1, -1). vertices are the descriptor +0 rows (16-byte loads).
    """
    q0, q1 = _local_point(frame, p0, r), _local_point(frame, p1, r)
    u = vsub(q1, q0, r)
    u = vmul(u, vdiv(bc(ONE), vsqrt(mdot(u, u, r)), r), r)
    neg_eps = bc(EDGE_PARALLEL ^ SIGN)
    best, out = bc(FACE_SCORE_INIT), (FACE_SCORE_INIT, 0xFFFFFFFF, 0xFFFFFFFF)
    for k, (v0, v1, pl0, pl1) in enumerate(edges):
        n0, n1 = vmask(list(planes[pl0])), vmask(list(planes[pl1]))
        if not lt_all(vmul(mdot(n1, u, r), mdot(n0, u, r), r), neg_eps):
            continue
        a, b = vmask(list(vertices[v0])), vmask(list(vertices[v1]))
        e = vsub(a, b, r)
        w = vsub(q0, q1, r)
        axis = vsub(vmul(shuf(w, w, 0xD2), shuf(e, e, 0xC9), r),
                    vmul(shuf(w, w, 0xC9), shuf(e, e, 0xD2), r), r)
        length = vsqrt(mdot(axis, axis, r))
        if lt_all(length, bc(EDGE_MIN_CROSS)):
            sep = bc(FACE_SCORE_INIT)
        else:
            axis = vdiv(axis, length, r)
            if lt_all(mdot(vadd(n1, n0, r), axis, r), bc(0)):
                axis = vxor(axis, bc(SIGN))
            sep = vsub(mdot(axis, q0, r), mdot(axis, a, r), r)
        if lt_all(bc(0), sep):
            return sep[0], k, 0
        if lt_all(best, sep):
            best, out = sep, (sep[0], k, 0)
    return out


def _f(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def _side_planes_18e3450(hull, frame, face):
    """0x18e3450 through engine.pose_contact_side_planes (float model; finite only)."""
    from engine.pose_contact_side_planes import append_side_planes
    storage = bytearray(0x804)
    frame_f = [[_f(x) for x in row[:3]] for row in frame]
    append_side_planes(storage, frame_f, hull['side_vertices'], hull['face_indices'][face],
                       [_f(x) for x in hull['planes'][face][:3]])
    count = struct.unpack_from('<I', storage, 0x800)[0]
    return [(list(struct.unpack_from('<3I', storage, 16 * i)), struct.unpack_from('<I', storage, 16 * i + 12)[0])
            for i in range(count)]


def hull_deep_face_contact(frame, hull, face, p0, p1, rad, flip, r):
    """0x19daa60(out, frameB, descriptor, &p0, &p1, &radius, query, flip) -> records.

    Clips the axis through the face's side planes (0x18e3450); any pass that leaves no
    point returns 0. Each surviving point with plane distance s <= 0 (all four lanes)
    gives one record: depth s - r, points p - r*n and p - s*n, feature word +0x1c = 0.
    At most two points survive, so at most two records.
    """
    plane = hull['planes'][face]
    loc = vmask(list(plane))
    nw = vadd(vmul(frame[2], bc(loc[2]), r),
              vadd(vmul(frame[1], bc(loc[1]), r), vmul(bc(loc[0]), frame[0], r), r), r)
    dw = vadd(mdot(frame[3], nw, r), bc(plane[3]), r)[0]
    pts = [(p0[:3], (face & 0xFFF) | 0x80000000), (p1[:3], (face & 0xFFF) | 0x81000000)]
    for side in _side_planes_18e3450(hull, frame, face):
        pts = clip_segment(pts, side, r, span_first=True)
        if not pts:
            return []
    n4 = vmask(nw[:3] + [dw])
    records = []
    for p, _tag in pts:
        e = vmask(list(p) + [0])
        s = vsub(mdot(n4, e, r), bc(dw), r)
        if not le_all(s, bc(0)):
            continue
        proj = vsub(e, vmul(s, n4, r), r)
        surf = vsub(e, vmul(rad, n4, r), r)
        depth = vsub(s, rad, r)[0]
        if flip:
            records.append(_record(vxor(bc(SIGN), n4), depth, surf, 0, proj))
        else:
            records.append(_record(n4, depth, proj, 0, surf))
    return records


def hull_deep_edge_contact(frame, hull, edge, p0, p1, rad, flip, r):
    """0x19da4e0(out, frameB, descriptor, &p0, &p1, &radius, query, flip) -> one record.

    Closest points of the axis segment and the hull edge (segment clamp with a 1e-5
    relative parallel test). Normal = (d1 x d2) reversed, i.e. d2 x d1, normalised, then
    negated when it points along the sum of the edge's two world face normals (lane
    compare against 0x33368c0). Depth is -(|Q - P|^2 + r): the squared distance, not the
    distance. Always one record.
    """
    v0, v1, pl0, pl1 = hull['edges'][edge]
    b0, b1, b2, t = frame
    n0l, n1l = vmask(list(hull['planes'][pl0])), vmask(list(hull['planes'][pl1]))
    n0w = vadd(vmul(b2, bc(n0l[2]), r), vadd(vmul(b0, bc(n0l[0]), r), vmul(b1, bc(n0l[1]), r), r), r)
    n1w = vadd(vmul(b2, bc(n1l[2]), r), vadd(vmul(b0, bc(n1l[0]), r), vmul(b1, bc(n1l[1]), r), r), r)
    w0 = _world_bcast_first(frame, vmask(list(hull['desc_vertices'][v0])), r)
    w1 = _world_bcast_first(frame, vmask(list(hull['desc_vertices'][v1])), r)
    d1 = vsub(p1, p0, r)
    rr = vsub(w0, p0, r)
    d2 = vsub(w1, w0, r)
    a = mdot(d1, d1, r)
    f1 = mdot(d1, rr, r)
    b = mdot(d1, d2, r)
    e = mdot(d2, d2, r)
    f2 = mdot(d2, rr, r)
    tol = vmul(e, bc(TINY), r)
    det = vsub(vmul(a, e, r), vmul(b, b, r), r)
    zero = bc(0)
    if le_all(vabs(det), tol):
        t_num, t_den, s_num, s_den = zero, a, f1, a
    else:
        s_num = vsub(vmul(f1, e, r), vmul(f2, b, r), r)
        t_num = vsub(vmul(f1, b, r), vmul(f2, a, r), r)
        t_den = det
        if lt_all(t_num, zero):
            t_num, s_num, s_den = zero, f1, a
        elif lt_all(det, t_num):
            t_num, s_num, s_den = det, vadd(f1, b, r), a
        else:
            s_den = det
    nf2 = vxor(bc(SIGN), f2)
    if lt_all(s_num, zero):
        s = zero
        if lt_all(nf2, zero):
            tt = zero
        elif lt_all(e, nf2):
            tt = bc(ONE)
        else:
            tt = vdiv(nf2, e, r)
    elif lt_all(s_den, s_num):
        s = bc(ONE)
        x = vadd(nf2, b, r)
        if lt_all(x, zero):
            tt = zero
        elif lt_all(e, x):
            tt = bc(ONE)
        else:
            tt = vdiv(x, e, r)
    else:
        tt = vdiv(t_num, t_den, r)
        s = vdiv(s_num, s_den, r)
    nsum = vadd(n1w, n0w, r)
    cross = vsub(vmul(shuf(d1, d1, 0xD2), shuf(d2, d2, 0xC9), r),
                 vmul(shuf(d1, d1, 0xC9), shuf(d2, d2, 0xD2), r), r)
    sd1 = vmul(d1, s, r)
    td2 = vmul(d2, tt, r)
    diff = vsub(vadd(td2, rr, r), sd1, r)
    q = vadd(td2, w0, r)
    p = vadd(sd1, p0, r)
    inv = vdiv(bc(ONE), vsqrt(mdot(cross, cross, r)), r)
    dd = vadd(mdot(diff, diff, r), rad, r)
    axis = vmul(cross, inv, r)
    sdot = mdot(nsum, axis, r)
    normal = [(x ^ SIGN) if _lt(c, z) else x for x, c, z in zip(axis, sdot, SELECT_ZERO)]
    depth = dd[0] ^ SIGN
    surf = vsub(p, vmul(rad, normal, r), r)
    if flip:
        return [_record(vxor(bc(SIGN), normal), depth, surf, 0, q)]
    return [_record(normal, depth, q, 0, surf)]


def capsule_hull_deep(p0, p1, rad, hull, frame, r):
    """Penetrating branch of 0x19dd130 (GJK distance <= 2^-23); returns (records, path).

    face = 0x19db470; if face score > 0 (comiss): face contact. Else edge = 0x19db150;
    edge contact when edge score > 0 or edge score > face score * 0.98 + 0.01 (scalar
    mulss/addss, ordered compares), otherwise face contact. Both contacts run with
    flip = 1 (normal from the capsule toward the hull, point on the capsule first).
    """
    fs, fi = hull_face_query(frame, hull['planes'], p0, p1, r)
    if fi == 0xFFFFFFFF:
        raise ValueError('no hull planes: the native contact indexes plane -1')
    if _f(fs) > 0:
        return hull_deep_face_contact(frame, hull, fi, p0, p1, rad, True, r), 'deep_face'
    es, ei, _ = hull_edge_query(frame, hull['desc_vertices'], hull['planes'], hull['edges'], p0, p1, r)
    threshold = _add(_mul(fs, EDGE_SCALE, r), EDGE_BIAS, r)
    if _f(es) > 0 or _f(es) > _f(threshold):
        return hull_deep_edge_contact(frame, hull, ei, p0, p1, rad, True, r), 'deep_edge'
    return hull_deep_face_contact(frame, hull, fi, p0, p1, rad, True, r), 'deep_face'


def read_capsule_hull_inputs(mem, geom):
    """Decode geom, the kind-4 shape and the kind-5 shape for capsule_hull_core."""
    frame_a, frame_b, shape_a, shape_b, _ = _geom(mem, geom)
    cap = struct.unpack('<2I', bytes(mem.view(shape_a + 0x40, 8)))
    desc = mem.q(shape_b + 0x100)
    verts = mem.q(shape_b + 0x40)
    desc_verts, planes_ptr, edges_ptr = mem.q(desc), mem.q(desc + 8), mem.q(desc + 0x10)
    nv, np_, ne = mem.w(desc + 0x20), mem.w(desc + 0x22), mem.w(desc + 0x24)
    decoded = read_hull_descriptor(mem, desc)
    hull = dict(
        vertices=[list(struct.unpack('<4I', bytes(mem.view(verts + 12 * i, 16)))) for i in range(nv)],
        desc_vertices=[list(struct.unpack('<4I', bytes(mem.view(desc_verts + 12 * i, 16)))) for i in range(nv)],
        planes=[list(struct.unpack('<4I', bytes(mem.view(planes_ptr + 20 * i, 16)))) for i in range(np_)],
        edges=[struct.unpack('<4H', bytes(mem.view(edges_ptr + 8 * i, 8))) for i in range(ne)],
        side_vertices=decoded['vertices'], face_indices=decoded['face_indices'])
    return cap, frame_a, hull, frame_b


def capsule_hull_tester(mem, geom, out, capacity=500, *, gjk, nan_rule='sse'):
    """0x19ddbc0(tester, geom, out, capacity) over flat memory; returns (count, path).

    The entry masks both frames and passes the raw shape pointers. capacity is forwarded
    and never read; every path writes at most two records. The shallow face path reads
    vertices through shape+0x40 (0x18e3640); the penetrating path reads the descriptor's
    own vertex array (+0).
    """
    cap, frame_a, hull, frame_b = read_capsule_hull_inputs(mem, geom)
    records, path = capsule_hull_core(cap, frame_a, hull, frame_b, gjk, nan_rule)
    for i, rec in enumerate(records):
        mem.view(out + RECORD_STRIDE * i, RECORD_STRIDE)[:] = rec
    return len(records), path
