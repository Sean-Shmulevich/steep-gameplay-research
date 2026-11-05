"""Narrow-phase capsule-grid tester: kind pairs (4,7) and (7,4).

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase capsule-grid tester" (static
reads of the (4,7) entry 0x198a910, the (7,4) entry and caller 0x19e0430, the per-triangle
cores 0x19e0000 and 0x19101e0, the segment-triangle test 0x1935ca0 and the capsule bounds
method 0x18c64a0). It composes the grid modules of "Grid triangle candidate enumeration",
"Terrain candidate collection and ownership", "Terrain profile admission", "Grid height
query"/"Connected preliminary grid contact", "Grid triangle vertex consumer boundary" and
"Complete grid record filter", and 0x1994f60 (engine.pose_contact_reverse). Native
comparison: analysis/command-executor-audit/check_pose_narrowphase_capsule_grid.py ->
native/snow_host/pose_narrowphase_capsule_grid_validation.json.

Recovered structure:

- 0x198a910 (vtable 0x29cb530 slot 3) is a swap wrapper. It builds a stack geom with the
  frames and shape pointers exchanged (flags +0x90..+0x92 copied, the (7,4) vtable
  0x29cb378 as the temporary tester), calls 0x19e0430, then 0x1994f60 over the returned
  records. This is the same pattern as 0x198b400 (sphere swap) and 0x198a780 (box/grid).
- 0x19e0430 works in terrain-local coordinates: full inverse of the terrain frame, the
  capsule frame relative to it, the capsule axis P0 = R*(0,-h,0), D = R*(0,2h,0),
  P1 = D + P0, local bounds from 0x18c64a0, optional preliminary height contact
  (geom+0x90; returns 1), candidate enumeration with the 128 retry, profile gate, then per
  admitted triangle (untransformed local vertices from 0x18c2c70) the core selected by the
  signed plane distances of P0 and P1: 0x19e0000 when 0 <= d1*d0 (all lanes), else
  0x19101e0. With geom+0x92 and resource+0x40 == 2 the new batch is filtered by 0x1996e50
  with an identity frame. The kept records are then transformed to world by the terrain
  frame (normal as a direction, +0x10 and +0x20 as points; only XYZ words are written).
  Candidates stop once the running count reaches the capacity (unsigned compare before
  every candidate).
- 0x19e0000 (same side, at most two records, honours its capacity argument
  capacity - count): each axis endpoint inside the triangle prism (three edge tests
  against -1e-5, unnormalised) and within r of the plane gives one record.
- 0x19101e0 (segment crosses the plane, at most one record, no capacity argument): when
  0x1935ca0 says the axis pierces the triangle the record uses the endpoint nearer the
  plane, depth -(|d| + r); otherwise the closest segment/edge pair over the three edges,
  depth |Ps - Qe| - r, written only when <= 0.

Static caller note: 0x18dd400 passes the same geom block (rbp-0x60) to the terrain wrapper
0x18e08a0 that reaches this tester, after writing +0x90 = 1 and +0x92 = 1 (0x18dd516,
0x18dd51a); so on that path the preliminary branch is armed and filtering depends only
on resource+0x40 == 2, whose live value is not established.

Records (in the (7,4) orientation, before the wrapper flips them): +0 normal, +0xc depth,
+0x10 point on the terrain side, +0x1c = 0, +0x20 point on the capsule side, +0x2c the
triangle id (the preliminary record has the height-query id).

Float32 lane semantics follow engine.pose_contact_payload_update (exact double then one
rounding, no FTZ/DAZ, default NaN 0xffc00000, two-NaN choice by nan_rule) and every lane
operation keeps the native operand order. The grid helpers reused here (bounds-to-cell
enumeration, height query, triangle vertices, record filter, profile gate) are float
models validated on finite inputs, so the whole tester is exact only where those inputs
are finite; the per-triangle cores (triangle_contacts and below) are lane exact.

Authored choices: Python owns the candidate buffer (native stack block or the 0x18c9140
allocation is not emulated); the runtime XYZ mask {-1,-1,-1,0} and the zero vector at
0x33368c0 are taken as initialised. Names are ours.
"""
import struct

from engine.pose_contact_payload_update import XYZ_MASK, _add, _mul, _sub, _to_bits, _to_float
from engine.pose_narrowphase_dispatch import _div, _le, _lt, _sqrt
from engine.pose_narrowphase_kind45 import (ABS, ONE, SIGN, TINY, bc, hsum, le_all, lt_all, mdot,
                                            shuf, vabs, vadd, vdiv, vmask, vmul, vsqrt, vsub, vxor)

RECORD_STRIDE = 0x30
HALF = 0x3F000000            # 0x1df31d4, 0.5
FLT_MAX = 0x7F7FFFFF         # 0x1eba000 (four lanes)
NORMAL_TINY = 0x358637BD     # 0x1e93b80, 1e-6
PLANE_THRESHOLD = TINY       # 0x1e252b0, 1e-5, stored at triangle block +0x70
IDENTITY_FRAME = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 0.0]]

CAPSULE_GRID_ENTRY_RVA = 0x198A910     # (4,7), vtable 0x29cb530
GRID_CAPSULE_ENTRY_RVA = 0x19E0430     # (7,4), vtable 0x29cb378
SAME_SIDE_CORE_RVA = 0x19E0000
CROSSING_CORE_RVA = 0x19101E0
PIERCE_TEST_RVA = 0x1935CA0
CAPSULE_BOUNDS_RVA = 0x18C64A0


def _f(bits):
    return _to_float(bits)


# --- 0x19e0430 prologue: inverse terrain frame, relative capsule frame, axis ----------

def relative_capsule_frame(terrain, capsule, r):
    """Rows R0, R1, R2, Rt of the capsule frame in terrain coordinates (masked rows in)."""
    a0, a1, a2, at = terrain
    b0, b1, b2, bt = capsule
    a2_yzx, a1_zxy = shuf(a2, a2, 0xC9), shuf(a1, a1, 0xD2)
    a2_zxy, a1_yzx = shuf(a2, a2, 0xD2), shuf(a1, a1, 0xC9)
    t0 = vmul(a2_yzx, a1_zxy, r)
    c0 = vsub(vmul(a2_zxy, a1_yzx, r), t0, r)
    det = hsum(vmask(vmul(a0, c0, r)), r)
    inv = vmask(vdiv(bc(ONE), det, r))
    a0_yzx, a0_zxy = shuf(a0, a0, 0xC9), shuf(a0, a0, 0xD2)
    s0 = vmul(vsub(vmul(a2_zxy, a1_yzx, r), vmul(a2_yzx, a1_zxy, r), r), inv, r)
    c1 = vsub(vmul(a0_zxy, a2_yzx, r), vmul(a2_zxy, a0_yzx, r), r)
    s1 = vmul(inv, c1, r)
    c2 = vsub(vmul(a0_yzx, a1_zxy, r), vmul(a1_yzx, a0_zxy, r), r)
    s2 = vmul(inv, c2, r)
    i0 = [s0[0], s1[0], s2[0], 0]
    i1 = [s0[1], s1[1], s2[1], 0]
    i2 = [s0[2], s1[2], s2[2], 0]
    nt = vxor(at, bc(SIGN))
    inv_t = vadd(vmul(i2, bc(nt[2]), r), vadd(vmul(i1, bc(nt[1]), r), vmul(i0, bc(nt[0]), r), r), r)
    rt = vadd(vmul(i2, bc(bt[2]), r),
              vadd(vadd(vmul(i0, bc(bt[0]), r), inv_t, r), vmul(i1, bc(bt[1]), r), r), r)
    rows = []
    for b in (b0, b1, b2):
        rows.append(vadd(vmul(i2, bc(b[2]), r),
                         vadd(vmul(i1, bc(b[1]), r), vmul(bc(b[0]), i0, r), r), r))
    return rows + [rt]


def capsule_axis(rel, half, r):
    """P0 = R*(0,-h,0) as a point, D = R*(0,2h,0) as a direction, P1 = D + P0."""
    r0, r1, r2, rt = rel
    p0 = vadd(vmul(bc(0), r2, r), vadd(vadd(vmul(bc(0), r0, r), rt, r),
                                       vmul(bc(half ^ SIGN), r1, r), r), r)
    two_h = _add(half, half, r)
    d = vadd(vmul(bc(0), r2, r), vadd(vmul(bc(two_h), r1, r), vmul(bc(0), r0, r), r), r)
    return p0, d, vadd(d, p0, r)


def capsule_local_bounds(half, radius, rel, r):
    """0x18c64a0(capsule, out, frame): six lane bits low xyz, high xyz (scalar SSE)."""
    ext = [_add(_mul(half, rel[1][j], r) & ABS, radius, r) for j in range(3)]
    low = [_sub(rel[3][j], ext[j], r) for j in range(3)]
    high = [_add(ext[j], rel[3][j], r) for j in range(3)]
    return low + high


# --- per-triangle block -------------------------------------------------------------

def triangle_block(a, b, c, r):
    """The caller's block at rbp+0x230: A, B, C, AB, BC, CA, unit normal, 1e-5."""
    ab, bcv, ca = vsub(b, a, r), vsub(c, b, r), vsub(a, c, r)
    raw = vsub(vmul(shuf(bcv, bcv, 0xD2), shuf(ab, ab, 0xC9), r),
               vmul(shuf(bcv, bcv, 0xC9), shuf(ab, ab, 0xD2), r), r)
    length = vsqrt(hsum(vmask(vmul(raw, raw, r)), r))
    n = vmul(raw, vdiv(bc(ONE), length, r), r)
    return [a, b, c, ab, bcv, ca, n, bc(PLANE_THRESHOLD)]


def _record(n, depth, pa, pb, triangle_id):
    return struct.pack('<12I', n[0], n[1], n[2], depth, pa[0], pa[1], pa[2], 0,
                       pb[0], pb[1], pb[2], triangle_id & 0xFFFFFFFF)


def endpoint_inside(tri, e, r):
    """0x19e0000 first loop: E against the three edge planes cross(n, edge), >= -1e-5."""
    a, b, c, ab, bcv, ca, n, thr = tri
    neg = vxor(bc(SIGN), thr)
    e1 = vsub(vmul(shuf(n, n, 0xC9), shuf(ab, ab, 0xD2), r),
              vmul(shuf(ab, ab, 0xC9), shuf(n, n, 0xD2), r), r)
    if not le_all(neg, mdot(vsub(e, a, r), e1, r)):
        return False
    e2 = vsub(vmul(shuf(bcv, bcv, 0xD2), shuf(n, n, 0xC9), r),
              vmul(shuf(n, n, 0xD2), shuf(bcv, bcv, 0xC9), r), r)
    if not le_all(neg, mdot(vsub(e, b, r), e2, r)):
        return False
    e3 = vsub(vmul(shuf(ca, ca, 0xD2), shuf(n, n, 0xC9), r),
              vmul(shuf(ca, ca, 0xC9), shuf(n, n, 0xD2), r), r)
    return le_all(neg, mdot(vsub(e, c, r), e3, r))


def same_side_contacts(endpoints, half, radius, dists, tri, capacity, triangle_id, r):
    """0x19e0000: returns the list of records (len <= min(2, capacity))."""
    a, n = tri[0], tri[6]
    rad = bc(radius)
    inside = [endpoint_inside(tri, e, r) for e in endpoints]
    if not any(inside):
        return []
    neg_n = vxor(bc(SIGN), n)
    s = vadd(dists[1], dists[0], r)
    big_n = [neg_n[k] if _lt(s[k], 0) else n[k] for k in range(4)]
    length = _add(half, half, r)
    l2 = bc(_mul(length, length, r))
    cos_max = vdiv(bc(length), vsqrt(vadd(l2, vmul(rad, rad, r), r)), r)
    out = []
    for i in range(2):
        if len(out) >= (capacity & 0xFFFFFFFF):
            break
        if not inside[i]:
            continue
        e, o = endpoints[i], endpoints[1 - i]
        de = hsum(vmask(vmul(vsub(e, a, r), n, r)), r)
        diff = vsub(o, e, r)
        dd = hsum(vmask(vmul(diff, diff, r)), r)
        q = vsub(e, vmul(de, n, r), r)
        u = vmul(diff, vdiv(bc(ONE), vsqrt(dd), r), r)
        c = vxor(hsum(vmask(vmul(u, big_n, r)), r), bc(SIGN))
        cl = vmul(c, bc(length), r)
        if le_all(c, bc(0)):
            push = rad
        elif le_all(c, cos_max):
            push = vdiv(rad, vsqrt(vsub(bc(ONE), vmul(c, c, r), r)), r)
        else:
            inner = vadd(vsub(vmul(rad, rad, r), l2, r), vmul(cl, cl, r), r)
            push = vadd(vsqrt(inner), cl, r)
        qe = vsub(q, e, r)
        depth = vsub(vsqrt(hsum(vmask(vmul(qe, qe, r)), r)), rad, r)
        if le_all(depth, bc(0)):
            pb = vsub(e, vmul(push, big_n, r), r)
            out.append(_record(big_n, depth[0], q, pb, triangle_id))
    return out


def segment_pierces_triangle(tri, p0, d, r):
    """0x1935ca0(tri, &{P0, D}, &t): (hit, t lanes). t is written only past the u/v tests."""
    a, b, c, thr = tri[0], tri[1], tri[2], tri[7]
    ab = vsub(b, a, r)
    ac = vsub(c, a, r)
    dn = vmul(d, vdiv(bc(ONE), vsqrt(hsum(vmask(vmul(d, d, r)), r)), r), r)
    p = vsub(vmul(shuf(dn, dn, 0xC9), shuf(ac, ac, 0xD2), r),
             vmul(shuf(ac, ac, 0xC9), shuf(dn, dn, 0xD2), r), r)
    det = mdot(p, ab, r)
    if all(not _is_nan_bits(x) and _f(x) == 0.0 for x in det):
        return False, None
    tv = vsub(p0, a, r)
    inv = vmask(vdiv(bc(ONE), det, r))
    neg = vxor(bc(SIGN), thr)
    u = vmul(mdot(tv, p, r), inv, r)
    if lt_all(u, neg):
        return False, None
    upper = vadd(thr, bc(ONE), r)
    if lt_all(upper, u):
        return False, None
    q = vsub(vmul(shuf(tv, tv, 0xC9), shuf(ab, ab, 0xD2), r),
             vmul(shuf(ab, ab, 0xC9), shuf(tv, tv, 0xD2), r), r)
    v = vmul(mdot(q, dn, r), inv, r)
    if lt_all(v, neg):
        return False, None
    if lt_all(upper, vadd(v, u, r)):
        return False, None
    t = vmul(mdot(q, ac, r), inv, r)
    dd = hsum(vmask(vmul(d, d, r)), r)
    hit = le_all(bc(0), t) and le_all(vmul(t, t, r), dd)
    return hit, t


def _is_nan_bits(x):
    return (x & 0x7F800000) == 0x7F800000 and (x & 0x7FFFFF) != 0


def _segment_edge(p0, d, a_vec, v, evec, r):
    """One edge of 0x19101e0's closest-pair loop: (Ps, Qe, dist2 lanes)."""
    ra = vsub(p0, v, r)
    e = mdot(evec, evec, r)
    b = mdot(d, evec, r)
    c = mdot(d, ra, r)
    f = mdot(ra, evec, r)
    denom = vsub(vmul(e, a_vec, r), vmul(b, b, r), r)
    tol = vmul(a_vec, bc(PLANE_THRESHOLD), r)
    if le_all(vabs(denom), tol):
        s_num, s_den, t_num, t_den = bc(0), e, f, e
    else:
        s_num = vsub(vmul(f, b, r), vmul(c, e, r), r)
        t_num = vsub(vmul(f, a_vec, r), vmul(c, b, r), r)
        s_den, t_den = denom, denom
        if lt_all(s_num, bc(0)):
            s_num, t_num, t_den = bc(0), f, e
        elif lt_all(denom, s_num):
            t_num, s_num, t_den = vadd(f, b, r), denom, e
    neg_c = vxor(bc(SIGN), c)
    if lt_all(t_num, bc(0)):
        t = bc(0)
        if lt_all(neg_c, bc(0)):
            s = bc(0)
        elif lt_all(a_vec, neg_c):
            s = bc(ONE)
        else:
            s = vdiv(neg_c, a_vec, r)
    elif lt_all(t_den, t_num):
        t = bc(ONE)
        bmc = vadd(b, neg_c, r)
        if lt_all(bmc, bc(0)):
            s = bc(0)
        elif lt_all(a_vec, bmc):
            s = bc(ONE)
        else:
            s = vdiv(bmc, a_vec, r)
    else:
        s = vdiv(s_num, s_den, r)
        t = vdiv(t_num, t_den, r)
    te = vmul(t, evec, r)
    sd = vmul(s, d, r)
    gap = vsub(vadd(sd, ra, r), te, r)
    return vadd(sd, p0, r), vadd(te, v, r), hsum(vmask(vmul(gap, gap, r)), r)


def _normal_or_plane(diff, n, r):
    if le_all(vabs(diff), bc(NORMAL_TINY)):
        return list(n)
    return vmul(diff, vdiv(bc(ONE), vsqrt(hsum(vmask(vmul(diff, diff, r)), r)), r), r)


def crossing_contacts(endpoints, segment, radius, dists, tri, triangle_id, r):
    """0x19101e0: returns ([record] or [], path name)."""
    rad = bc(radius)
    n = tri[6]
    hit, _ = segment_pierces_triangle(tri, segment[0], segment[1], r)
    if hit:
        best, sel, proj = bc(FLT_MAX), bc(0), bc(0)
        for k in range(2):
            sq = vmul(dists[k], dists[k], r)
            if lt_all(sq, best):
                best, sel = sq, endpoints[k]
                proj = vsub(endpoints[k], vmul(dists[k], n, r), r)
        diff = vsub(proj, sel, r)
        normal = _normal_or_plane(diff, n, r)
        dist = vsqrt(hsum(vmask(vmul(diff, diff, r)), r))
        depth = vsub(vxor(bc(SIGN), dist), rad, r)
        pb = vsub(sel, vmul(rad, normal, r), r)
        return [_record(normal, depth[0], proj, pb, triangle_id)], 'pierce'
    p0, d = segment
    a_vec = hsum(vmask(vmul(d, d, r)), r)
    best, ps_sel, qe_sel = bc(FLT_MAX), bc(0), bc(0)
    a, b, c, ab, bcv, ca = tri[:6]
    for v, evec in ((a, ab), (b, bcv), (c, ca)):
        ps, qe, dist2 = _segment_edge(p0, d, a_vec, v, evec, r)
        if lt_all(dist2, best):
            best, ps_sel, qe_sel = dist2, ps, qe
    normal = _normal_or_plane(vsub(ps_sel, qe_sel, r), n, r)
    dq = vsub(qe_sel, ps_sel, r)
    depth = vsub(vsqrt(hsum(vmask(vmul(dq, dq, r)), r)), rad, r)
    if not le_all(depth, bc(0)):
        return [], 'edge_separated'
    pb = vsub(ps_sel, vmul(rad, normal, r), r)
    return [_record(normal, depth[0], qe_sel, pb, triangle_id)], 'edge'


def triangle_contacts(vertices, axis, half, radius, capacity, triangle_id, nan_rule='sse'):
    """One admitted triangle of 0x19e0430: local vertices (three 4-lane bit rows) and the
    local axis (P0, D, P1). Returns (records, path); capacity is what remains."""
    r = nan_rule
    p0, d, p1 = axis
    tri = triangle_block(*vertices, r)
    a, n = tri[0], tri[6]
    d1 = mdot(n, vsub(p1, a, r), r)
    d0 = mdot(n, vsub(p0, a, r), r)
    if le_all(bc(0), vmul(d1, d0, r)):
        return same_side_contacts([p0, p1], half, radius, [d0, d1], tri, capacity,
                                  triangle_id, r), 'same_side'
    return crossing_contacts([p0, p1], (p0, d), radius, [d0, d1], tri, triangle_id, r)


def _world_records(records, start, count, terrain, r):
    """Caller loop at 0x19e0c40: XYZ of normal, +0x10 and +0x20 through the terrain frame."""
    b0, b1, b2, t = terrain
    for i in range(start, start + count):
        o = i * RECORD_STRIDE
        nrm = vmask(list(struct.unpack_from('<4I', records, o)))
        pa = vmask(list(struct.unpack_from('<4I', records, o + 0x10)))
        pb = vmask(list(struct.unpack_from('<4I', records, o + 0x20)))
        wn = vadd(vmul(b2, bc(nrm[2]), r), vadd(vmul(b1, bc(nrm[1]), r), vmul(b0, bc(nrm[0]), r), r), r)
        wa = vadd(vmul(b2, bc(pa[2]), r), vadd(vadd(vmul(b0, bc(pa[0]), r), t, r),
                                               vmul(b1, bc(pa[1]), r), r), r)
        wb = vadd(vmul(b2, bc(pb[2]), r), vadd(vadd(vmul(bc(pb[0]), b0, r), t, r),
                                               vmul(b1, bc(pb[1]), r), r), r)
        struct.pack_into('<3I', records, o, *wn[:3])
        struct.pack_into('<3I', records, o + 0x10, *wa[:3])
        struct.pack_into('<3I', records, o + 0x20, *wb[:3])


def emit_grid_capsule_contacts(output, capacity, resource, samples, terrain_rows, capsule_rows,
                               half, radius, terrain_profiles, capsule_profile, *, profiles,
                               preliminary=False, filter_enabled=False, nan_rule='sse',
                               trace=None):
    """0x19e0430 with grid first. Rows are 4-lane bit lists (masked here); half/radius are
    the bits at capsule+0x40/+0x44. Returns the native return value (see the preliminary
    note in LINK_SOLVER.md). trace, when a dict, receives path counters."""
    from engine.pose_grid_candidates import collect_grid_triangle_candidates
    from engine.pose_grid_cell import grid_triangle_vertices
    from engine.pose_grid_contact_filter import filter_grid_records
    from engine.pose_grid_height_contact import query_sampled_grid_contact
    from engine.pose_grid_profile_gate import grid_triangle_profile_gate
    r = nan_rule
    capacity &= 0xFFFFFFFF
    terrain = [vmask(list(row)) for row in terrain_rows]
    capsule = [vmask(list(row)) for row in capsule_rows]
    rel = relative_capsule_frame(terrain, capsule, r)
    axis = capsule_axis(rel, half, r)
    bounds = capsule_local_bounds(half, radius, rel, r)
    trace = trace if trace is not None else {}

    def bump(key):
        trace[key] = trace.get(key, 0) + 1
    if preliminary:
        center = [_f(_mul(_add(bounds[j + 3], bounds[j], r), HALF, r)) for j in range(3)]
        frame = [[_f(x) for x in row[:3]] for row in terrain]
        if len(output) < RECORD_STRIDE and capacity:
            raise ValueError('Record storage required')
        if query_sampled_grid_contact(resource, samples, frame, center, _f(radius),
                                      output if capacity else None):
            bump('preliminary')
            return 1
    ids =collect_grid_triangle_candidates(resource, [_f(x) for x in bounds])
    if ids['retried']:
        bump('candidate_retry')
    total = 0
    for triangle in ids['ids']:
        if total >= capacity:
            break
        _, admitted = grid_triangle_profile_gate(terrain_profiles, capsule_profile, triangle,
                                                 profiles=profiles)
        if not admitted:
            bump('profile_rejected')
            continue
        vertices = [[_to_bits(x) for x in v] for v in grid_triangle_vertices(resource, samples, triangle)]
        records, path = triangle_contacts(vertices, axis, half, radius, capacity - total,
                                          triangle, r)
        bump(path)
        count = len(records)
        if (total + count) * RECORD_STRIDE > len(output):
            raise ValueError('Complete output storage required')
        for k, rec in enumerate(records):
            output[(total + k) * RECORD_STRIDE:(total + k + 1) * RECORD_STRIDE] = rec
        if filter_enabled and struct.unpack_from('<I', resource, 0x40)[0] == 2:
            batch = memoryview(output)[total * RECORD_STRIDE:]
            kept = filter_grid_records(resource, samples, IDENTITY_FRAME, triangle, batch, count)
            trace['filtered_out'] = trace.get('filtered_out', 0) + count - kept
            count = kept
        _world_records(output, total, count, terrain, r)
        total += count
    return total


# --- flat-memory bindings ------------------------------------------------------------

def _rows(raw):
    return [list(struct.unpack_from('<4I', raw, 16 * k)) for k in range(4)]


def read_grid_resource(mem, grid):
    """Resource bytes, float samples and the profile dictionaries from flat memory."""
    resource = bytes(mem.view(grid, 0xB8))
    width, height = struct.unpack_from('<2H', resource, 0x68)
    cw, ch = struct.unpack_from('<2H', resource, 0x9C)
    sp = struct.unpack_from('<Q', resource, 0x48)[0]
    samples = list(struct.unpack('<%df' % (width * height), bytes(mem.view(sp, 4 * width * height))))
    mp, tp, default = struct.unpack_from('<Q', resource, 0xB0)[0], \
        struct.unpack_from('<Q', resource, 0xA0)[0], struct.unpack_from('<Q', resource, 0x20)[0]
    mapping = None if not mp else list(bytes(mem.view(mp, cw * ch)))
    table = []
    if mapping is not None:
        table = list(struct.unpack('<%dQ' % (max(mapping) + 1), bytes(mem.view(tp, 8 * (max(mapping) + 1)))))
    return resource, samples, dict(default20=default, mapb0=mapping, tablea0=table)


def _profile(mem, token):
    return dict(mask48=mem.get('<Q', token + 0x48), mask50=mem.get('<Q', token + 0x50))


def _output_size(resource, capacity):
    cw, ch = struct.unpack_from('<2H', resource, 0x9C)
    return RECORD_STRIDE * max(1, min(capacity & 0xFFFFFFFF, 4 * cw * ch))


def grid_capsule_tester(mem, geom, out, capacity=500, *, nan_rule='sse', trace=None, swapped=None):
    """0x19e0430(tester, geom, out, capacity) over flat memory; returns the count.

    swapped: optional (rows A, rows B, shape A, shape B) already exchanged by the wrapper.
    """
    raw = bytes(mem.view(geom, 0x93))
    if swapped is None:
        rows_a, rows_b = _rows(raw[0:0x40]), _rows(raw[0x40:0x80])
        grid, capsule = struct.unpack_from('<QQ', raw, 0x80)
    else:
        rows_a, rows_b, grid, capsule = swapped
    preliminary, filtering = raw[0x90] != 0, raw[0x92] != 0
    resource, samples, terrain_profiles = read_grid_resource(mem, grid)
    half = mem.get('<I', capsule + 0x40)
    radius = mem.get('<I', capsule + 0x44)
    capsule_token = mem.get('<Q', capsule + 0x20)
    tokens = {capsule_token, terrain_profiles['default20']} | set(terrain_profiles['tablea0'])
    profiles = {t: _profile(mem, t) for t in tokens if t}
    output = mem.view(out, _output_size(resource, capacity))
    return emit_grid_capsule_contacts(output, capacity, resource, samples, rows_a, rows_b, half, radius,
                                      terrain_profiles, dict(default20=capsule_token),
                                      profiles=profiles, preliminary=preliminary,
                                      filter_enabled=filtering, nan_rule=nan_rule, trace=trace)


def capsule_grid_tester(mem, geom, out, capacity=500, *, nan_rule='sse', trace=None):
    """0x198a910: (4,7) swap wrapper. Exchanges frames and shapes, runs 0x19e0430 with the
    original capacity, then 0x1994f60 over [out, out + 0x30 n) (normal sign flip, +0x10 and
    +0x20 swapped; depth, +0x1c and +0x2c kept)."""
    from engine.pose_contact_reverse import reverse_contact_records
    raw = bytes(mem.view(geom, 0x93))
    shape_a, shape_b = struct.unpack_from('<QQ', raw, 0x80)
    swapped = (_rows(raw[0x40:0x80]), _rows(raw[0:0x40]), shape_b, shape_a)
    n = grid_capsule_tester(mem, geom, out, capacity, nan_rule=nan_rule, trace=trace, swapped=swapped)
    resource = bytes(mem.view(shape_b, 0xB8))
    reverse_contact_records(mem.view(out, _output_size(resource, capacity)), 0, n)
    return n
