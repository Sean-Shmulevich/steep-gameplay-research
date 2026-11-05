"""Convex point query 0x18f0a70 (GJK-style distance from a point to a kind-5 hull) and the
hull support routine 0x1949480 / wrapper 0x19497c0.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase sphere testers and swap
wrapper" (the caller 0x19d58b0 and the service signature) and the static reads below of
the memory image (build-specific anchors; offsets are evidence anchors, not portable API
fields).

Call shape (from 0x19d58b0): 0x18f0a70(out, block, point, iterations) with block = the
0x48 bytes {frame rows b0, b1, b2, t (4 lanes each), hull shape pointer}, point = a 4-lane
vector read unmasked, iterations = 16 from that caller. out receives three 4-lane rows:
+0x00 distance (broadcast), +0x10 closest point on the hull (world), +0x20 the matching
point-side combination. The model returns (dist, on_hull, on_point) as bit lists, the
`point_query` service shape used by engine.pose_narrowphase_sphere.

Algorithm (recovered order; names are ours):
- Simplex of up to four entries {vertex index, 0, s (world hull point), P (the query
  point), w = P - s, weight (4 lanes)}. It starts with vertex 0 transformed to world,
  weight 1. The previous squared distance starts at |w0|^2.
- Each iteration (at most `iterations`; none when iterations <= 0):
  1. Direction by simplex size: 1 -> -w0; 2 -> ((e x -w0) x e) with e = w1 - w0 written as
     two lane-shuffled cross products; 3 -> n = (w1-w0) x (w2-w0), kept when n.w0 < 0 else
     negated. If |d|^2 < 2^-46 (0x29ca860) the query stops.
  2. Support: the local direction is the frame rows dotted with -d (haddps pair order),
     masked; 0x1949480 returns a vertex index; the vertex is loaded with a 16-byte movups
     (12-byte stride), masked and transformed: ((t + x*b0) + y*b1) + z*b2.
  3. The simplex (count, all four entries) is saved. If the index is in the "visited"
     list the query stops. The visited list holds the indices of the simplex as it was
     right after the previous addition (before reduction); it is empty on the first
     iteration, so vertex 0 can be added again once.
  4. The entry is appended and the visited list refreshed; then the region solver for
     2, 3 or 4 points (Voronoi-region tests on dot products of edge vectors and cross
     products, newest point last) keeps the closest feature, reorders entries and sets
     barycentric weights = (1 / denominator, masked) * numerator. Three degenerate
     exits keep the reduced count and the previous weights and stop the query:
     segment |e.e| <= static 0x3336a30, triangle |n.n| <= static 0x3336a50,
     tetrahedron |signed volume| <= static 0x3336a70 (all three 1e-7 x4 after their
     function-local initialisers 0x29ca870 / 0x29ca870 / scalar 0x1e4a8b8 broadcast).
  5. Count 4 (point inside the hull) stops the query. Otherwise v = sum weight_i * w_i
     (count 1: v = w0 without weight) and |v|^2 is compared with 0.999999 (0x29ca880,
     0x3f7fffef) times the previous value: when 0.999999*prev <= |v|^2 the simplex saved
     in step 3 is restored and the query stops; else prev = |v|^2 and the loop continues.
- Output by final count: 1 -> (s0, P0); 2/3 -> (sum s_i*wt_i, sum P_i*wt_i); 4 -> both
  rows equal sum s_i*wt_i (the point is inside); 0 or > 4 would give zeros (unreached).
  dist = sqrt(haddps((on_point - on_hull)^2 masked)) on all four lanes.

Support routine 0x1949480(shape, dir3) (dir3 = three floats copied by 0x19497c0):
- shape+0xc0 == 0: brute force over indices 0 .. (u32 shape+0x48) - 2, dot =
  (y*vy + x*vx) + z*vz, strict greater-than (comiss; unordered never wins), first best
  kept, start value -FLT_MAX (0x1e4a918), index 0 when nothing wins. The hull
  constructor 0x1948780 stores +0x48 = n + 1 for n copied vertices and allocates n+1
  slots, and the clone path 0x1948e20 passes +0x48 - 1 back as n, so the scan covers
  exactly the n real vertices; the extra slot is padding (unwritten by the constructor)
  that keeps the 16-byte load of the last vertex in bounds. A field value 0 wraps to
  0xffffffff natively (unbounded scan); the model raises.
- shape+0xc0 != 0: cube-map lookup. s = (1/sqrt((x*x + y*y) + z*z)) * f32[+0xe8];
  cell = truncate(f32[+0xe8] + c*s) per axis (cvttss2si; NaN/overflow 0x80000000),
  clamped to >= 0 and then signed-min with u32[+0xe0]; slot = ((iz*E4 + iy)*E4 + ix)
  in 32-bit arithmetic with E4 = u32[+0xe4]; entry = u32 table[+0xc0][slot]. Even entry
  -> vertex entry>>1. Odd entry -> list at qword[+0xd0] + 4*(entry>>1): u32 items, vertex
  item>>1, scanned until an item with bit 0 set (inclusive), best by strict greater dot.

Float32 semantics follow engine.pose_contact_payload_update / pose_narrowphase_dispatch:
exact double then one rounding, no FTZ/DAZ, default NaN 0xffc00000, two-NaN choice by
`nan_rule` ('sse' manual, 'x87' emulator). Every lane operation keeps the native operand
order (destination first) because the two-NaN rule depends on it. cmpleps / cmpltps are
false on NaN; all tested quantities are haddps broadcasts, so the native all-lanes tests
reduce to one lane except the static thresholds (compared per lane). No rsqrtps/rcpps
occur in this routine (divps/sqrtps/sqrtss/divss only), so nothing here is
hardware-approximation dependent.

Supplied (not restated): the CRT thread-safe static initialisation (0x1c44fb0 /
0x1c44f50) - the model takes the three statics as parameters - and __chkstk 0x1c45120.

Authored choices: names, the trace hook, the Python exception for a zero vertex count and
the `statics` parameter. Nothing here claims equivalence with the original engine beyond
the validated fixtures.
"""
import math
import struct

from engine.pose_contact_payload_update import XYZ_MASK, _add, _mul, _sub
from engine.pose_narrowphase_dispatch import _div, _hadd_sum, _le, _lt, _sqrt

POINT_QUERY_RVA = 0x18F0A70
SUPPORT_RVA = 0x1949480
SUPPORT_WRAPPER_RVA = 0x19497C0
HULL_CONSTRUCTOR_RVA = 0x1948780
HULL_CLONE_RVA = 0x1948E20
LEAF_RVAS = {0x1927B60: 'broadcast', 0x1928540: 'mul', 0x1928630: 'mul-add', 0x19285B0: 'all-le',
             0x192A1C0: 'distance', 0x192A200: 'dot', 0x192A1F0: 'div', 0x1928C40: 'mask',
             0x193C310: 'abs-all-le', 0x193C5C0: 'reciprocal-mask', 0x19284A0: 'copy-entry',
             0x1928380: 'copy-simplex'}

SIGN = 0x80000000
ABS = 0x7FFFFFFF
ONE = 0x3F800000
MINUS_ONE = 0xBF800000
NEG_FLT_MAX = 0xFF7FFFFF            # RVA 0x1e4a918
DIRECTION_EPSILON = 0x28800000      # RVA 0x29ca860, 2^-46 (compared with |d|^2)
PROGRESS_FACTOR = 0x3F7FFFEF        # RVA 0x29ca880, 0.999999
STATIC_EPSILON = 0x33D6BF95         # 1e-7: 0x29ca870 (x4) and 0x1e4a8b8 (scalar)
DEFAULT_STATICS = ((STATIC_EPSILON,) * 4,) * 3   # 0x3336a30 segment, 0x3336a50 triangle, 0x3336a70 volume
INT_INDEFINITE = 0x80000000


# --- lane helpers --------------------------------------------------------------------

def _m(mask):
    return list(struct.unpack('<4I', mask))


def _bc(x):
    return [x, x, x, x]


def _vadd(a, b, r): return [_add(x, y, r) for x, y in zip(a, b)]
def _vsub(a, b, r): return [_sub(x, y, r) for x, y in zip(a, b)]
def _vmul(a, b, r): return [_mul(x, y, r) for x, y in zip(a, b)]
def _vand(a, m): return [x & k for x, k in zip(a, m)]
def _vneg(a): return [x ^ SIGN for x in a]
def _yzx(v): return [v[1], v[2], v[0], v[3]]      # shufps 0xc9
def _zxy(v): return [v[2], v[0], v[1], v[3]]      # shufps 0xd2


def _dot(a, b, m, r):
    """mulps a, b; andps mask; haddps twice (all lanes equal)."""
    return _hadd_sum(_vand(_vmul(a, b, r), m), r)


def _cr(p, q, s, t, r):
    """subps(mulps(p, q), mulps(s, t)): one lane-shuffled cross product as emitted."""
    return _vsub(_vmul(p, q, r), _vmul(s, t, r), r)


def _inv(x, m, r):
    """1.0 x4 divps x, then the XYZ mask."""
    return _vand(_bc(_div(ONE, x, r)), m)


def _abs_le(x, static):
    return all(_le(x & ABS, s) for s in static)


def _cvtt(bits):
    """cvttss2si: truncation; NaN or out of int32 range -> 0x80000000."""
    if (bits & 0x7F800000) == 0x7F800000:
        return -0x80000000
    v = struct.unpack('<f', struct.pack('<I', bits))[0]
    t = math.trunc(v)
    if t < -0x80000000 or t > 0x7FFFFFFF:
        return -0x80000000
    return t


def _s32(x):
    x &= 0xFFFFFFFF
    return x - (1 << 32) if x & 0x80000000 else x


def _f(mem, address):
    return mem.d(address)


# --- support routine (0x1949480) -------------------------------------------------------

def _vertex_dot(mem, verts, index, d, r):
    x, y, z = d
    base = verts + 12 * index
    return _add(_add(_mul(y, _f(mem, base + 4), r), _mul(x, _f(mem, base), r), r),
                _mul(z, _f(mem, base + 8), r), r)


def _gt(a, b):
    """comiss a, b followed by jbe-skip: a > b ordered."""
    return _lt(b, a)


def hull_support(mem, shape, d, nan_rule='sse'):
    """0x1949480(shape, &dir3). d = (x, y, z) bit words. Returns the vertex index."""
    r = nan_rule
    lookup = mem.q(shape + 0xC0)
    verts = mem.q(shape + 0x40)
    if not lookup:
        n = (mem.d(shape + 0x48) - 1) & 0xFFFFFFFF
        if n >= 0x80000000:
            raise ValueError('vertex count field 0: the native scan is unbounded')
        best, index = NEG_FLT_MAX, 0
        for i in range(n):
            v = _vertex_dot(mem, verts, i, d, r)
            if _gt(v, best):
                best, index = v, i
        return index
    x, y, z = d
    e0, e4, e8 = mem.d(shape + 0xE0), mem.d(shape + 0xE4), mem.d(shape + 0xE8)
    length = _sqrt(_add(_add(_mul(x, x, r), _mul(y, y, r), r), _mul(z, z, r), r))
    s = _mul(_div(ONE, length, r), e8, r)
    cells = []
    for c in (x, y, z):
        k = _cvtt(_add(e8, _mul(c, s, r), r))
        k = k if k > 0 else 0
        cells.append(k if k < _s32(e0) else _s32(e0))
    ix, iy, iz = cells
    slot = ((((iz * e4) + iy) & 0xFFFFFFFF) * e4 + ix) & 0xFFFFFFFF
    entry = mem.d(lookup + 4 * slot)
    if not entry & 1:
        return entry >> 1
    item_at = mem.q(shape + 0xD0) + 4 * (entry >> 1)
    item = mem.d(item_at)
    index = item >> 1
    best = _vertex_dot(mem, verts, index, d, r)
    while not item & 1:
        item_at += 4
        item = mem.d(item_at)
        v = _vertex_dot(mem, verts, item >> 1, d, r)
        if _gt(v, best):
            best, index = v, item >> 1
    return index


# --- simplex -----------------------------------------------------------------------

class _Entry:
    __slots__ = ('index', 'second', 's', 'p', 'w', 'weight')

    def __init__(self, index, second, s, p, w, weight):
        self.index, self.second, self.s, self.p, self.w, self.weight = index, second, s, p, w, weight

    def copy(self):
        return _Entry(self.index, self.second, list(self.s), list(self.p), list(self.w), list(self.weight))


def _blank():
    return _Entry(0, 0, [0] * 4, [0] * 4, [0] * 4, [0] * 4)


def _world_vertex(mem, verts, index, rows, m, r):
    raw = list(struct.unpack('<4I', bytes(mem.view(verts + 12 * index, 16))))
    v = _vand(raw, m)
    acc = _vadd(rows[3], _vmul(_bc(v[0]), rows[0], r), r)
    acc = _vadd(acc, _vmul(_bc(v[1]), rows[1], r), r)
    return _vadd(acc, _vmul(_bc(v[2]), rows[2], r), r)


def _local_direction(rows, nd, m, r):
    """(-d) through the frame rows: mulps -d,row_k; haddps(p0,p1); haddps(p2,p2);
    haddps of those -> [p0 pair sum, p1 pair sum, p2 pair sum, p2 pair sum], masked."""
    p = [_vmul(nd, rows[k], r) for k in range(3)]
    h1 = [_add(p[0][0], p[0][1], r), _add(p[0][2], p[0][3], r),
          _add(p[1][0], p[1][1], r), _add(p[1][2], p[1][3], r)]
    h2 = [_add(p[2][0], p[2][1], r), _add(p[2][2], p[2][3], r)] * 2
    return _vand([_add(h1[0], h1[1], r), _add(h1[2], h1[3], r),
                  _add(h2[0], h2[1], r), _add(h2[2], h2[3], r)], m)


def _direction(e, count, r, m):
    a = e[0].w
    if count == 1:
        return _vneg(a)
    if count == 2:
        ao, ed = _vneg(a), _vsub(e[1].w, a, r)
        c = _cr(_zxy(ao), _yzx(ed), _yzx(ao), _zxy(ed), r)
        return _cr(_yzx(c), _zxy(ed), _yzx(ed), _zxy(c), r)
    if count == 3:
        ac, ab = _vsub(e[2].w, a, r), _vsub(e[1].w, a, r)
        n = _cr(_zxy(ac), _yzx(ab), _yzx(ac), _zxy(ab), r)
        return n if _lt(_dot(n, a, m, r), 0) else _vneg(n)
    return [0, 0, 0, 0]


def _solve_segment(e, m, r, statics):
    a, b = e[0].w, e[1].w
    ed = _vsub(b, a, r)
    ee = _dot(ed, ed, m, r)
    ub = _dot(ed, a, m, r) ^ SIGN
    ua = _dot(ed, b, m, r)
    if _le(ub, 0):
        e[0].weight = _bc(ONE)
        return 1, True
    if _le(ua, 0):
        e[0] = e[1].copy()
        e[0].weight = _bc(ONE)
        return 1, True
    if _abs_le(ee, statics[0]):
        return 1, False
    inv = _inv(ee, m, r)
    e[0].weight = _vmul(inv, _bc(ua), r)
    e[1].weight = _vmul(inv, _bc(ub), r)
    return 2, True


def _solve_triangle(e, m, r, statics):
    a, b, c = e[0].w, e[1].w, e[2].w
    ab = _vsub(b, a, r)
    ab_b, ab_ab = _dot(ab, b, m, r), _dot(ab, ab, m, r)
    neg_ab_a = _dot(ab, a, m, r) ^ SIGN
    bc = _vsub(c, b, r)
    bc_bc = _dot(bc, bc, m, r)
    neg_bc_b = _dot(bc, b, m, r) ^ SIGN
    bc_c = _dot(bc, c, m, r)
    ca = _vsub(a, c, r)
    ca_ca = _dot(ca, ca, m, r)
    neg_ca_c = _dot(ca, c, m, r) ^ SIGN
    ca_a = _dot(ca, a, m, r)
    if _le(neg_ca_c, 0) and _le(bc_c, 0):
        e[0] = e[2].copy()
        e[0].weight = _bc(ONE)
        return 1, True
    x_bc = _cr(_yzx(b), _zxy(c), _yzx(c), _zxy(b), r)
    x_ca = _cr(_zxy(a), _yzx(c), _yzx(a), _zxy(c), r)
    x_ab = _cr(_yzx(a), _zxy(b), _yzx(b), _zxy(a), r)
    ac = _vsub(c, a, r)
    n = _cr(_zxy(ac), _yzx(ab), _yzx(ac), _zxy(ab), r)
    va, vb = _dot(n, x_bc, m, r), _dot(n, x_ca, m, r)
    nn, vc = _dot(n, n, m, r), _dot(n, x_ab, m, r)
    if _le(vc, 0):                                           # edge AB
        inv = _inv(ab_ab, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(ab_b), r), _vmul(inv, _bc(neg_ab_a), r)
        return 2, True
    if _le(va, 0) and _lt(0, bc_c) and _lt(0, neg_bc_b):     # edge BC
        e[0], e[1] = e[1].copy(), e[2].copy()
        inv = _inv(bc_bc, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(bc_c), r), _vmul(inv, _bc(neg_bc_b), r)
        return 2, True
    if _le(vb, 0) and _lt(0, ca_a) and _lt(0, neg_ca_c):     # edge CA
        e[0], e[1] = e[2].copy(), e[0].copy()
        inv = _inv(ca_ca, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(ca_a), r), _vmul(inv, _bc(neg_ca_c), r)
        return 2, True
    if _abs_le(nn, statics[1]):
        return 2, False
    inv = _inv(nn, m, r)
    e[0].weight = _vmul(inv, _bc(va), r)
    e[2].weight = _vmul(inv, _bc(vc), r)
    e[1].weight = _vmul(inv, _bc(vb), r)
    return 3, True


def _solve_tetrahedron(e, m, r, statics):
    a, b, c, d = e[0].w, e[1].w, e[2].w, e[3].w
    ab = _vsub(b, a, r)
    ac = _vsub(c, a, r)
    ad = _vsub(d, a, r)
    ad_ad = _dot(ad, ad, m, r)
    neg_ad_a = _dot(ad, a, m, r) ^ SIGN
    ad_d = _dot(ad, d, m, r)
    bc = _vsub(c, b, r)
    cd = _vsub(d, c, r)
    cd_cd = _dot(cd, cd, m, r)
    neg_cd_c = _dot(cd, c, m, r) ^ SIGN
    cd_d = _dot(cd, d, m, r)
    db = _vsub(b, d, r)
    db_db = _dot(db, db, m, r)
    neg_db_d = _dot(db, d, m, r) ^ SIGN
    db_b = _dot(db, b, m, r)
    if _le(ad_d, 0) and _le(cd_d, 0) and _le(neg_db_d, 0):   # vertex D
        e[0] = e[3].copy()
        e[0].weight = _bc(ONE)
        return 1, True
    # face ABC (opposite D)
    x_cb = _cr(_yzx(c), _zxy(b), _yzx(b), _zxy(c), r)
    x_ba = _cr(_zxy(a), _yzx(b), _yzx(a), _zxy(b), r)
    x_ac = _cr(_yzx(a), _zxy(c), _yzx(c), _zxy(a), r)
    n1 = _cr(_zxy(ab), _yzx(ac), _yzx(ab), _zxy(ac), r)
    n1n1, n1_cb = _dot(n1, n1, m, r), _dot(n1, x_cb, m, r)
    n1_ac, n1_ba = _dot(n1, x_ac, m, r), _dot(n1, x_ba, m, r)
    # face ABD
    x_bd = _cr(_yzx(b), _zxy(d), _yzx(d), _zxy(b), r)
    x_da = _cr(_zxy(a), _yzx(d), _yzx(a), _zxy(d), r)
    x_ab = _cr(_yzx(a), _zxy(b), _yzx(b), _zxy(a), r)
    n2 = _cr(_zxy(ad), _yzx(ab), _yzx(ad), _zxy(ab), r)
    n2n2, n2_bd = _dot(n2, n2, m, r), _dot(n2, x_bd, m, r)
    n2_da, n2_ab = _dot(n2, x_da, m, r), _dot(n2, x_ab, m, r)
    # face ACD
    x_dc = _cr(_yzx(d), _zxy(c), _yzx(c), _zxy(d), r)
    x_ca = _cr(_zxy(a), _yzx(c), _yzx(a), _zxy(c), r)
    x_ad = _cr(_yzx(a), _zxy(d), _yzx(d), _zxy(a), r)
    n3 = _cr(_zxy(ac), _yzx(ad), _yzx(ac), _zxy(ad), r)
    n3_dc, n3n3 = _dot(n3, x_dc, m, r), _dot(n3, n3, m, r)
    n3_ca, n3_ad = _dot(n3, x_ca, m, r), _dot(n3, x_ad, m, r)
    # face BCD
    bd = _vsub(d, b, r)
    x_cd = _cr(_yzx(c), _zxy(d), _yzx(d), _zxy(c), r)
    x_db = _cr(_zxy(b), _yzx(d), _yzx(b), _zxy(d), r)
    x_bc = _cr(_yzx(b), _zxy(c), _yzx(c), _zxy(b), r)
    n4 = _cr(_zxy(bd), _yzx(bc), _yzx(bd), _zxy(bc), r)
    n4n4, n4_cd = _dot(n4, n4, m, r), _dot(n4, x_cd, m, r)
    n4_db, n4_bc = _dot(n4, x_db, m, r), _dot(n4, x_bc, m, r)
    if _le(n3_ad, 0) and _le(n2_da, 0) and _lt(0, ad_d) and _lt(0, neg_ad_a):       # edge AD
        e[1] = e[3].copy()
        inv = _inv(ad_ad, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(ad_d), r), _vmul(inv, _bc(neg_ad_a), r)
        return 2, True
    if _le(n3_dc, 0) and _le(n4_cd, 0) and _lt(0, cd_d) and _lt(0, neg_cd_c):       # edge CD
        e[0], e[1] = e[2].copy(), e[3].copy()
        inv = _inv(cd_cd, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(cd_d), r), _vmul(inv, _bc(neg_cd_c), r)
        return 2, True
    if _le(n2_bd, 0) and _le(n4_db, 0) and _lt(0, db_b) and _lt(0, neg_db_d):       # edge BD
        e[0] = e[3].copy()
        inv = _inv(db_db, m, r)
        e[0].weight, e[1].weight = _vmul(inv, _bc(db_b), r), _vmul(inv, _bc(neg_db_d), r)
        return 2, True
    mv = _cr(_zxy(ad), _yzx(ac), _yzx(ad), _zxy(ac), r)
    vol = _dot(mv, ab, m, r)
    sgn = _bc(MINUS_ONE if _lt(vol, 0) else ONE)
    y_cd = _cr(_yzx(c), _zxy(d), _yzx(d), _zxy(c), r)
    u_a = _vmul(sgn, _bc(_dot(y_cd, b, m, r)), r)
    y_dc = _cr(_yzx(d), _zxy(c), _yzx(c), _zxy(d), r)
    y_cb = _cr(_zxy(b), _yzx(c), _yzx(b), _zxy(c), r)
    y_bd = _cr(_yzx(b), _zxy(d), _yzx(d), _zxy(b), r)
    u_b = _vmul(_bc(_dot(y_dc, a, m, r)), sgn, r)
    u_d = _vmul(_bc(_dot(y_cb, a, m, r)), sgn, r)
    u_c = _vmul(_bc(_dot(y_bd, a, m, r)), sgn, r)
    total = _vmul(sgn, _bc(vol), r)
    if all(_le(x, 0) for x in u_d) and _lt(0, n1_cb) and _lt(0, n1_ba) and _lt(0, n1_ac):   # face ABC
        e[3] = e[1].copy()
        e[1] = e[2].copy()
        e[2] = e[3].copy()
        inv = _inv(n1n1, m, r)
        e[0].weight = _vmul(inv, _bc(n1_cb), r)
        e[2].weight = _vmul(inv, _bc(n1_ac), r)
        e[1].weight = _vmul(inv, _bc(n1_ba), r)
        return 3, True
    if all(_le(x, 0) for x in u_c) and _lt(0, n2_bd) and _lt(0, n2_da) and _lt(0, n2_ab):   # face ABD
        e[2] = e[3].copy()
        inv = _inv(n2n2, m, r)
        e[1].weight = _vmul(_bc(n2_da), inv, r)
        e[2].weight = _vmul(_bc(n2_ab), inv, r)
        e[0].weight = _vmul(_bc(n2_bd), inv, r)
        return 3, True
    if all(_le(x, 0) for x in u_b) and _lt(0, n3_dc) and _lt(0, n3_ca) and _lt(0, n3_ad):   # face ACD
        e[1] = e[3].copy()
        inv = _inv(n3n3, m, r)
        e[1].weight = _vmul(_bc(n3_ca), inv, r)
        e[2].weight = _vmul(_bc(n3_ad), inv, r)
        e[0].weight = _vmul(_bc(n3_dc), inv, r)
        return 3, True
    if all(_le(x, 0) for x in u_a) and _lt(0, n4_cd) and _lt(0, n4_db) and _lt(0, n4_bc):   # face BCD
        e[0], e[1], e[2] = e[1].copy(), e[2].copy(), e[3].copy()
        inv = _inv(n4n4, m, r)
        e[0].weight = _vmul(inv, _bc(n4_cd), r)
        e[1].weight = _vmul(inv, _bc(n4_db), r)
        e[2].weight = _vmul(inv, _bc(n4_bc), r)
        return 3, True
    if all(_le(t & ABS, s) for t, s in zip(total, statics[2])):
        return 3, False
    inv = _vand([_div(ONE, t, r) for t in total], m)
    e[0].weight = _vmul(inv, u_a, r)
    e[1].weight = _vmul(inv, u_b, r)
    e[2].weight = _vmul(inv, u_c, r)
    e[3].weight = _vmul(inv, u_d, r)
    return 4, True


_SOLVERS = {2: _solve_segment, 3: _solve_triangle, 4: _solve_tetrahedron}
_INITIAL_VISITED = ()     # the visited list is empty until the first addition


def _solver(count):
    if count == 2:
        return _solve_segment
    return _SOLVERS[count]


def _combine(e, count, field, r):
    acc = _vmul(getattr(e[0], field), e[0].weight, r)
    for k in range(1, count):
        acc = _vadd(_vmul(e[k].weight, getattr(e[k], field), r), acc, r)
    return acc


# --- the query (0x18f0a70) ------------------------------------------------------------

def convex_point_query(mem, rows, shape, point, iterations=16, *, mask=XYZ_MASK, nan_rule='sse',
                       statics=DEFAULT_STATICS, trace=None, support=None):
    """0x18f0a70. rows: the four 4-lane frame rows of the block; shape: hull pointer;
    point: 4 lanes (used unmasked). Returns (dist, on_hull, on_point) bit lists.
    trace (list) receives one dict per completed loop decision (authored debug aid)."""
    r, m = nan_rule, _m(mask)
    support = support or hull_support
    verts = mem.q(shape + 0x40)
    p = list(point)
    s0 = _world_vertex(mem, verts, 0, rows, m, r)
    w0 = _vsub(p, s0, r)
    e = [_Entry(0, 0, s0, list(p), w0, _bc(ONE)), _blank(), _blank(), _blank()]
    count = 1
    prev = _bc(_dot(w0, w0, m, r))
    visited = list(_INITIAL_VISITED)
    reason = 'iterations'
    it = 0
    while it < iterations:
        d = _direction(e, count, r, m)
        if _lt(_dot(d, d, m, r), DIRECTION_EPSILON):
            reason = 'direction'
            break
        index = support(mem, shape, _local_direction(rows, _vneg(d), m, r)[:3], r)
        s = _world_vertex(mem, verts, index, rows, m, r)
        saved = (count, [x.copy() for x in e])
        if any(v == index for v in visited):
            reason = 'repeat'
            break
        e[count] = _Entry(index, 0, s, list(p), _vsub(p, s, r), _bc(ONE))
        count += 1
        visited = [x.index for x in e[:count]]
        count, go = _solver(count)(e, m, r, statics)
        if trace is not None:
            trace.append({'iteration': it, 'index': index, 'count': count, 'continue': go})
        if not go:
            reason = 'degenerate'
            break
        if count == 4:
            reason = 'inside'
            break
        v = e[0].w if count == 1 else _combine(e, count, 'w', r)
        vv = _bc(_dot(v, v, m, r))
        scaled = [_mul(PROGRESS_FACTOR, x, r) for x in prev]
        prev = vv
        if all(_le(a, b) for a, b in zip(scaled, vv)):
            count, e = saved[0], saved[1]
            reason = 'no-progress'
            break
        it += 1
    if trace is not None:
        trace.append({'exit': reason, 'count': count})
    if count == 1:
        on_hull, on_point = list(e[0].s), list(e[0].p)
    elif count in (2, 3):
        on_hull, on_point = _combine(e, count, 's', r), _combine(e, count, 'p', r)
    elif count == 4:
        on_hull = _combine(e, 4, 's', r)
        on_point = list(on_hull)
    else:
        on_hull, on_point = [0] * 4, [0] * 4
    diff = _vsub(on_point, on_hull, r)
    dist = _bc(_sqrt(_dot(diff, diff, m, r)))
    return dist, on_hull, on_point


def bind_point_query(mem, *, iterations=16, mask=XYZ_MASK, nan_rule='sse', statics=DEFAULT_STATICS):
    """The `point_query(frame_b_rows, shape_b, point)` service for
    engine.pose_narrowphase_sphere.sphere_convex_tester."""
    def point_query(rows, shape, point):
        return convex_point_query(mem, rows, shape, point, iterations, mask=mask, nan_rule=nan_rule,
                                  statics=statics)
    return point_query
