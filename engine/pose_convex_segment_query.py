"""Segment-vs-convex distance queries: 0x18f3710 (segment vs kind-5 hull, the sibling of the
point query 0x18f0a70) and 0x18eab80 (segment vs box half extents).

Evidence: docs/reconstruction/LINK_SOLVER.md "Convex point query (0x18f0a70) and hull
support (0x1949480)" (the shared GJK loop, solvers, statics and hull support) and
"Convex segment queries (0x18f3710, 0x18eab80)" (this module), plus "Narrow-phase capsule
and convex hull testers" (caller 0x19dd130) and "Narrow-phase box testers" (caller
0x19d9160). Static reads of the memory image; offsets are evidence anchors, not
portable API fields. Native comparison:
analysis/command-executor-audit/check_pose_convex_segment_query.py
-> native/snow_host/pose_convex_segment_query_validation.json.

Call shapes (callers 0x19dd130 and 0x19d9160):
  0x18f3710(out, block, points, 16): block = {frame rows b0, b1, b2, t; hull shape pointer
    at +0x40}; points = {p0, p1} (two 4-lane rows, aligned, read unmasked).
  0x18eab80(out, block, points, 16): block = {frame rows; half extents (4 lanes) at +0x40}.
  out = {dist (broadcast), on_shape (world), on_segment}, 0x30 bytes.

All three queries (0x18f0a70, 0x18f3710, 0x18eab80) are instances of one GJK routine:
the same simplex layout {shape index, segment index, s, P, w = P - s, weight}, the same
inlined 2/3/4-point region solvers that read the same function-local statics 0x3336a30 /
0x3336a50 / 0x3336a70 (guards 0x3336a40 / 60 / 80), the same constants 0x29ca860 (2^-46)
and 0x29ca880 (0.999999) and the same leaves. This module therefore imports the solvers,
direction, combination and support code of engine.pose_convex_point_query instead of
copying them. The Unicorn receipt checks that reuse lane for lane under the emulator's
two-NaN rule and, with an overlay that rewrites every two-NaN lane of the executed
addps/subps/mulps/divps(/ss) to the first operand, under nan_rule='sse', which makes the
operand order of the reused code observable (the emulator's own rule is commutative).

Recovered differences of 0x18f3710 from 0x18f0a70:
- Entry 0 is {0, 0, s0 = world(hull vertex 0), P = p0, w0 = p0 - s0, 1}. The world
  transform of vertex 0 multiplies the third term as b2 * z (mulps [rdx+0x20], bcast z;
  operand order differs from the loop transform, which is z * b2).
- Each iteration, after the hull support (unchanged: -d through the rows, 0x19497c0 ->
  0x1949480), the segment support picks j = 1 when 0 < hadd2(((p1 - p0) * d) & M) (lane
  0 of the cmpltps; NaN gives 0), else 0, and P = the j-th point (unmasked).
- The repeat test compares the (shape index, segment index) pair against the pairs of
  the simplex as it stood after the previous addition (empty on the first iteration).
- The solvers subtract a zero origin from every w first (subps w, 0). For every w that
  can occur (all are subps results, hence never signalling NaN) this is the identity,
  so the point-query solvers apply unchanged.
- Output by count: 1 -> (s0, P0); 2/3 -> (sum s_k*wt_k, sum P_k*wt_k); 4 -> both rows the
  shape combination; dist = sqrt(hadd2((Q - H)^2 & M)) in all lanes.

0x18eab80 differs from 0x18f3710 only in the shape support:
- Box support of the local direction L (masked, as for the hull): code = (L.x < 0 ?
  0x100 : 0) | (L.y < 0 ? 0x10 : 0) | (L.z < 0 ? 1 : 0) (cmpltps, NaN or -0 counts as
  not negative); vertex = (x, y, z, 0) with x = code & 0xf00 ? -hx : hx, y = code & 0xf0
  ? -hy : hy, z = code & 0xf ? -hz : hz (sign flip by xorps), the extents re-read from
  block +0x40 lanes 0..2 each iteration; the box vertex is not masked (lane 3 is a
  constructed 0). The code is the simplex shape index.
- Entry 0 uses the all-positive vertex (code 0) with the loop transform's operand order.

Float32 semantics follow engine.pose_convex_point_query (exact double then one rounding,
no FTZ/DAZ, default NaN 0xffc00000, two-NaN choice by `nan_rule`, destination-first
operand order kept).

Supplied (not restated): the CRT thread-safe static initialisation 0x1c44fb0 /
0x1c44f50 (statics are a parameter), __chkstk 0x1c45120.

Authored choices: names, the trace hook, the `statics` parameter, the bind helpers.
Nothing here claims equivalence with the original engine beyond the validated fixtures.
"""
from engine import pose_convex_point_query as pq
from engine.pose_contact_payload_update import XYZ_MASK
from engine.pose_convex_point_query import (
    DEFAULT_STATICS, ONE, SIGN, _Entry, _bc, _blank, _combine, _direction, _dot, _local_direction,
    _m, _vadd, _vand, _vmul, _vneg, _vsub, _world_vertex, hull_support)
from engine.pose_narrowphase_dispatch import _le, _lt, _mul, _sqrt
import struct

SEGMENT_QUERY_RVA = 0x18F3710
BOX_SEGMENT_QUERY_RVA = 0x18EAB80
POINT_QUERY_RVA = pq.POINT_QUERY_RVA
CAPSULE_HULL_CORE_RVA = 0x19DD130     # caller of 0x18f3710
BOX_CAPSULE_CORE_RVA = 0x19D9160      # caller of 0x18eab80
SEGMENT_INDEX_ONE = 1                 # 16-byte constant 0x1e04e10 (1 x4), pand-selected

DIRECTION_EPSILON = pq.DIRECTION_EPSILON   # 0x29ca860, 2^-46
PROGRESS_FACTOR = pq.PROGRESS_FACTOR       # 0x29ca880, 0.999999
_SOLVERS = pq._SOLVERS                     # shared inlined solvers (same statics)
_INITIAL_VISITED = ()                      # empty until the first addition
BOX_X, BOX_Y, BOX_Z = 0x100, 0x10, 0x1     # box support code bits


# --- shape supports -------------------------------------------------------------------

def segment_support(segment, d, m, r):
    """j = 1 when 0 < hadd2(((p1 - p0) * d) & M), else 0."""
    e = _vsub(segment[1], segment[0], r)
    return SEGMENT_INDEX_ONE if _lt(0, _dot(e, d, m, r)) else 0


def _world_first_hull(mem, verts, rows, m, r):
    """Vertex 0 of 0x18f3710: ((t + x*b0) + y*b1) + b2*z (third product reversed)."""
    raw = list(struct.unpack('<4I', bytes(mem.view(verts, 16))))
    v = _vand(raw, m)
    acc = _vadd(rows[3], _vmul(_bc(v[0]), rows[0], r), r)
    acc = _vadd(acc, _vmul(_bc(v[1]), rows[1], r), r)
    return _vadd(acc, _vmul(rows[2], _bc(v[2]), r), r)


def box_support(half, local):
    """0x18eab80 inline box support: (code, local vertex 4 lanes)."""
    code = ((BOX_X if _lt(local[0], 0) else 0) | (BOX_Y if _lt(local[1], 0) else 0)
            | (BOX_Z if _lt(local[2], 0) else 0))
    x = half[0] ^ SIGN if code & 0xF00 else half[0]
    y = half[1] ^ SIGN if code & 0xF0 else half[1]
    z = half[2] ^ SIGN if code & 0xF else half[2]
    return code, [x, y, z, 0]


def _world_box(rows, v, r):
    acc = _vadd(rows[3], _vmul(_bc(v[0]), rows[0], r), r)
    acc = _vadd(acc, _vmul(_bc(v[1]), rows[1], r), r)
    return _vadd(acc, _vmul(_bc(v[2]), rows[2], r), r)


# --- the shared loop -------------------------------------------------------------------

def _key(index, j):
    """The repeat test compares both simplex words: shape index (+0) and segment index (+4)."""
    return index, j


def _gjk(rows, segment, s0, shape_support, iterations, m, r, statics, trace):
    p0, p1 = list(segment[0]), list(segment[1])
    seg = (p0, p1)
    w0 = _vsub(p0, s0, r)
    e = [_Entry(0, 0, s0, list(p0), w0, _bc(ONE)), _blank(), _blank(), _blank()]
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
        index, s = shape_support(_local_direction(rows, _vneg(d), m, r))
        j = segment_support(seg, d, m, r)
        p = seg[1] if j == 1 else seg[0]
        saved = (count, [x.copy() for x in e])
        if any(v == _key(index, j) for v in visited):
            reason = 'repeat'
            break
        e[count] = _Entry(index, j, s, list(p), _vsub(p, s, r), _bc(ONE))
        count += 1
        visited = [_key(x.index, x.second) for x in e[:count]]
        count, go = _SOLVERS[count](e, m, r, statics)
        if trace is not None:
            trace.append({'iteration': it, 'index': index, 'segment': j, 'count': count, 'continue': go})
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
        on_shape, on_seg = list(e[0].s), list(e[0].p)
    elif count in (2, 3):
        on_shape, on_seg = _combine(e, count, 's', r), _combine(e, count, 'p', r)
    elif count == 4:
        on_shape = _combine(e, 4, 's', r)
        on_seg = list(on_shape)
    else:
        on_shape, on_seg = [0] * 4, [0] * 4
    diff = _vsub(on_seg, on_shape, r)
    dist = _bc(_sqrt(_dot(diff, diff, m, r)))
    return dist, on_shape, on_seg


# --- public queries --------------------------------------------------------------------

def convex_segment_query(mem, rows, shape, segment, iterations=16, *, mask=XYZ_MASK, nan_rule='sse',
                         statics=DEFAULT_STATICS, trace=None, support=None):
    """0x18f3710. rows: the four 4-lane frame rows of the block; shape: hull pointer;
    segment: (p0, p1) 4-lane bit lists (unmasked). Returns (dist, on_hull, on_segment).
    trace (list) receives one dict per completed loop decision (authored debug aid)."""
    r, m = nan_rule, _m(mask)
    sup = support or hull_support
    verts = mem.q(shape + 0x40)

    def shape_support(local):
        index = sup(mem, shape, local[:3], r)
        return index, _world_vertex(mem, verts, index, rows, m, r)
    s0 = _world_first_hull(mem, verts, rows, m, r)
    return _gjk(rows, segment, s0, shape_support, iterations, m, r, statics, trace)


def box_segment_query(rows, half, segment, iterations=16, *, mask=XYZ_MASK, nan_rule='sse',
                      statics=DEFAULT_STATICS, trace=None):
    """0x18eab80. rows: frame rows; half: the 4-lane extents at block +0x40 (lanes 0..2
    used); segment: (p0, p1). Returns (dist, on_box, on_segment)."""
    r, m = nan_rule, _m(mask)
    half = list(half)

    def shape_support(local):
        code, v = box_support(half, local)
        return code, _world_box(rows, v, r)
    s0 = _world_box(rows, [half[0], half[1], half[2], 0], r)
    return _gjk(rows, segment, s0, shape_support, iterations, m, r, statics, trace)


def read_block(mem, block):
    """The 0x48/0x50-byte block: (rows, pointer at +0x40, 4 lanes at +0x40)."""
    rows = [list(struct.unpack('<4I', bytes(mem.view(block + 16 * k, 16)))) for k in range(4)]
    return rows, mem.q(block + 0x40), list(struct.unpack('<4I', bytes(mem.view(block + 0x40, 16))))


def segment_query_at(mem, out, block, points, iterations=16, *, box=False, mask=XYZ_MASK, nan_rule='sse',
                     statics=DEFAULT_STATICS):
    """Memory form of either routine: reads block and points, writes the 0x30-byte result."""
    rows, shape, half = read_block(mem, block)
    seg = [list(struct.unpack('<4I', bytes(mem.view(points + 16 * k, 16)))) for k in range(2)]
    if box:
        res = box_segment_query(rows, half, seg, iterations, mask=mask, nan_rule=nan_rule, statics=statics)
    else:
        res = convex_segment_query(mem, rows, shape, seg, iterations, mask=mask, nan_rule=nan_rule,
                                   statics=statics)
    mem.view(out, 0x30)[:] = struct.pack('<12I', *res[0], *res[1], *res[2])
    return res


def bind_segment_query(mem, rows, shape, *, iterations=16, mask=XYZ_MASK, nan_rule='sse', statics=DEFAULT_STATICS):
    """The `gjk(p0, p1) -> (dist, on_hull, on_axis)` service of
    engine.pose_narrowphase_kind45.capsule_hull_core for the hull frame `rows` (as the
    entry 0x19ddbc0 passes them, already masked) and hull shape pointer `shape`."""
    def gjk(p0, p1):
        return convex_segment_query(mem, rows, shape, (p0, p1), iterations, mask=mask, nan_rule=nan_rule,
                                    statics=statics)
    return gjk
