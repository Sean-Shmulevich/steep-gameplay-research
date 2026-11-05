"""Kind-6 mode-2 neighbourhood record filter: 0x19974c0 with 0x1996280 (vertex fan) and
0x1995fa0 (edge test).

Evidence: docs/reconstruction/LINK_SOLVER.md "Kind-6 tree query and mode-2 neighbourhood filter"
(static reads of 0x19974c0, 0x1996280, 0x1995fa0 and the call at 0x19cca71) and "Narrow-phase
capsule-terrain (kind 6) tester" (shape/mesh layout). Native comparison:
analysis/command-executor-audit/check_pose_terrain6_leaves.py
-> native/snow_host/pose_terrain6_leaves_validation.json.

Recovered local behaviour (names are ours):

- 0x19974c0(shape, frame, triangle, records, count) -> count. The tester (0x19cc160) passes
  the identity rows at rbp+0x260 (0x1e25250, 0x1e25270, 0x1df4060, translation 0) and the
  freshly written local records. count == 0 or mesh+0xa8 == 0 returns count untouched.
- Same skeleton as the kind-7 filter 0x1996e50 ("Complete grid record filter"): scaled
  triangle V0..V2 (shape+0x70 scale x mesh+0x30 vertex, u16 indices at mesh+0x40),
  N = (V1-V0) x (V2-V0), inv = 1/(N.N); per record P = ((r0*x + t) + r1*y) + r2*z from
  +0x10, D = (r1*y + r0*x) + r2*z from +0; barycentric WA, WB, WC = ((Vk-P) x (Vl-P)).N *
  inv; branch order vertex A/B/C (W > 0.9999), then edge AB (WC < 0.0001), BC (WA), CA
  (WB); rejection copies the last record over the current one and retries the slot.
- Differences from kind 7: (1) before any branch, a record whose D.N < -1e-5 (all three
  lanes; 0x1e252b0 negated) is rejected; (2) the vertex test walks the triangle fan
  through the edge tables: start with the vertex after Vj in this triangle, then cross
  edge slot 3*cur + pos(v) of the current triangle (u32 at mesh+0xb8 -> u16 pair at
  mesh+0xa8 + 4*edge; take the entry that is not the current triangle) and use the
  vertex following v in the next triangle (position 0 when v is absent), until the pair
  gives 0xffff or the starting triangle; rejects as soon as normalize(Nb - Vj).D > 1e-5;
  (3) the edge test (j, VA, VB) uses the opposite vertex V(j+2) as N0 and, across edge
  slot 3*t + (j+1)%3 (not j), the vertex following VA in the neighbour (else its first
  vertex) as N1 (N1 = N0 when the pair gives 0xffff; no starting-triangle check); U and
  V are always normalised (kind 7 keeps near-zero vectors), then
  first = D.((E x U) x E), second = D.(E x (V x E)) against 1e-5.
- Operand orders follow the code (scale*vertex, except vertex*scale in 0x19974c0's V1.x and
  in 0x1995fa0's x lanes); each lane operation rounds once (engine.pose_contact_payload_update).

Authored: the names, the explicit `frame` argument (identity by default, as the tester
passes) and the `service` binding to the tester signature. The native fan walk has no
iteration bound; the model raises after FAN_LIMIT steps instead of hanging.
"""
import struct

from engine.pose_narrowphase_capsule_terrain6 import (
    IDENTITY_ROWS, RECORD_STRIDE, SIGN, ONE, TOL_PARALLEL, _copy_record, _u16, _u32, _u64, _vec,
    all_lt, bc, hsum, mdot, vadd, vdiv, vmask, vmul, vsqrt, vsub, vxor, yzx, zxy,
)
from engine.pose_contact_payload_update import _mul

FILTER_RVA = 0x19974C0
VERTEX_FAN_RVA = 0x1996280
EDGE_TEST_RVA = 0x1995FA0
UPPER = 0x3F7FF972        # 0x29cb630, 0.9999
LOWER = 0x38D1B717        # 0x1e93ba0, 0.0001
THRESHOLD = TOL_PARALLEL  # 0x1e252b0, 1e-5 (stored at rbp-0x70 and passed to both helpers)
BACK_THRESHOLD = TOL_PARALLEL  # the same constant, sign-flipped for the D.N gate
EDGE_SLOT_STEP = 1        # 0x1995fa0 reads the edge-table slot (j + 1) % 3
NO_TRIANGLE = 0xFFFF
FAN_LIMIT = 1 << 20
IDENTITY_FRAME = tuple(list(row) for row in IDENTITY_ROWS) + ([0, 0, 0, 0],)


def read_mode2_mesh(mem, shape):
    mesh = _u64(mem, shape + 0x48)
    return dict(vertices=_u64(mem, mesh + 0x30), indices=_u64(mem, mesh + 0x40),
                pairs=_u64(mem, mesh + 0xA8), edges=_u64(mem, mesh + 0xB8),
                scale=[_u32(mem, shape + 0x70 + 4 * k) for k in range(3)])


def _index(mem, m, slot):
    return _u16(mem, m['indices'] + 2 * (slot & 0xFFFFFFFF))


def _vertex_words(mem, m, v):
    a = m['vertices'] + 12 * v
    return [_u32(mem, a + 4 * k) for k in range(3)]


def scaled(mem, m, v, order, r):
    """Scaled vertex; order[k] True = scale * vertex (else vertex * scale). Lane 3 = 0."""
    p, s = _vertex_words(mem, m, v), m['scale']
    return [_mul(s[k], p[k], r) if order[k] else _mul(p[k], s[k], r) for k in range(3)] + [0]


SCALE_FIRST = (True, True, True)
EDGE_ORDER = (False, True, True)          # 0x1995fa0 and 0x19974c0's V1: x is vertex * scale


def _neighbour(mem, m, edge_slot, current):
    edge = _u32(mem, m['edges'] + 4 * (edge_slot & 0xFFFFFFFF))
    t0 = _u16(mem, m['pairs'] + 4 * edge)
    return _u16(mem, m['pairs'] + 4 * edge + 2) if t0 == current else t0


def _normalised(v, r):
    """ones / sqrtps(mdot(v, v)) (the reciprocal length in every lane); callers keep the multiply order."""
    return vdiv(bc(ONE), vsqrt(mdot(v, v, r)), r)


def _vertex_rejects(nb, v, d, thr, r):
    diff = vsub(vmask(nb), v, r)
    dot = mdot(vmul(_normalised(diff, r), diff, r), d, r)
    return all_lt(thr, dot, 3)


def vertex_fan_test(mem, m, tri, j, v, d, r, *, thr=None, trace=None):
    """0x1996280(ctx, j, &Vj, &D) -> True to reject."""
    thr = thr or bc(THRESHOLD)
    tri &= 0xFFFFFFFF
    base = (3 * tri) & 0xFFFFFFFF
    vid = _index(mem, m, base + j)
    nxt_pos = (j + 1) % 3
    nb = scaled(mem, m, _index(mem, m, base + nxt_pos), SCALE_FIRST, r)
    if _vertex_rejects(nb, v, d, thr, r):
        return True
    cur = tri
    for _ in range(FAN_LIMIT):
        slot = (base + (nxt_pos + 2) % 3) & 0xFFFFFFFF
        n = _neighbour(mem, m, slot, cur)
        if n == NO_TRIANGLE or n == tri:
            return False
        cur, base = n, 3 * n
        if _index(mem, m, base) == vid:
            nxt_pos = 1
        elif _index(mem, m, base + 1) == vid:
            nxt_pos = 2
        else:
            nxt_pos = 0
        if trace is not None:
            trace.append(('fan', cur))
        nb = scaled(mem, m, _index(mem, m, base + nxt_pos), SCALE_FIRST, r)
        if _vertex_rejects(nb, v, d, thr, r):
            return True
    raise RuntimeError('vertex fan did not terminate (native loop has no bound)')


def edge_test(mem, m, tri, j, va, vb, d, r, *, thr=None):
    """0x1995fa0(ctx, j, &VA, &VB, &D) -> True to reject."""
    thr = thr or bc(THRESHOLD)
    tri &= 0xFFFFFFFF
    base = (3 * tri) & 0xFFFFFFFF
    start = _index(mem, m, base + j)
    n0 = scaled(mem, m, _index(mem, m, base + (j + 2) % 3), EDGE_ORDER, r)
    n1 = n0
    other = _neighbour(mem, m, base + (j + EDGE_SLOT_STEP) % 3, tri)
    if other != NO_TRIANGLE:
        nb = 3 * other
        first = _index(mem, m, nb)
        if first == start:
            vi = _index(mem, m, nb + 1)
        elif _index(mem, m, nb + 1) == start:
            vi = _index(mem, m, nb + 2)
        else:
            vi = first
        n1 = scaled(mem, m, vi, EDGE_ORDER, r)
    e = vsub(va, vb, r)
    e = vmul(e, _normalised(e, r), r)
    u = vsub(vmask(n0), vb, r)
    u = vmul(u, _normalised(u, r), r)
    w = vsub(vmask(n1), va, r)
    w = vmul(w, _normalised(w, r), r)
    ez, ey = zxy(e), yzx(e)
    x = vsub(vmul(zxy(u), ey, r), vmul(yzx(u), ez, r), r)
    f = vsub(vmul(yzx(x), ez, r), vmul(ey, zxy(x), r), r)
    if all_lt(thr, mdot(d, f, r), 3):
        return True
    y = vsub(vmul(yzx(w), ez, r), vmul(ey, zxy(w), r), r)
    g = vsub(vmul(zxy(y), ey, r), vmul(yzx(y), ez, r), r)
    return all_lt(thr, mdot(d, g, r), 3)


def triangle_frame(mem, m, tri, r):
    """V0, V1, V2 (masked), edge normal N and inv = mask(ones / N.N) as 0x19974c0 builds them."""
    base = (3 * (tri & 0xFFFFFFFF)) & 0xFFFFFFFF
    v0 = scaled(mem, m, _index(mem, m, base), SCALE_FIRST, r)
    v1 = scaled(mem, m, _index(mem, m, base + 1), EDGE_ORDER, r)
    v2 = scaled(mem, m, _index(mem, m, base + 2), SCALE_FIRST, r)
    ab = vsub(v1, v0, r)
    ac = vsub(v2, v0, r)
    n = vsub(vmul(yzx(ab), zxy(ac), r), vmul(yzx(ac), zxy(ab), r), r)
    inv = vmask(vdiv(bc(ONE), mdot(n, n, r), r))
    return [v0, v1, v2], n, inv


def classify(p_rel, n, inv, r):
    """Barycentric weights (WA, WB, WC) of 0x19974c0 from A' = V0-P, B' = V1-P, C' = V2-P."""
    a, b, c = p_rel
    wa = vsub(vmul(yzx(b), zxy(c), r), vmul(yzx(c), zxy(b), r), r)
    wb = vsub(vmul(yzx(c), zxy(a), r), vmul(yzx(a), zxy(c), r), r)
    wc = vsub(vmul(yzx(a), zxy(b), r), vmul(yzx(b), zxy(a), r), r)
    return [vmul(hsum(vmask(vmul(w, n, r)), r), inv, r) for w in (wa, wb, wc)]


def neighbourhood_filter(mem, shape, tri, records, count, frame=IDENTITY_FRAME, *, nan_rule='sse',
                         trace=None):
    """0x19974c0: filter `count` 0x30-byte records at `records` in place; returns the count."""
    r = nan_rule
    count &= 0xFFFFFFFF
    if count == 0:
        return 0
    m = read_mode2_mesh(mem, shape)
    if m['pairs'] == 0:
        return count
    rows = [list(x) for x in frame]
    verts, n, inv = triangle_frame(mem, m, tri, r)
    neg_thr = vxor(bc(BACK_THRESHOLD), bc(SIGN))
    upper, lower = bc(UPPER), bc(LOWER)
    i = 0
    while i < count:
        rec = records + RECORD_STRIDE * i
        p = vmask(_vec(mem, rec + 0x10))
        pw = vadd(vmul(rows[2], bc(p[2]), r),
                  vadd(vadd(vmul(rows[0], bc(p[0]), r), rows[3], r), vmul(rows[1], bc(p[1]), r), r), r)
        rel = [vsub(v, pw, r) for v in verts]
        wa, wb, wc = classify(rel, n, inv, r)
        dr = vmask(_vec(mem, rec))
        d = vadd(vmul(rows[2], bc(dr[2]), r),
                 vadd(vmul(rows[1], bc(dr[1]), r), vmul(rows[0], bc(dr[0]), r), r), r)
        if all_lt(hsum(vmask(vmul(d, n, r)), r), neg_thr, 3):
            reject, path = True, 'back'
        elif all_lt(upper, wa, 3):
            reject, path = vertex_fan_test(mem, m, tri, 0, verts[0], d, r), 'vertex0'
        elif all_lt(upper, wb, 3):
            reject, path = vertex_fan_test(mem, m, tri, 1, verts[1], d, r), 'vertex1'
        elif all_lt(upper, wc, 3):
            reject, path = vertex_fan_test(mem, m, tri, 2, verts[2], d, r), 'vertex2'
        elif all_lt(wc, lower, 3):
            reject, path = edge_test(mem, m, tri, 0, verts[0], verts[1], d, r), 'edge0'
        elif all_lt(wa, lower, 3):
            reject, path = edge_test(mem, m, tri, 1, verts[1], verts[2], d, r), 'edge1'
        elif all_lt(wb, lower, 3):
            reject, path = edge_test(mem, m, tri, 2, verts[2], verts[0], d, r), 'edge2'
        else:
            reject, path = False, 'interior'
        if trace is not None:
            trace.append((path, reject))
        if reject:
            count -= 1
            _copy_record(mem, rec, records + RECORD_STRIDE * count)
        else:
            i += 1
    return count


def service(*, nan_rule='sse', traces=None):
    """Bind to the tester's `edge_filter(mem, shape, triangle, records, count) -> count`."""
    def edge_filter(mem, shape, tri, records, count):
        tr = [] if traces is not None else None
        n = neighbourhood_filter(mem, shape, tri, records, count, nan_rule=nan_rule, trace=tr)
        if traces is not None:
            traces.append(tr)
        return n
    return edge_filter
