"""Narrow-phase tester for the kind pair (4,6): capsule against kind-6 triangle-mesh terrain.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase capsule-terrain (kind 6) tester"
(static reads of the (4,6) slot-3 entry 0x198af50, the (6,4) core 0x19cc160 and its callees
0x19c9530, 0x18c64a0, 0x1910760, 0x19101e0, 0x1935ca0, 0x1996d00, 0x1997fd0) and "Narrow-phase
sphere testers and swap wrapper" (the flip 0x1994f60). Native comparison:
analysis/command-executor-audit/check_pose_narrowphase_capsule_terrain6.py
-> native/snow_host/pose_narrowphase_capsule_terrain6_validation.json.

Recovered structure (names are ours, not recovered identifiers):

- 0x198af50 is a swap wrapper exactly like 0x198b400/0x198b590/0x198b720: it builds a
  geom block with the frames and shapes exchanged, calls 0x19cc160 (slot 3 of the (6,4)
  vtable 0x29cb170) with the same out pointer and capacity, then flips the returned
  records with 0x1994f60. The (6,4) core therefore works with A = terrain, B = capsule.
- Kind 6 (from field use): shape+0x20 default collision-filter object, +0x40 u32 edge
  filter mode (1 = back-face test 0x1996d00, 2 = neighbourhood test 0x19974c0, other = none),
  +0x48 mesh, +0x50 filter-object table indexed by the per-triangle byte table +0x60,
  +0x68 u32 filter enable, +0x70/+0x74/+0x78 per-axis vertex scale. Mesh: +0x30 float3
  vertices (12-byte stride), +0x40 u16 indices (three per triangle), +0x48 u32 triangle
  count, +0x70 u16 per-triangle group key, +0x80 bounding tree (+0 extent, +0xc minimum,
  +0x18 12-byte nodes with 8-bit quantized child boxes and u16 child/triangle ids),
  +0xa8 u16 triangle pairs per edge and +0xb8 u32 edge id per triangle edge (mode 2 only).
- Per triangle at most two records: 0x1910760 (both capsule ends on one side of the
  triangle plane) writes one record per end inside the triangle prism and one per
  remaining end for the nearest triangle edges, bounded by the remaining capacity;
  0x19101e0 (ends on opposite sides) writes exactly 0 or 1. The loop stops once
  `capacity` records exist, so the result never exceeds capacity (capacity 0 gives 0).
- Record +0x2c = (triangle << 16) | group key; +0x1c = 0. With geom+0x90 set, a final pass
  keeps, per group key, only the records whose world normal is within 0.001 per component
  of the deepest record's normal (0x1e25210 = 0.001; 0x1e3da60 = FLT_MAX start).

Supplied, not restated: the tree query 0x1952b20 (`query(tree_address, aabb_words,
capacity) -> list of triangle ids`), the mode-2 filter 0x19974c0 (`edge_filter(mem, shape,
triangle, records_address, count) -> count`), and allocation (the 0x80-entry overflow
buffer from 0x18c9140, the key-array growth 0x193d810), which do not change results.

Float32 lane semantics follow engine.pose_contact_payload_update (exact double then one
rounding, default NaN 0xffc00000, two-NaN choice by nan_rule; 'x87' is the emulator rule).
Operand order (destination first) is kept for every lane operation. Only the runtime XYZ
mask {-1,-1,-1,0} is modelled; 0x33368c0 is zero.
"""
import struct

from engine.pose_contact_payload_update import _add, _is_nan, _mul, _sub, _to_float
from engine.pose_narrowphase_dispatch import _div, _le, _lt, _sqrt
from engine.pose_narrowphase_sphere import SWAP_GEOM_ADDRESS, _Overlay, flip_contact_records, swapped_geom

RECORD_STRIDE = 0x30
SIGN = 0x80000000
ABS = 0x7FFFFFFF
ONE = 0x3F800000
TOL_PARALLEL = 0x3727C5AC    # 0x1e252b0, 1e-5: tri block +0x70 and the segment-edge |det| scale
TOL_DIRECTION = 0x358637BD   # 0x1e93b80, 1e-6: |C_s - C_t| <= tol -> triangle normal
FLT_MAX = 0x7F7FFFFF         # 0x1eba000 (crossing case start) and 0x1e3da60 (key pass start)
KEY_NORMAL_TOL = 0x3A83126F  # 0x1e25210, 0.001
ZERO_CMP = 0                 # 0x33368c0 (zero)
FIRST_QUERY_CAP = 0x80
IDENTITY_ROWS = ((ONE, 0, 0, 0), (0, ONE, 0, 0), (0, 0, ONE, 0))   # 0x1e25250/0x1e25270/0x1df4060

SWAP_ENTRY_RVA = 0x198AF50
CORE_RVA = 0x19CC160
SAME_SIDE_RVA = 0x1910760
CROSSING_RVA = 0x19101E0
SEGMENT_TRIANGLE_RVA = 0x1935CA0
BACKFACE_FILTER_RVA = 0x1996D00
RAW_NORMAL_RVA = 0x1997FD0
NEIGHBOUR_FILTER_RVA = 0x19974C0      # supplied
TREE_QUERY_RVA = 0x1952B20            # supplied
INVERSE_RVA = 0x19C9530
CAPSULE_BOUNDS_RVA = 0x18C64A0


# --- 4-lane helpers (lists of four uint32 bit patterns) --------------------------------

def vadd(a, b, r): return [_add(x, y, r) for x, y in zip(a, b)]
def vsub(a, b, r): return [_sub(x, y, r) for x, y in zip(a, b)]
def vmul(a, b, r): return [_mul(x, y, r) for x, y in zip(a, b)]
def vdiv(a, b, r): return [_div(x, y, r) for x, y in zip(a, b)]
def vsqrt(a): return [_sqrt(x) for x in a]
def vxor(a, b): return [x ^ y for x, y in zip(a, b)]
def vmask(a): return [a[0], a[1], a[2], 0]
def vabs(a): return [x & ABS for x in a]
def bc(x): return [x] * 4
def yzx(v): return [v[1], v[2], v[0], v[3]]      # shufps 0xc9
def zxy(v): return [v[2], v[0], v[1], v[3]]      # shufps 0xd2


def hsum(v, r):
    """Two haddps: (v0+v1)+(v2+v3) in every lane."""
    return bc(_add(_add(v[0], v[1], r), _add(v[2], v[3], r), r))


def mdot(a, b, r):
    """mulps a, b (a is the destination), andps mask, two haddps."""
    return hsum(vmask(vmul(a, b, r)), r)


def all_lt(a, b, n):
    return all(_lt(x, y) for x, y in list(zip(a, b))[:n])


def all_le(a, b, n):
    return all(_le(x, y) for x, y in list(zip(a, b))[:n])


def all_eq(a, b, n):
    return all(not _is_nan(x) and not _is_nan(y) and _to_float(x) == _to_float(y) for x, y in list(zip(a, b))[:n])


def normalise(v, r):
    """ones / sqrtps(mdot(v, v)), then mulps v, inv."""
    return vmul(v, vdiv(bc(ONE), vsqrt(mdot(v, v, r)), r), r)


def _u16(mem, a): return struct.unpack('<H', bytes(mem.view(a, 2)))[0]
def _u32(mem, a): return struct.unpack('<I', bytes(mem.view(a, 4)))[0]
def _u64(mem, a): return struct.unpack('<Q', bytes(mem.view(a, 8)))[0]
def _vec(mem, a): return list(struct.unpack('<4I', bytes(mem.view(a, 16))))


def _record(n, depth, pa, tag, pb, feature):
    return struct.pack('<12I', n[0], n[1], n[2], depth, pa[0], pa[1], pa[2], tag, pb[0], pb[1], pb[2], feature)


def _copy_record(mem, dst, src):
    mem.view(dst, RECORD_STRIDE)[:] = bytes(mem.view(src, RECORD_STRIDE))


# --- frame helpers ----------------------------------------------------------------------

def inverse3(rows, r):
    """0x19c9530(out, rows): cofactor inverse of the three masked rows; out lane 3 = 0."""
    r0, r1, r2 = rows[:3]
    c12 = vsub(vmul(zxy(r2), yzx(r1), r), vmul(yzx(r2), zxy(r1), r), r)
    det = hsum(vmask(vmul(r0, c12, r)), r)
    inv = vmask(vdiv(bc(ONE), det, r))
    a = vmul(vsub(vmul(yzx(r1), zxy(r2), r), vmul(yzx(r2), zxy(r1), r), r), inv, r)
    b = vmul(vsub(vmul(yzx(r2), zxy(r0), r), vmul(yzx(r0), zxy(r2), r), r), inv, r)
    c = vmul(vsub(vmul(zxy(r1), yzx(r0), r), vmul(yzx(r1), zxy(r0), r), r), inv, r)
    return [[a[k], b[k], c[k], 0] for k in range(3)]


def relative_capsule(frame_a, frame_b, h, r):
    """0x19cc160 prologue: B (capsule) rows in A (terrain) space and the capsule axis.

    Returns (rel rows R0, R1, R2, t), P0 = R*(0,-h,0)+t, D = R*(0,2h,0), P1 = D + P0."""
    inv = inverse3(frame_a, r)
    i0, i1, i2 = inv
    b0, b1, b2, bt = frame_b
    nt = vxor(bc(SIGN), frame_a[3])
    t0 = vadd(vmul(i2, bc(nt[2]), r), vadd(vmul(i1, bc(nt[1]), r), vmul(bc(nt[0]), i0, r), r), r)
    rel_t = vadd(vmul(i2, bc(bt[2]), r), vadd(vadd(vmul(bc(bt[0]), i0, r), t0, r), vmul(i1, bc(bt[1]), r), r), r)
    rel0 = vadd(vmul(i2, bc(b0[2]), r), vadd(vmul(i1, bc(b0[1]), r), vmul(i0, bc(b0[0]), r), r), r)
    rel1 = vadd(vmul(i2, bc(b1[2]), r), vadd(vmul(i1, bc(b1[1]), r), vmul(bc(b1[0]), i0, r), r), r)
    rel2 = vadd(vmul(i2, bc(b2[2]), r), vadd(vmul(i1, bc(b2[1]), r), vmul(bc(b2[0]), i0, r), r), r)
    two_h = _add(h, h, r)
    p0 = vadd(vmul(bc(0), rel2, r), vadd(vadd(vmul(bc(0), rel0, r), rel_t, r), vmul(bc(h ^ SIGN), rel1, r), r), r)
    d = vadd(vmul(bc(0), rel2, r), vadd(vmul(bc(two_h), rel1, r), vmul(bc(0), rel0, r), r), r)
    p1 = vadd(d, p0, r)
    return (rel0, rel1, rel2, rel_t), p0, d, p1


def capsule_bounds(h, radius, rel, r):
    """0x18c64a0(shape, out, rel rows): local AABB words (min xyz, max xyz)."""
    axis, t = rel[1], rel[3]
    ext = [_add(_mul(h, axis[k], r) & ABS, radius, r) for k in range(3)]
    return [_sub(t[k], ext[k], r) for k in range(3)] + [_add(ext[k], t[k], r) for k in range(3)]


def query_bounds(box, scale, r):
    """AABB divided by the per-axis scale, as passed to the tree query (rbp+0x80)."""
    inv = [_div(ONE, s, r) for s in scale]
    return [_mul(box[k], inv[k % 3], r) for k in range(6)]


# --- triangle data ------------------------------------------------------------------------

def triangle_vertices(mem, mesh, scale, tri, r):
    idx = mesh['indices']
    out = []
    for j in range(3):
        v = _u16(mem, idx + 2 * ((3 * tri + j) & 0xFFFFFFFF))
        a = mesh['vertices'] + 12 * v
        out.append([_mul(scale[k], _u32(mem, a + 4 * k), r) for k in range(3)] + [0])
    return out


def triangle_block(v, r):
    """The core's per-triangle block (rbp+0x140): V0..V2, edges, unit normal, 1e-5."""
    v0, v1, v2 = v
    e0, e1, e2 = vsub(v1, v0, r), vsub(v2, v1, r), vsub(v0, v2, r)
    big = vsub(vmul(zxy(e1), yzx(e0), r), vmul(yzx(e1), zxy(e0), r), r)
    n = normalise(big, r)
    return dict(v=[v0, v1, v2], e=[e0, e1, e2], n=n, eps=bc(TOL_PARALLEL))


# --- segment-edge closest points (shared by 0x1910760 and 0x19101e0) ----------------------

def segment_edge(p0, d, d2, w, v, e, r, *, crossing):
    """Clamped closest points between segment p0 + s*d and edge v + t*e.

    `crossing` selects the operand order of 0x19101e0 (d = D.w, c*a, e*a); otherwise
    0x1910760 (w.D, a*c, a*e). Returns (C_s, C_t, dist2) as 4-lane vectors."""
    b = mdot(d, e, r)
    c = mdot(e, e, r)
    a = hsum(d2, r)
    tol = vmul(hsum(d2, r), bc(TOL_PARALLEL), r)
    dd = mdot(d, w, r) if crossing else mdot(w, d, r)
    ee = mdot(w, e, r)
    denom = vsub(vmul(c, a, r) if crossing else vmul(a, c, r), vmul(b, b, r), r)
    zero = bc(0)
    if all_le(vabs(denom), tol, 4):
        s_d, s_n, t_n, t_d = c, zero, ee, c
    else:
        s_d = denom
        s_n = vsub(vmul(ee, b, r), vmul(dd, c, r), r)
        t_n = vsub(vmul(ee, a, r) if crossing else vmul(a, ee, r), vmul(dd, b, r), r)
        t_d = denom
        if all_lt(s_n, zero, 3):
            s_n, t_n, t_d = zero, ee, c
        elif all_lt(denom, s_n, 3):
            t_n, s_n, t_d = vadd(ee, b, r), denom, c
    neg_d = vxor(bc(SIGN), dd)
    if all_lt(t_n, zero, 3):
        t = zero
        if all_lt(neg_d, zero, 3):
            s = zero
        elif all_lt(a, neg_d, 3):
            s = bc(ONE)
        else:
            s = vdiv(neg_d, a, r)
    elif all_lt(t_d, t_n, 3):
        t = bc(ONE)
        if all_lt(vadd(b, neg_d, r), zero, 3):
            s = zero
        elif all_lt(a, vadd(b, neg_d, r), 3):
            s = bc(ONE)
        else:
            s = vdiv(vadd(b, neg_d, r), a, r)
    else:
        s = vdiv(s_n, s_d, r)
        t = vdiv(t_n, t_d, r)
    te = vmul(t, e, r)
    sd = vmul(s, d, r)
    c_s = vadd(sd, p0, r)
    diff = vsub(vadd(sd, w, r), te, r)
    c_t = vadd(te, v, r)
    return c_s, c_t, mdot(diff, diff, r)


def _edge_record(c_s, c_t, radius, tri_n, feature, r):
    """Shared tail: normal from C_t toward C_s (triangle normal when |C_s-C_t| <= 1e-6)."""
    v = vsub(c_s, c_t, r)
    n = tri_n if all_le(vabs(v), bc(TOL_DIRECTION), 4) else normalise(v, r)
    dv = vsub(c_t, c_s, r)
    depth = vsub(vsqrt(mdot(dv, dv, r)), bc(radius), r)
    if not all_le(depth, bc(0), 4):
        return None
    pb = vsub(c_s, vmul(bc(radius), n, r), r)
    return _record(n, depth[0], c_t, 0, pb, feature)


# --- 0x1910760: both capsule ends on one side of the triangle plane -----------------------

def inside_reach(neg_c, limit, rr, four_h2, along, r):
    """Offset of point B along the oriented normal for an end inside the prism:
    r when the axis points away from the plane (-c <= 0), r / sqrt(1 - c^2) up to
    2h / sqrt(4h^2 + r^2), else sqrt(r^2 - 4h^2 + (2hc)^2) + (-2hc)."""
    if all_le(neg_c, bc(0), 4):
        return rr
    if all_le(neg_c, limit, 4):
        return vdiv(rr, vsqrt(vsub(bc(ONE), vmul(neg_c, neg_c, r), r)), r)
    return vadd(vsqrt(vadd(vsub(vmul(rr, rr, r), four_h2, r), vmul(along, along, r), r)), along, r)


def nearest_edges(dist, outside):
    """Edge indices used for the `outside` (1 or 2) ends: the nearest, or the two nearest,
    by squared distance (strict <, lanes 0..2; ties go to the later edge)."""
    if outside == 1:
        if all_lt(dist[0], dist[1], 3):
            return [0 if all_lt(dist[0], dist[2], 3) else 2]
        return [1 if all_lt(dist[1], dist[2], 3) else 2]
    if all_lt(dist[0], dist[1], 3):
        return [0, 2 if all_lt(dist[2], dist[1], 3) else 1]
    return [1, 2 if all_lt(dist[2], dist[0], 3) else 0]


def same_side_contacts(seg, p0, d, h, radius, dots, tri, capacity, feature, r):
    """0x1910760: returns the list of records (at most min(2, capacity))."""
    v0, v1, v2 = tri['v']
    e0, e1, e2 = tri['e']
    n, eps = tri['n'], tri['eps']
    neg_eps = vxor(bc(SIGN), eps)
    inside = []
    for p in seg:
        c0 = vsub(vmul(yzx(n), zxy(e0), r), vmul(yzx(e0), zxy(n), r), r)
        ok = all_le(neg_eps, mdot(vsub(p, v0, r), c0, r), 4)
        if ok:
            c1 = vsub(vmul(zxy(e1), yzx(n), r), vmul(zxy(n), yzx(e1), r), r)
            ok = all_le(neg_eps, mdot(vsub(p, v1, r), c1, r), 4)
        if ok:
            c2 = vsub(vmul(zxy(e2), yzx(n), r), vmul(yzx(e2), zxy(n), r), r)
            ok = all_le(neg_eps, mdot(vsub(p, v2, r), c2, r), 4)
        inside.append(ok)
    outside = inside.count(False)
    records = []
    if any(inside):
        two_h = bc(_add(h, h, r))
        rr = bc(radius)
        flip = [_lt(x, ZERO_CMP) for x in vadd(dots[1], dots[0], r)]
        n_o = [(x ^ SIGN) if f else x for x, f in zip(n, flip)]
        four_h2 = vmul(two_h, two_h, r)
        limit = vdiv(two_h, vsqrt(vadd(four_h2, vmul(rr, rr, r), r)), r)
        for k in range(2):
            if len(records) >= capacity:
                break
            if not inside[k]:
                continue
            p, q = seg[k], seg[1 - k]
            s = mdot(vsub(p, v0, r), n, r)
            qp = vsub(q, p, r)
            proj = vsub(p, vmul(s, n, r), r)
            u = vmul(qp, vdiv(bc(ONE), vsqrt(mdot(qp, qp, r)), r), r)
            neg_c = vxor(mdot(u, n_o, r), bc(SIGN))
            along = vmul(neg_c, two_h, r)
            reach = inside_reach(neg_c, limit, rr, four_h2, along, r)
            dv = vsub(proj, p, r)
            depth = vsub(vsqrt(mdot(dv, dv, r)), rr, r)
            if all_le(depth, bc(0), 4):
                pb = vsub(p, vmul(reach, n_o, r), r)
                records.append(_record(n_o, depth[0], proj, 0, pb, feature))
    if outside == 0 or len(records) >= capacity:
        return records
    d2 = vmask(vmul(d, d, r))
    near = []
    for k in range(3):
        w = vsub(p0, tri['v'][k], r)
        near.append(segment_edge(p0, d, d2, w, tri['v'][k], tri['e'][k], r, crossing=False))
    for k in nearest_edges([x[2] for x in near], outside):
        if len(records) >= capacity:
            break
        rec = _edge_record(near[k][0], near[k][1], radius, n, feature, r)
        if rec is not None:
            records.append(rec)
    return records


# --- 0x1935ca0 and 0x19101e0: ends on opposite sides --------------------------------------

def segment_hits_triangle(tri, p0, d, r):
    """0x1935ca0(tri block, &{P0, D}, out): True when the segment pierces the triangle
    (barycentric tolerance 1e-5, 0 <= t and t^2 <= |D|^2 with t along the unit direction)."""
    v0, v1, v2 = tri['v']
    eps = tri['eps']
    e1 = vsub(v1, v0, r)
    e2 = vsub(v2, v0, r)
    dn = vmul(d, vdiv(bc(ONE), vsqrt(mdot(d, d, r)), r), r)
    pvec = vsub(vmul(yzx(dn), zxy(e2), r), vmul(yzx(e2), zxy(dn), r), r)
    det = mdot(pvec, e1, r)
    if all_eq(det, bc(0), 4):
        return False
    tvec = vsub(p0, v0, r)
    inv = vmask(vdiv(bc(ONE), det, r))
    u = vmul(mdot(tvec, pvec, r), inv, r)
    neg_eps = vxor(bc(SIGN), eps)
    if all_lt(u, neg_eps, 3):
        return False
    hi = vadd(eps, bc(ONE), r)
    if all_lt(hi, u, 3):
        return False
    qvec = vsub(vmul(yzx(tvec), zxy(e1), r), vmul(yzx(e1), zxy(tvec), r), r)
    v = vmul(mdot(qvec, dn, r), inv, r)
    if all_lt(v, neg_eps, 3):
        return False
    if all_lt(hi, vadd(v, u, r), 3):
        return False
    t = vmul(mdot(qvec, e2, r), inv, r)
    if not all_le(bc(0), t, 4):
        return False
    return all_le(vmul(t, t, r), mdot(d, d, r), 4)


def crossing_contact(seg, p0, d, radius, dots, tri, feature, r):
    """0x19101e0: one record or None (capacity is not an argument)."""
    n = tri['n']
    rr = bc(radius)
    if segment_hits_triangle(tri, p0, d, r):
        best, pt, proj = bc(FLT_MAX), bc(0), bc(0)
        for k in range(2):
            sq = vmul(dots[k], dots[k], r)
            if all_lt(sq, best, 3):
                best, pt = sq, seg[k]
                proj = vsub(seg[k], vmul(dots[k], n, r), r)
        v = vsub(proj, pt, r)
        nn = n if all_le(vabs(v), bc(TOL_DIRECTION), 4) else normalise(v, r)
        depth = vsub(vxor(bc(SIGN), vsqrt(mdot(v, v, r))), rr, r)
        pb = vsub(pt, vmul(rr, nn, r), r)
        return _record(nn, depth[0], proj, 0, pb, feature)
    d2 = vmask(vmul(d, d, r))
    best, c_s, c_t = bc(FLT_MAX), bc(0), bc(0)
    for k in range(3):
        w = vsub(p0, tri['v'][k], r)
        cs, ct, dist = segment_edge(p0, d, d2, w, tri['v'][k], tri['e'][k], r, crossing=True)
        if all_lt(dist, best, 3):
            best, c_s, c_t = dist, cs, ct
    return _edge_record(c_s, c_t, radius, n, feature, r)


# --- mode-1 filter 0x1996d00 with 0x1997fd0 ------------------------------------------------

def raw_face_normal(mem, mesh, tri, r):
    """0x1997fd0: unit normal of the unscaled triangle, (V1-V0) x (V2-V0) in scalar ops."""
    idx = mesh['indices']
    base = 3 * (tri & 0xFFFF)
    ids = [_u16(mem, idx + 2 * (base + j)) for j in range(3)]
    p = [[_u32(mem, mesh['vertices'] + 12 * i + 4 * k) for k in range(3)] for i in ids]
    a = [_sub(p[2][k], p[0][k], r) for k in range(3)]    # V2 - V0
    b = [_sub(p[1][k], p[0][k], r) for k in range(3)]    # V1 - V0
    nx = _sub(_mul(a[2], b[1], r), _mul(b[2], a[1], r), r)
    ny = _sub(_mul(b[2], a[0], r), _mul(b[0], a[2], r), r)
    nz = _sub(_mul(b[0], a[1], r), _mul(b[1], a[0], r), r)
    length = _sqrt(_add(_add(_mul(ny, ny, r), _mul(nx, nx, r), r), _mul(nz, nz, r), r))
    inv = _div(ONE, length, r)
    return [_mul(nx, inv, r), _mul(ny, inv, r), _mul(nz, inv, r), 0]


def backface_filter(mem, mesh, tri, out, count, r):
    """0x1996d00: drop (swap with the last) records whose local normal has a negative dot
    with the raw face normal; scans from the last record down. Returns the new count."""
    fn = raw_face_normal(mem, mesh, tri, r)
    rows = IDENTITY_ROWS
    face = vadd(vmul(list(rows[2]), bc(fn[2]), r),
                vadd(vmul(list(rows[1]), bc(fn[1]), r), vmul(list(rows[0]), bc(fn[0]), r), r), r)
    for i in range(count - 1, -1, -1):
        rec = out + RECORD_STRIDE * i
        dot = hsum(vmask(vmul(vmask(_vec(mem, rec)), face, r)), r)
        if all_lt(dot, bc(0), 3):
            count -= 1
            _copy_record(mem, rec, out + RECORD_STRIDE * count)
    return count


# --- mesh reading, record transform and the key pass ---------------------------------------

def read_terrain_shape(mem, shape):
    mesh_ptr = _u64(mem, shape + 0x48)
    mesh = dict(address=mesh_ptr, vertices=_u64(mem, mesh_ptr + 0x30), indices=_u64(mem, mesh_ptr + 0x40),
                count=_u32(mem, mesh_ptr + 0x48), groups=_u64(mem, mesh_ptr + 0x70), tree=mesh_ptr + 0x80)
    return dict(mode=_u32(mem, shape + 0x40), mesh=mesh, scale=[_u32(mem, shape + 0x70 + 4 * k) for k in range(3)],
                filter_enable=_u32(mem, shape + 0x68), filter_bytes=_u64(mem, shape + 0x60),
                filter_table=_u64(mem, shape + 0x50), default_filter=_u64(mem, shape + 0x20))


def triangle_admitted(mem, terrain, capsule_shape, tri):
    """Collision-filter gate (core 0x19cc700..0x19cc748); always true when +0x68 is 0."""
    if not terrain['filter_enable']:
        return True
    if terrain['filter_bytes']:
        slot = mem.view(terrain['filter_bytes'] + tri, 1)[0]
        f = _u64(mem, terrain['filter_table'] + 8 * slot)
    else:
        f = terrain['default_filter']
    c = _u64(mem, capsule_shape + 0x20)
    return ((_u64(mem, f + 0x50) & _u64(mem, c + 0x48)) | (_u64(mem, c + 0x50) & _u64(mem, f + 0x48))) != 0


def transform_records(mem, out, count, frame_a, r):
    """Local -> world: normal by rows only, points by rows and translation (xyz written)."""
    a0, a1, a2, at = frame_a
    for i in range(count):
        rec = out + RECORD_STRIDE * i
        n, p, q = (vmask(_vec(mem, rec + o)) for o in (0, 0x10, 0x20))
        n2 = vadd(vmul(a2, bc(n[2]), r), vadd(vmul(a1, bc(n[1]), r), vmul(a0, bc(n[0]), r), r), r)
        p2 = vadd(vmul(a2, bc(p[2]), r), vadd(vadd(vmul(a0, bc(p[0]), r), at, r), vmul(a1, bc(p[1]), r), r), r)
        q2 = vadd(vmul(a2, bc(q[2]), r), vadd(vadd(vmul(bc(q[0]), a0, r), at, r), vmul(a1, bc(q[1]), r), r), r)
        for off, v in ((0, n2), (0x10, p2), (0x20, q2)):
            mem.view(rec + off, 12)[:] = struct.pack('<3I', *v[:3])


def _cmp_ge(x, y):
    """comiss x, y; jae: CF clear (x >= y); unordered sets CF."""
    return not (_is_nan(x) or _is_nan(y)) and _to_float(x) >= _to_float(y)


def _cmp_above(x, y):
    """comiss x, y; ja: ordered and x > y."""
    return not (_is_nan(x) or _is_nan(y)) and _to_float(x) > _to_float(y)


def key_pass(mem, out, count, r):
    """geom+0x90 pass: per low-16-bit key (in order of first appearance), find the first
    record of least depth (unordered comparisons take the record), then remove every
    record of that key whose normal differs by more than 0.001 in any component."""
    keys = []
    for i in range(count):
        k = _u16(mem, out + RECORD_STRIDE * i + 0x2C)
        if k not in keys:
            keys.append(k)
    for key in keys:
        best, bn = FLT_MAX, (0, 0, 0)
        for i in range(count):
            rec = out + RECORD_STRIDE * i
            if _u16(mem, rec + 0x2C) == key:
                depth = _u32(mem, rec + 0xC)
                if not _cmp_ge(depth, best):
                    best = depth
                    bn = tuple(_u32(mem, rec + 4 * k) for k in range(3))
        i = 0
        while i < count:
            rec = out + RECORD_STRIDE * i
            if _u16(mem, rec + 0x2C) == key:
                if any(_cmp_above(_sub(_u32(mem, rec + 4 * k), bn[k], r) & ABS, KEY_NORMAL_TOL) for k in range(3)):
                    count -= 1
                    _copy_record(mem, rec, out + RECORD_STRIDE * count)
                    continue
            i += 1
    return count


# --- the (6,4) core 0x19cc160 and the (4,6) swap entry 0x198af50 ---------------------------

def _rows(mem, geom, base):
    return [vmask(_vec(mem, geom + base + 0x10 * k)) for k in range(4)]


def terrain_capsule_core(mem, geom, out, capacity=500, *, query, edge_filter=None, nan_rule='sse', trace=None):
    """0x19cc160(tester, geom, out, capacity) with A = kind-6 terrain, B = capsule.

    query(tree_address, aabb_words, capacity) -> triangle ids (the native 0x1952b20);
    edge_filter(mem, shape, triangle, records_address, count) -> count (0x19974c0, mode 2).
    trace, when a list, receives (event, data) tuples for the harness."""
    r = nan_rule
    capacity &= 0xFFFFFFFF
    frame_a, frame_b = _rows(mem, geom, 0), _rows(mem, geom, 0x40)
    shape_a, shape_b = _u64(mem, geom + 0x80), _u64(mem, geom + 0x88)
    flag_filter, flag_keys = mem.view(geom + 0x92, 1)[0], mem.view(geom + 0x90, 1)[0]
    terrain = read_terrain_shape(mem, shape_a)
    mesh = terrain['mesh']
    h, radius = _u32(mem, shape_b + 0x40), _u32(mem, shape_b + 0x44)
    rel, p0, d, p1 = relative_capsule(frame_a, frame_b, h, r)
    box = capsule_bounds(h, radius, rel, r)
    qbox = query_bounds(box, terrain['scale'], r)
    total = ((3 * mesh['count']) & 0xFFFFFFFF) // 3
    first_cap = min(total, FIRST_QUERY_CAP)
    tris = list(query(mesh['tree'], qbox, first_cap))
    if trace is not None:
        trace.append(('query', (qbox, first_cap, len(tris))))
    if len(tris) == FIRST_QUERY_CAP:
        tris = list(query(mesh['tree'], qbox, total))
        if trace is not None:
            trace.append(('query', (qbox, total, len(tris))))
    seg = [p0, p1]
    written = 0
    for tri in tris:
        if written >= capacity:
            break
        tri &= 0xFFFF
        if not triangle_admitted(mem, terrain, shape_b, tri):
            continue
        block = triangle_block(triangle_vertices(mem, mesh, terrain['scale'], tri, r), r)
        group = _u16(mem, mesh['groups'] + 2 * tri)
        feature = (tri << 16) | group
        v0 = block['v'][0]
        dots = [mdot(block['n'], vsub(p, v0, r), r) for p in seg]
        here = out + RECORD_STRIDE * written
        if all_le(bc(0), vmul(dots[1], dots[0], r), 4):
            records = same_side_contacts(seg, p0, d, h, radius, dots, block, capacity - written, feature, r)
            path = 'same_side'
        else:
            rec = crossing_contact(seg, p0, d, radius, dots, block, feature, r)
            records = [] if rec is None else [rec]
            path = 'crossing'
        for i, rec in enumerate(records):
            mem.view(here + RECORD_STRIDE * i, RECORD_STRIDE)[:] = rec
        n = len(records)
        if trace is not None:
            trace.append((path, (tri, n)))
        if flag_filter:
            if terrain['mode'] == 1:
                n = backface_filter(mem, mesh, tri, here, n, r)
            if terrain['mode'] == 2:
                n = edge_filter(mem, shape_a, tri, here, n)
        if n:
            transform_records(mem, here, n, frame_a, r)
        written += n
    if flag_keys:
        written = key_pass(mem, out, written, r)
    return written


def capsule_terrain_tester(mem, geom, out, capacity=500, *, query, edge_filter=None, nan_rule='sse', trace=None,
                           lane3=0):
    """(4,6) slot 3, 0x198af50: swapped geom (frames and shapes exchanged), the (6,4) core,
    then 0x1994f60 over the returned records. Geom: frameA = capsule, frameB = terrain,
    +0x80 capsule shape, +0x88 terrain shape (as 0x18e0980 passes them)."""
    tmp = SWAP_GEOM_ADDRESS
    view = _Overlay(mem, tmp, swapped_geom(bytes(mem.view(geom, 0x93)), lane3))
    n = terrain_capsule_core(view, tmp, out, capacity, query=query, edge_filter=edge_filter,
                             nan_rule=nan_rule, trace=trace)
    flip_contact_records(mem, out, out + RECORD_STRIDE * n)
    return n
