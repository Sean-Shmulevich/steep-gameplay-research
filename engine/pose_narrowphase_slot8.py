"""Narrow-phase tester slot +8 (vt[1]): the boolean overlap test, and its binding to the
flagged-neighbor routines.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase tester slot +8 (overlap
test)". It extends "Narrow-phase tester table and sphere-sphere tester" (TESTER_TABLE,
selector 0x18de680) and "Live narrow-phase tester census" (the flagged bodies 0x18dfa10
and 0x18e01e0 select a tester and call its slot +8 at 0x18e011a / 0x18e0784, then test
`al`). Static reads of every tester vtable in this image.

Tester vtable layout (5 qwords per table, packed back to back in .rdata):
  +0x00 0x198a280 destructor (shared)
  +0x08 slot 1: overlap(tester, geom) -> al (0/1). This module.
  +0x10 slot 2: overlap(tester, geom, filter*) -> al. Non-terrain cells use 0x1163990
        (`mov rax,[rcx]; jmp [rax+8]`, i.e. slot 1 with r8 ignored). Terrain cells read a
        16-byte filter {any-of mask, all-of mask} and skip triangles whose material
        qword (+0x38) misses the first mask or lacks a bit of the second.
  +0x18 slot 3: contact generation(tester, geom, out, capacity) (earlier sections).
  +0x20 slot 4: contact generation with the same filter as a fifth argument. Non-terrain
        cells use 0xfec1b0 (`jmp [rax+0x18]`, slot 3 with the filter ignored).

`geom` is the 0x90-byte query block: frameA rows +0x00..+0x3f, frameB rows
+0x40..+0x7f (basis rows, then translation), shapeA +0x80, shapeB +0x88. The flagged
bodies leave every fourth lane unwritten; every slot-1 body here masks rows with the
runtime XYZ mask 0x3336890 first, so with the standard mask that lane is irrelevant.

Distinct slot-1 bodies (non-terrain):
  0x19d4df0 (2,2) sphere-sphere          0x19d5300 (2,3) sphere-box
  0x19d57f0 (2,4) sphere-capsule         0x19d8cf0 (3,3) box-box (15-axis SAT)
  0x19dcf20 -> 0x19dca50 (4,4) capsule-capsule (segment distance)
  0x19c6520 (2,5) (3,4) (3,5) (4,5) (5,5) generic support-function test (Minkowski
            portal refinement over shape vt+0x68 centre and vt+0x40 support).
Swapped cells call the forward cell's slot 1 with A and B exchanged through a geom-swap
wrapper (0x198d5b0 template; 0x198e370 (3,2), 0x198e4b0 (4,2), 0x198d5b0 (4,3),
0x198e5f0 (5,2), 0x198d6f0 (5,3), 0x198d830 (5,4)). The wrapper copies only xyz of the
eight rows (lane 3 = stale stack), swaps the shape pointers and passes a stack tester
whose vtable is the forward cell's; no result post-processing.

Terrain cells (kind 6 and 7 rows and their swaps) have their own slot-1 bodies
(TERRAIN_SLOT8). They are not restated: `pose_tester_overlap` raises
TerrainSlot8Unavailable for them.

Shape virtuals used by 0x19c6520 (dispatched on the shape's own vtable, as native):
  vt+0x68 centre (local): 0x18aae30 (sphere/box/capsule) writes (0,0,0); hull 0x18af7b0
         copies +0x64/+0x68/+0x6c. 12 bytes are written and 16 read, then masked.
  vt+0x40 support (shape, out, &dir) -> 16 bytes:
         sphere 0x18ab4b0, box 0x18ab2e0, capsule 0x18ab3b0, hull 0x1949450
         (-> vt+0x48 0x1949400 -> 0x1949480, engine.pose_convex_point_query.hull_support).

Float32 lane semantics follow engine.pose_contact_payload_update (exact double then one
rounding, no FTZ/DAZ, default NaN 0xffc00000, two-NaN choice by `nan_rule`). Stale
lanes (centre/hull-support fourth lane, swap-wrapper fourth lanes) are modelled as 0
before masking, which equals native only under the standard mask; the harness uses the
standard mask for those bodies.

Authored: function names, the iteration guard of the portal test (native has no cap and
can loop forever; the model raises PortalIterationLimit), the terrain exception, the
service adapters and the zero fourth lane of frames given as Python floats.
"""
import struct
from types import SimpleNamespace

from engine.pose_contact_payload_update import XYZ_MASK, _add, _is_nan, _mul, _sub
from engine.pose_narrowphase_dispatch import (
    TESTER_TABLE,
    _div,
    _le,
    _lt,
    _sqrt,
    select_pose_tester,
)
from engine.pose_convex_point_query import hull_support

IMAGE_BASE = 0x140000000
SIGN = 0x80000000
ABS = 0x7FFFFFFF
ONE = 0x3F800000                 # 0x1e252f0 (x4)
TWO = 0x40000000                 # 0x1e61d20 (x4)
PORTAL_EPSILON = 0x38800000      # 0x29cc0d0 (x4), 2^-14
PARALLEL_FACTOR = 0x3727C5AC     # 0x1e252b0 (x4), 1e-5
SAT_EPSILON = (0x3727C5AC, 0x3727C5AC, 0x3727C5AC, 0)   # 0x29cc0e0: 1e-5 x3, lane 3 = 0
ZERO4 = (0, 0, 0, 0)             # 0x33368c0 (runtime static, zero in the image)

SHARED_SLOT2_RVA = 0x1163990     # jmp [vt+8]
SHARED_SLOT4_RVA = 0xFEC1B0      # jmp [vt+0x18]
DESTRUCTOR_RVA = 0x198A280

SPHERE_SPHERE_RVA = 0x19D4DF0
SPHERE_BOX_RVA = 0x19D5300
SPHERE_CAPSULE_RVA = 0x19D57F0
BOX_BOX_RVA = 0x19D8CF0
CAPSULE_CAPSULE_RVA = 0x19DCF20
CAPSULE_CAPSULE_CORE_RVA = 0x19DCA50
PORTAL_RVA = 0x19C6520

SHAPE_VTABLES = {0x29C9BE8: 'sphere', 0x29C9AC8: 'box', 0x29C9B58: 'capsule', 0x29C9D80: 'hull'}
SUPPORT_RVAS = {'sphere': 0x18AB4B0, 'box': 0x18AB2E0, 'capsule': 0x18AB3B0, 'hull': 0x1949450}
CENTRE_RVAS = {'sphere': 0x18AAE30, 'box': 0x18AAE30, 'capsule': 0x18AAE30, 'hull': 0x18AF7B0}

# Kind pair -> (slot 1 RVA, slot 2 RVA, slot 4 RVA, forward pair if slot 1 is a geom-swap
# wrapper). Read from each TESTER_TABLE vtable (+8, +0x10, +0x20) in this image.
SLOT_TABLE = {
    (2, 2): (0x19D4DF0, 0x1163990, 0xFEC1B0, None),
    (2, 3): (0x19D5300, 0x1163990, 0xFEC1B0, None),
    (2, 4): (0x19D57F0, 0x1163990, 0xFEC1B0, None),
    (2, 5): (0x19C6520, 0x1163990, 0xFEC1B0, None),
    (2, 6): (0x198E230, 0x198F3B0, 0x198C8F0, (6, 2)),
    (2, 7): (0x198DD30, 0x198EEB0, 0x198C270, (7, 2)),
    (3, 2): (0x198E370, 0x198F4F0, 0x198CA90, (2, 3)),
    (3, 3): (0x19D8CF0, 0x1163990, 0xFEC1B0, None),
    (3, 4): (0x19C6520, 0x1163990, 0xFEC1B0, None),
    (3, 5): (0x19C6520, 0x1163990, 0xFEC1B0, None),
    (3, 6): (0x198DE70, 0x198EFF0, 0x198C410, (6, 3)),
    (3, 7): (0x198D970, 0x198EAF0, 0x198BD90, (7, 3)),
    (4, 2): (0x198E4B0, 0x198F630, 0x198CC30, (2, 4)),
    (4, 3): (0x198D5B0, 0x198E730, 0x198B8B0, (3, 4)),
    (4, 4): (0x19DCF20, 0x1163990, 0xFEC1B0, None),
    (4, 5): (0x19C6520, 0x1163990, 0xFEC1B0, None),
    (4, 6): (0x198DFB0, 0x198F130, 0x198C5B0, (6, 4)),
    (4, 7): (0x198DAB0, 0x198EC30, 0x198BF30, (7, 4)),
    (5, 2): (0x198E5F0, 0x198F770, 0x198CDD0, (2, 5)),
    (5, 3): (0x198D6F0, 0x198E870, 0x198BA50, (3, 5)),
    (5, 4): (0x198D830, 0x198E9B0, 0x198BBF0, (4, 5)),
    (5, 5): (0x19C6520, 0x1163990, 0xFEC1B0, None),
    (5, 6): (0x198E0F0, 0x198F270, 0x198C750, (6, 5)),
    (5, 7): (0x198DBF0, 0x198ED70, 0x198C0D0, (7, 5)),
    (6, 2): (0x19C8840, 0x19C8EC0, 0x19C7C40, None),
    (6, 3): (0x19CB1D0, 0x19CB990, 0x19CA3F0, None),
    (6, 4): (0x19CDDB0, 0x19CE540, 0x19CCF70, None),
    (6, 5): (0x19D3C30, 0x19D43F0, 0x19D2DE0, None),
    (7, 2): (0x19E33F0, 0x19E3430, 0x19E33B0, None),
    (7, 3): (0x19DF180, 0x19DF8C0, 0x19DE7C0, None),
    (7, 4): (0x19E1830, 0x19E1F10, 0x19E0E20, None),
    (7, 5): (0x19E46A0, 0x19E46E0, 0x19E4660, None),
}
VTABLE_TO_CELL = {vt: cell for cell, (vt, _entry, _fwd) in TESTER_TABLE.items()}
TERRAIN_SLOT8 = {cell: row[0] for cell, row in SLOT_TABLE.items() if row[3] is None and cell[0] in (6, 7)}


class TerrainSlot8Unavailable(NotImplementedError):
    """A terrain cell's slot 1 is not restated here."""


class PortalIterationLimit(RuntimeError):
    """The native portal loop has no iteration cap; the model stops at max_iterations."""


# --- lane helpers -------------------------------------------------------------------

def _w(mem, address):
    return struct.unpack('<I', bytes(mem.view(address, 4)))[0]


def _ld(mem, address):
    return list(struct.unpack('<4I', bytes(mem.view(address, 16))))


def _bc(x):
    return [x, x, x, x]


def _vadd(a, b, r): return [_add(x, y, r) for x, y in zip(a, b)]
def _vsub(a, b, r): return [_sub(x, y, r) for x, y in zip(a, b)]
def _vmul(a, b, r): return [_mul(x, y, r) for x, y in zip(a, b)]
def _vand(a, m): return [x & k for x, k in zip(a, m)]
def _vxor(a, k): return [x ^ k for x in a]
def _yzx(v): return [v[1], v[2], v[0], v[3]]       # shufps 0xc9
def _zxy(v): return [v[2], v[0], v[1], v[3]]       # shufps 0xd2


def _haddps(a, b, r):
    return [_add(a[0], a[1], r), _add(a[2], a[3], r), _add(b[0], b[1], r), _add(b[2], b[3], r)]


def _dot(a, b, m, r):
    """mulps a, b; andps M; haddps twice: ((p0+p1)+(p2+p3)), equal in all lanes."""
    p = _vand(_vmul(a, b, r), m)
    h = _haddps(p, p, r)
    return _add(h[0], h[1], r)


def _rows_dot(rows, v, m, r, v_first=False):
    """haddps(haddps(b0*v, b1*v), haddps(b2*v, b2*v)) & M: v in a row basis.

    v_first selects the mulps operand order (v * b instead of b * v)."""
    p0, p1, p2 = ((_vmul(v, rows[i], r) if v_first else _vmul(rows[i], v, r)) for i in range(3))
    h2 = _haddps(p2, p2, r)
    return _vand(_haddps(_haddps(p0, p1, r), h2, r), m)


def _apply(rows, s, r):
    """((b0*s.x + t) + b1*s.y) + b2*s.z, each scalar broadcast (shufps 0/0x55/0xaa)."""
    acc = _vadd(_vmul(rows[0], _bc(s[0]), r), rows[3], r)
    acc = _vadd(acc, _vmul(rows[1], _bc(s[1]), r), r)
    return _vadd(_vmul(rows[2], _bc(s[2]), r), acc, r)


def _maxps(a, b):
    """maxps a, b: a when a > b (ordered), else b."""
    return a if _lt(b, a) else b


def _all_le(a, b):
    return all(_le(x, y) for x, y in zip(a, b))


def _mask_words(mask):
    return list(struct.unpack('<4I', mask))


def _read_rows(mem, address):
    return [_ld(mem, address + 16 * k) for k in range(4)]


def _cross(p, q, r):
    """p.yzx*q.zxy - q.yzx*p.zxy (the emitted form of p x q)."""
    return _vsub(_vmul(_yzx(p), _zxy(q), r), _vmul(_yzx(q), _zxy(p), r), r)


# --- 0x19d4df0 (2,2) sphere-sphere --------------------------------------------------

def sphere_sphere_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse'):
    """|tA - tB|^2 <= (rB + rA)^2 (cmpleps, NaN fails)."""
    r, m = nan_rule, _mask_words(mask)
    rs = _add(_w(mem, shape_b + 0x40), _w(mem, shape_a + 0x40), r)       # addss rB, rA
    d = _vsub(_vand(rows_a[3], m), _vand(rows_b[3], m), r)
    return int(_le(_dot(d, d, m, r), _mul(rs, rs, r)))


# --- 0x19d5300 (2,3) sphere-box -----------------------------------------------------

def sphere_box_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse'):
    """Clamp-distance test in the box frame: sum(max(|l|-E, 0)^2) <= r^2."""
    r, m = nan_rule, _mask_words(mask)
    rad = _w(mem, shape_a + 0x40)
    r2 = _mul(rad, rad, r)
    d = _vsub(_vand(rows_a[3], m), _vand(rows_b[3], m), r)
    rows = [_vand(rows_b[k], m) for k in range(3)]
    ext = _vand(_ld(mem, shape_b + 0x40), m)
    local = _rows_dot(rows, d, m, r)
    over = [_maxps(_sub(x & ABS, e, r), 0) for x, e in zip(local, ext)]
    return int(_le(_dot(over, over, m, r), r2))


# --- 0x19d57f0 (2,4) sphere-capsule -------------------------------------------------

def sphere_capsule_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse'):
    """(l.x, max(|l.y|-h, 0), l.z) squared <= (rA + rc)^2, l = centre in capsule frame."""
    r, m = nan_rule, _mask_words(mask)
    d = _vsub(_vand(rows_a[3], m), _vand(rows_b[3], m), r)
    rows = [_vand(rows_b[k], m) for k in range(3)]
    big = _add(_w(mem, shape_a + 0x40), _w(mem, shape_b + 0x44), r)        # addss rA, rc
    local = _rows_dot(rows, d, m, r)
    over = _maxps(_sub(local[1] & ABS, _w(mem, shape_b + 0x40), r), 0)
    v = [local[0], over, local[2], 0]
    return int(_le(_dot(v, v, m, r), _mul(big, big, r)))


# --- 0x19dcf20 -> 0x19dca50 (4,4) capsule-capsule -------------------------------------

def capsule_capsule_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse',
                            trace=None):
    """Clamped segment-segment distance^2 <= (rA + rB)^2.

    Segment k: P = t - h*b1, D = 2*(h*b1). Parallel when |a*e - b*b| <= a*1e-5; then
    sN = 0, sD = e (not 1), tN = f, tD = e.
    """
    r, m = nan_rule, _mask_words(mask)
    fa = [_vand(x, m) for x in rows_a]
    fb = [_vand(x, m) for x in rows_b]
    u_a = _vmul(_bc(_w(mem, shape_a + 0x40)), fa[1], r)
    u_b = _vmul(_bc(_w(mem, shape_b + 0x40)), fb[1], r)
    p_a = _vsub(fa[3], u_a, r)
    d_a = _vmul(u_a, _bc(TWO), r)
    p_b = _vsub(fb[3], u_b, r)
    d_b = _vmul(u_b, _bc(TWO), r)
    w = _vsub(p_a, p_b, r)
    a = _dot(d_a, d_a, m, r)
    b = _dot(d_a, d_b, m, r)
    e = _dot(d_b, d_b, m, r)
    c = _dot(d_a, w, m, r)
    f = _dot(w, d_b, m, r)
    denom = _sub(_mul(a, e, r), _mul(b, b, r), r)
    path = []
    if _le(denom & ABS, _mul(a, PARALLEL_FACTOR, r)):
        path.append('parallel')
        s_n, s_d, t_n, t_d = 0, e, f, e
    else:
        s_n = _sub(_mul(f, b, r), _mul(c, e, r), r)
        t_n = _sub(_mul(a, f, r), _mul(c, b, r), r)
        s_d = denom
        if _lt(s_n, 0):
            path.append('s_low')
            s_n, t_n, t_d = 0, f, e
        elif _lt(denom, s_n):
            path.append('s_high')
            s_n, t_n, t_d = denom, _add(f, b, r), e
        else:
            t_d = denom
    if _lt(t_n, 0):
        path.append('t_low')
        tc, x = 0, c ^ SIGN
        sc = 0 if _lt(x, 0) else (ONE if _lt(a, x) else _div(x, a, r))
    elif _lt(t_d, t_n):
        path.append('t_high')
        tc, x = ONE, _add(c ^ SIGN, b, r)
        sc = 0 if _lt(x, 0) else (ONE if _lt(a, x) else _div(x, a, r))
    else:
        sc, tc = _div(s_n, s_d, r), _div(t_n, t_d, r)
    big = _add(_w(mem, shape_a + 0x44), _w(mem, shape_b + 0x44), r)
    diff = _vsub(_vadd(_vmul(d_a, _bc(sc), r), w, r), _vmul(_bc(tc), d_b, r), r)
    if trace is not None:
        trace.extend(path)
    return int(_le(_dot(diff, diff, m, r), _mul(big, big, r)))


# --- 0x19d8cf0 (3,3) box-box ----------------------------------------------------------

def box_box_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse', trace=None):
    """15-axis separating test with |R| + 1e-5. Returns 1 when no axis separates.

    Order: A faces (3 lanes at once), B faces, then A0xBj, A1xBj, A2xBj (3 lanes each).
    Every test is `|lhs| <= rhs` on all four lanes; a NaN lane separates.
    """
    r, m = nan_rule, _mask_words(mask)
    a0, a1, a2, at = (_vand(x, m) for x in rows_a)
    b0, b1, b2, bt = (_vand(x, m) for x in rows_b)
    e_a = _vand(_ld(mem, shape_a + 0x40), m)
    e_b = _vand(_ld(mem, shape_b + 0x40), m)

    def rd(x, y):
        return _dot(x, y, m, r)
    row0 = [rd(b0, a0), rd(b1, a0), rd(b2, a0), 0]          # A.b0 in B's basis
    row1 = [rd(a1, b0), rd(b1, a1), rd(b2, a1), 0]
    row2 = [rd(a2, b0), rd(b1, a2), rd(b2, a2), 0]
    t = _vsub(bt, at, r)
    t_a = _rows_dot([a0, a1, a2], t, m, r, v_first=True)
    ar0 = _vadd(_vand(row0, _bc(ABS)), list(SAT_EPSILON), r)
    ar1 = _vadd(_vand(row1, _bc(ABS)), list(SAT_EPSILON), r)
    ar2 = _vadd(_vand(row2, _bc(ABS)), list(SAT_EPSILON), r)
    rhs = _vadd(_rows_dot([ar0, ar1, ar2], e_b, m, r), e_a, r)
    if not _all_le(_vand(t_a, _bc(ABS)), rhs):
        _note(trace, 'axis_a')
        return 0
    ex, ey, ez = (_bc(e_a[k]) for k in range(3))
    tx, ty, tz = (_bc(t_a[k]) for k in range(3))
    proj = _vadd(_vmul(tz, row2, r), _vadd(_vmul(ty, row1, r), _vmul(tx, row0, r), r), r)
    rad = _vadd(_vadd(_vmul(ez, ar2, r), _vadd(_vmul(ey, ar1, r), _vmul(ex, ar0, r), r), r), e_b, r)
    if not _all_le(_vand(proj, _bc(ABS)), rad):
        _note(trace, 'axis_b')
        return 0
    ebc, ebd = _yzx(e_b), _zxy(e_b)

    def edge(ar, lhs, rad_a):
        rad_b = _vadd(_vmul(_yzx(ar), ebd, r), _vmul(_zxy(ar), ebc, r), r)
        return _all_le(_vand(lhs, _bc(ABS)), _vadd(rad_a, rad_b, r))
    if not edge(ar0, _vsub(_vmul(tz, row1, r), _vmul(ty, row2, r), r),
                _vadd(_vmul(ey, ar2, r), _vmul(ez, ar1, r), r)):
        _note(trace, 'axis_a0xb')
        return 0
    if not edge(ar1, _vsub(_vmul(tx, row2, r), _vmul(tz, row0, r), r),
                _vadd(_vmul(ex, ar2, r), _vmul(ez, ar0, r), r)):
        _note(trace, 'axis_a1xb')
        return 0
    if not edge(ar2, _vsub(_vmul(ty, row0, r), _vmul(tx, row1, r), r),
                _vadd(_vmul(ex, ar1, r), _vmul(ey, ar0, r), r)):
        _note(trace, 'axis_a2xb')
        return 0
    _note(trace, 'overlap')
    return 1


def _note(trace, label):
    if trace is not None:
        trace.append(label)


# --- shape virtuals used by 0x19c6520 --------------------------------------------------

def shape_class(mem, shape, image_base=IMAGE_BASE):
    vt = struct.unpack('<Q', bytes(mem.view(shape, 8)))[0] - image_base
    try:
        return SHAPE_VTABLES[vt]
    except KeyError:
        raise ValueError('shape %#x has vtable RVA %#x, not a modelled primitive' % (shape, vt)) from None


def shape_centre(mem, shape, *, image_base=IMAGE_BASE):
    """vt+0x68: 12 bytes written; the fourth lane read back is modelled as 0."""
    if shape_class(mem, shape, image_base) == 'hull':
        return [_w(mem, shape + 0x64), _w(mem, shape + 0x68), _w(mem, shape + 0x6C), 0]
    return [0, 0, 0, 0]


def shape_support(mem, shape, d, *, mask=XYZ_MASK, nan_rule='sse', image_base=IMAGE_BASE):
    """vt+0x40(shape, out, &d): the 16 bytes written to out (d is 4 lane words)."""
    r, m = nan_rule, _mask_words(mask)
    kind = shape_class(mem, shape, image_base)
    if kind == 'sphere':                                    # 0x18ab4b0
        rad = _w(mem, shape + 0x40)
        length = _sqrt(_dot(d, d, m, r))
        if _lt(0, length):
            return _vmul(d, _bc(_div(rad, length, r)), r)
        return [rad, 0, 0, 0]
    if kind == 'box':                                       # 0x18ab2e0
        ext = _vand(_ld(mem, shape + 0x40), m)
        return [e ^ SIGN if _lt(x, z) else e for x, e, z in zip(d, ext, ZERO4)]
    if kind == 'capsule':                                   # 0x18ab3b0
        length = _sqrt(_dot(d, d, m, r))
        out = _vmul(d, _bc(_div(_w(mem, shape + 0x44), length, r)), r)
        h = _w(mem, shape + 0x40)
        h = h ^ SIGN if _lt(d[1], ZERO4[1]) else h
        return [out[0], _add(h, out[1], r), out[2], out[3]]
    index = hull_support(mem, shape, d[:3], nan_rule)       # 0x1949450 -> 0x1949400
    verts = struct.unpack('<Q', bytes(mem.view(shape + 0x40, 8)))[0]
    v = [_w(mem, verts + 12 * index + 4 * k) for k in range(3)] + [0]
    return _vand(v, m)


# --- 0x19c6520 generic portal test ------------------------------------------------------

def portal_overlap(mem, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse',
                   max_iterations=4096, trace=None, image_base=IMAGE_BASE):
    """Minkowski portal refinement over B - A with the shapes' support functions.

    Returns 1 on overlap, 0 on separation. Tests in order (all `cmp*ps` on broadcast
    dot products; NaN takes the not-taken side):
      |v0| <= 2^-14 on all 4 lanes -> 1; v1.n <= 0 -> 0; |v1 x v0| <= 2^-14 (4 lanes) -> 1;
      v2.n <= 0 -> 0; portal search (v3.n <= 0 -> 0); refinement with normalised n:
      v1.n >= 0 -> 1; v4.n <= 0 -> 0 (as 0 <= -(v4.n)); (v4-v3).n <= 0 -> 0.
    """
    r, m = nan_rule, _mask_words(mask)
    a0, a1, a2, at = (_vand(x, m) for x in rows_a)
    b0, b1, b2, bt = (_vand(x, m) for x in rows_b)
    fa, fb = [a0, a1, a2, at], [b0, b1, b2, bt]

    def world(rows, s):
        return _apply(rows, s, r)

    def support(n):
        sa = shape_support(mem, shape_a, _rows_dot([a0, a1, a2], _vxor(n, SIGN), m, r),
                           mask=mask, nan_rule=r, image_base=image_base)
        wa = world(fa, sa)
        sb = shape_support(mem, shape_b, _rows_dot([b0, b1, b2], n, m, r),
                           mask=mask, nan_rule=r, image_base=image_base)
        return _vsub(world(fb, sb), wa, r)

    def note(label):
        if trace is not None:
            trace.append(label)

    ca = _vand(shape_centre(mem, shape_a, image_base=image_base), m)
    wa = _vadd(_vmul(_bc(ca[2]), a2, r),
               _vadd(_vadd(_vmul(a0, _bc(ca[0]), r), at, r), _vmul(_bc(ca[1]), a1, r), r), r)
    cb = _vand(shape_centre(mem, shape_b, image_base=image_base), m)
    wb = _vadd(_vmul(_bc(cb[2]), b2, r),
               _vadd(_vadd(_vmul(b0, _bc(cb[0]), r), bt, r), _vmul(_bc(cb[1]), b1, r), r), r)
    v0 = _vsub(wb, wa, r)
    if all(_le(x & ABS, PORTAL_EPSILON) for x in v0):
        note('centres_coincide')
        return 1
    n = _vxor(v0, SIGN)
    v1 = support(n)
    if _le(_dot(v1, n, m, r), 0):
        note('v1_miss')
        return 0
    n = _cross(v1, v0, r)
    if all(_le(x & ABS, PORTAL_EPSILON) for x in n):
        note('v1_on_axis')
        return 1
    v2 = support(n)
    if _le(_dot(v2, n, m, r), 0):
        note('v2_miss')
        return 0
    n = _cross(_vsub(v1, v0, r), _vsub(v2, v0, r), r)
    if _lt(0, _dot(v0, n, m, r)):
        note('swap_v1_v2')
        v1, v2, n = v2, v1, _vxor(n, SIGN)
    for _ in range(max_iterations):                        # portal discovery
        v3 = support(n)
        if _le(_dot(v3, n, m, r), 0):
            note('v3_miss')
            return 0
        if _lt(_dot(v0, _cross(v1, v3, r), m, r), 0):
            v2 = v3
            n = _cross(_vsub(v1, v0, r), _vsub(v3, v0, r), r)
            note('replace_v2')
            continue
        c2 = _vsub(_vmul(_zxy(v2), _yzx(v3), r), _vmul(_yzx(v2), _zxy(v3), r), r)   # v3 x v2
        if _lt(_dot(v0, c2, m, r), 0):
            v1 = v3
            n = _cross(_vsub(v3, v0, r), _vsub(v2, v0, r), r)
            note('replace_v1')
            continue
        break
    else:
        raise PortalIterationLimit('portal discovery')
    for _ in range(max_iterations):                        # refinement
        n = _cross(_vsub(v2, v1, r), _vsub(v3, v1, r), r)
        n = _vmul(n, _bc(_div(ONE, _sqrt(_dot(n, n, m, r)), r)), r)
        if _le(0, _dot(v1, n, m, r)):
            note('portal_hit')
            return 1
        v4 = support(n)
        if _le(0, _dot(v4, n, m, r) ^ SIGN):
            note('v4_miss')
            return 0
        if _le(_dot(_vsub(v4, v3, r), n, m, r), 0):
            note('refine_stall')
            return 0
        c = _cross(v4, v0, r)
        if _lt(0, _dot(c, v1, m, r)):
            if _lt(0, _dot(c, v2, m, r)):
                v1 = v4
            else:
                v3 = v4
        elif _lt(0, _dot(c, v3, m, r)):
            v2 = v4
        else:
            v1 = v4
        note('refine')
    raise PortalIterationLimit('refinement')


# --- dispatch ---------------------------------------------------------------------------

BODIES = {
    SPHERE_SPHERE_RVA: sphere_sphere_overlap,
    SPHERE_BOX_RVA: sphere_box_overlap,
    SPHERE_CAPSULE_RVA: sphere_capsule_overlap,
    BOX_BOX_RVA: box_box_overlap,
    CAPSULE_CAPSULE_RVA: capsule_capsule_overlap,
    PORTAL_RVA: portal_overlap,
}


def slot8_body(cell):
    """(slot-1 RVA of the body that finally runs, swapped?) for a kind pair."""
    slot1, _s2, _s4, forward = SLOT_TABLE[cell]
    if forward is not None:
        return SLOT_TABLE[forward][0], True
    return slot1, False


def cell_overlap(mem, cell, rows_a, rows_b, shape_a, shape_b, *, mask=XYZ_MASK, nan_rule='sse',
                 **options):
    """Slot 1 of the given kind pair on lane-word rows (4 rows x 4 lanes per frame).

    Swapped cells exchange the frames (fourth lanes cleared: native copies xyz only) and
    the shapes, then run the forward body.
    """
    body, swapped = slot8_body(cell)
    if body not in BODIES:
        raise TerrainSlot8Unavailable('slot 1 %#x of cell %r is a terrain body (not restated)' % (body, cell))
    if swapped:
        rows_a, rows_b = ([row[:3] + [0] for row in rows_b], [row[:3] + [0] for row in rows_a])
        shape_a, shape_b = shape_b, shape_a
    fn = BODIES[body]
    if fn not in (box_box_overlap, capsule_capsule_overlap, portal_overlap):
        options.pop('trace', None)
    if fn is not portal_overlap:
        options.pop('max_iterations', None)
        options.pop('image_base', None)
    return fn(mem, rows_a, rows_b, shape_a, shape_b, mask=mask, nan_rule=nan_rule, **options)


def tester_cell(mem, tester, image_base=IMAGE_BASE):
    vt = struct.unpack('<Q', bytes(mem.view(tester, 8)))[0] - image_base
    try:
        return VTABLE_TO_CELL[vt]
    except KeyError:
        raise ValueError('tester %#x has vtable RVA %#x, not a tester table entry' % (tester, vt)) from None


def pose_tester_overlap(mem, tester, geom, *, mask=XYZ_MASK, nan_rule='sse', image_base=IMAGE_BASE,
                        **options):
    """tester->vt[1](tester, geom) over flat memory: 0 or 1 (the native `al`)."""
    cell = tester_cell(mem, tester, image_base)
    rows_a = _read_rows(mem, geom)
    rows_b = _read_rows(mem, geom + 0x40)
    shape_a, shape_b = struct.unpack('<QQ', bytes(mem.view(geom + 0x80, 16)))
    return cell_overlap(mem, cell, rows_a, rows_b, shape_a, shape_b, mask=mask, nan_rule=nan_rule,
                        image_base=image_base, **options)


# --- flagged-neighbor service adapters ----------------------------------------------------

def _bits(x):
    return struct.unpack('<I', struct.pack('<f', x))[0]


def _rows_from_floats(basis, translation):
    return [[_bits(v) for v in row] + [0] for row in list(basis) + [translation]]


def pose_overlap_from_frames(mem, tester, frame_a, frame_b, shape_a, shape_b, *, mask=XYZ_MASK,
                             nan_rule='sse', image_base=IMAGE_BASE, **options):
    """frame = (3 basis rows, translation) of Python floats holding float32 values."""
    cell = tester_cell(mem, tester, image_base)
    return cell_overlap(mem, cell, _rows_from_floats(*frame_a), _rows_from_floats(*frame_b),
                        shape_a, shape_b, mask=mask, nan_rule=nan_rule, image_base=image_base, **options)


def _split12(world):
    return (world[0:3], world[3:6], world[6:9]), world[9:12]


def bind_pose_flagged_tester_services(mem, *, mask=XYZ_MASK, nan_rule='sse', image_base=IMAGE_BASE,
                                      max_iterations=4096, log=None):
    """Tester services for engine.pose_flagged_neighbor_update and _create.

    Returns a namespace with
      select_tester(factory, a, b) / select_collider(dispatcher, a, b): 0x18de680 over
          flat memory (the provider+0x68 object is the tester dispatcher);
      test_update(tester, world_a, world_b, a, b): for update_pose_flagged_neighbor
          (12-float world lists);
      test_create(tester, query): for create_pose_flagged_neighbor (query = (frame_a,
          frame_b, a, b)).
    Callers assign test_update or test_create to their own `test_overlap` attribute.
    `log`, when a list, receives (tester, cell, result) per call.
    """
    opts = dict(mask=mask, nan_rule=nan_rule, image_base=image_base, max_iterations=max_iterations)

    def select(dispatcher, a, b):
        return select_pose_tester(mem, dispatcher, a, b)

    def run(tester, fa, fb, a, b):
        result = pose_overlap_from_frames(mem, tester, fa, fb, a, b, **opts)
        if log is not None:
            log.append((tester, tester_cell(mem, tester, image_base), result))
        return result

    def test_update(tester, world_a, world_b, a, b):
        return run(tester, _split12(world_a), _split12(world_b), a, b)

    def test_create(tester, query):
        fa, fb, a, b = query
        return run(tester, fa, fb, a, b)

    return SimpleNamespace(select_tester=select, select_collider=select,
                           test_update=test_update, test_create=test_create)


__all__ = [
    'SLOT_TABLE', 'TERRAIN_SLOT8', 'BODIES', 'SHAPE_VTABLES', 'TerrainSlot8Unavailable',
    'PortalIterationLimit', 'sphere_sphere_overlap', 'sphere_box_overlap', 'sphere_capsule_overlap',
    'capsule_capsule_overlap', 'box_box_overlap', 'portal_overlap', 'shape_support', 'shape_centre',
    'cell_overlap', 'pose_tester_overlap', 'pose_overlap_from_frames', 'bind_pose_flagged_tester_services',
    'slot8_body', 'tester_cell', '_is_nan',
]
