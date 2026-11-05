"""Sphere-vs-box, sphere-vs-capsule and sphere-vs-convex narrow-phase testers, and the
swapped-pair record flip.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase sphere testers and swap
wrapper". Static reads of the memory image (build-specific anchors):

- (2,3) entry 0x19d5260 -> core 0x19d4e50 (tail 0x19d5209): sphere vs box.
- (2,4) entry 0x19d5720 -> core 0x19d53b0: sphere vs capsule.
- (2,5) entry 0x19d5c90 -> core 0x19d58b0: sphere vs convex hull. The core calls
  0x18f0a70 (a GJK-style point query, 16 iterations) and, for a centre on or inside
  the hull, scans the hull's face planes.
- 0x1994f60(begin, end): flips every 0x30-byte record in [begin, end).
- Swapped entries (3,2) 0x198b400, (4,2) 0x198b590, (5,2) 0x198b720: identical code
  except the forward entry and the vtable stored into a stack tester object.

Kind identification (from the fields each core reads; kind numbers are the dispatcher's
shape+0x28 & 0x7fff):
- 3 box: extents xyz at shape+0x40/+0x44/+0x48 (one movups, masked). The sphere centre
  is clamped to +-extent along each frame row. Agrees with the box producer in
  LINK_SOLVER.md "Resource-pair dispatch lookup" (extent fields +0x40/44/48).
- 4 capsule: half-height h at shape+0x40, radius at shape+0x44. The segment runs from
  local (0,-h,0) to (0,+h,0), the frame's second row.
- 5 convex hull: vertex pointer at shape+0x40 (packed 12-byte float3), vertex count
  word at shape+0x48, optional support lookup at +0xc0/+0xd0/+0xe0..+0xe8 (read by the
  support routine 0x1949480), and a face-plane block pointer at shape+0x100 (block+8 =
  plane array, block+0x22 = u16 plane count, 0x14-byte planes nx, ny, nz, d, unused).

Recovered behavior restated here (lane-exact float32 on bit patterns):
- Each entry masks the eight geom rows with the XYZ mask. (2,3) and (2,5) pass the raw
  shape pointers and the core reads shape+0x40 itself; (2,4) passes shape+0x40, or 0
  for a null shape. No core null-checks; a null shape faults natively, and the model
  raises instead.
- No core reads the capacity argument. Each writes at most one record (even with
  capacity 0) and returns 0 or 1. Record +0x1c = 0, +0x2c = 0xffff0000.
- Normals point from shape A (the sphere) toward shape B.
- The swap wrapper builds a second geom with frames and shapes exchanged, calls the
  forward entry with the same out and capacity, then flips each returned record:
  normal xyz negated (sign-bit xor), +0x10..+0x1b exchanged with +0x20..+0x2b; depth and
  both feature words keep their values. Lane 3 of each copied frame row is not written
  by the wrapper (uninitialised stack); the entry's mask clears it under the standard
  mask. The model takes it as a parameter (default 0).

Supplied service: the (2,5) point query 0x18f0a70 is not restated. It is injected as
`point_query(frame_b_rows, shape_b, point) -> (dist, on_hull, on_point)` (three 4-lane
bit lists, the 0x30 bytes the core reads back at rsp+0x30). The harness runs it
natively and feeds its result in.

Float32 semantics follow engine.pose_contact_payload_update / pose_narrowphase_dispatch:
exact double then one rounding, no FTZ/DAZ, default NaN 0xffc00000, two-NaN choice by
`nan_rule` ('sse' manual, 'x87' emulator). minps/maxps return the second operand unless
the first compares strictly less/greater; cmpps is false on NaN.

Authored choices: function names and the (dist, on_hull, on_point) service signature
are ours. Nothing here claims equivalence with the original engine beyond the
validated fixtures.
"""
import struct

from engine.pose_contact_payload_update import XYZ_MASK, _add, _mul, _sub
from engine.pose_narrowphase_dispatch import (
    RECORD_STRIDE,
    SPHERE_FEATURE_WORD,
    _div,
    _hadd_sum,
    _le,
    _lt,
    _minps,
    _sqrt,
)

SPHERE_BOX_ENTRY_RVA, SPHERE_BOX_CORE_RVA = 0x19D5260, 0x19D4E50
SPHERE_CAPSULE_ENTRY_RVA, SPHERE_CAPSULE_CORE_RVA = 0x19D5720, 0x19D53B0
SPHERE_CONVEX_ENTRY_RVA, SPHERE_CONVEX_CORE_RVA = 0x19D5C90, 0x19D58B0
POINT_QUERY_RVA = 0x18F0A70
FLIP_RVA = 0x1994F60
SWAP_ENTRIES = {(3, 2): (0x198B400, (2, 3)), (4, 2): (0x198B590, (2, 4)), (5, 2): (0x198B720, (2, 5))}

SIGN = 0x80000000
ABS = 0x7FFFFFFF
ONE = 0x3F800000
FLT_MAX = 0x7F7FFFFF                       # RVA 0x1eba000
BOX_INSIDE_EPSILON = 0x38D1B717            # RVA 0x1e93ba0, 1e-4 (compared with dist^2)
CAPSULE_EPSILON = 0x36A7C5AC               # RVA 0x1ef69e0, 5e-6 (scalar)
CONVEX_EPSILON = 0x34000000                # RVA 0x1eeb1f0, 2^-23
CAPSULE_ZERO = 0                           # RVA 0x33368c0, zero (initializer 0x400c7ea0)
UNIT_AXES = ((ONE, 0, 0, 0), (0, ONE, 0, 0), (0, 0, ONE, 0))   # RVA 0x1e25250/0x1e25270/0x1df4060
POINT_QUERY_ITERATIONS = 16
FEATURE_ID = 0
SWAP_GEOM_ADDRESS = 0x7FFF000000000000   # authored: where the model places the swapped geom
NEGATE = SIGN                              # sign flip used by 0x1994f60


# --- lane helpers -------------------------------------------------------------------

def _maxps(a, b):
    """maxps a, b: a when a > b (ordered), else b."""
    return a if _lt(b, a) else b


def _bc(x):
    return [x, x, x, x]


def _vadd(a, b, r): return [_add(x, y, r) for x, y in zip(a, b)]
def _vsub(a, b, r): return [_sub(x, y, r) for x, y in zip(a, b)]
def _vmul(a, b, r): return [_mul(x, y, r) for x, y in zip(a, b)]
def _vand(a, m): return [x & k for x, k in zip(a, m)]
def _vneg(a): return [x ^ SIGN for x in a]


def _dot(a, b, m, r):
    """mulps a, b; andps mask; haddps twice -> (p0+p1)+(p2+p3)."""
    return _hadd_sum(_vand(_vmul(a, b, r), m), r)


def _record(n, depth, p_a, p_b):
    return [n[0], n[1], n[2], depth, p_a[0], p_a[1], p_a[2], FEATURE_ID, p_b[0], p_b[1], p_b[2],
            SPHERE_FEATURE_WORD]


def _m(mask):
    return list(struct.unpack('<4I', mask))


# --- sphere vs box (0x19d4e50) ---------------------------------------------------------

def sphere_box_core(radius, frame_a, extents, frame_b, mask=XYZ_MASK, nan_rule='sse'):
    """radius: bits at sphere+0x40; frames: four masked rows (b0, b1, b2, t);
    extents: the raw 4 lanes at box+0x40 (masked here, as the core does).
    Returns the 12 record words, or None (count 0).
    """
    r_, m = nan_rule, _m(mask)
    t_a, t_b = frame_a[3], frame_b[3]
    e = _vand(extents, m)
    d = _vsub(t_a, t_b, r_)
    local = [_dot(frame_b[k], d, m, r_) for k in range(3)]
    c = [_maxps(_minps(local[k], e[k]), e[k] ^ SIGN) for k in range(3)]
    closest = t_b
    for k in range(3):
        closest = _vadd(closest, _vmul(_bc(c[k]), frame_b[k], r_), r_)
    diff = _vsub(closest, t_a, r_)
    dist2 = _dot(diff, diff, m, r_)
    rr = _mul(radius, radius, r_)
    if not _le(dist2, rr):
        return None
    if _lt(BOX_INSIDE_EPSILON, dist2):
        length = _sqrt(dist2)
        n = [_div(x, length, r_) for x in diff]
        depth = _sub(length, radius, r_)
        p_a = _vsub(closest, _vmul(n, _bc(depth), r_), r_)
        return _record(n, depth, p_a, closest)
    # Centre within 1e-2 of the box or inside it: unmasked hadd tree on R*d.
    a = _vmul(frame_b[0], d, r_)
    b = _vmul(frame_b[1], d, r_)
    cc = _vmul(d, frame_b[2], r_)
    h1 = [_add(cc[0], cc[1], r_), _add(cc[2], cc[3], r_)] * 2
    h2 = [_add(a[0], a[1], r_), _add(a[2], a[3], r_), _add(b[0], b[1], r_), _add(b[2], b[3], r_)]
    loc = [_add(h2[0], h2[1], r_), _add(h2[2], h2[3], r_), _add(h1[0], h1[1], r_), _add(h1[2], h1[3], r_)]
    loc = _vand(loc, m)
    margin = [_sub(e[k], loc[k] & ABS, r_) for k in range(3)]
    if _lt(margin[0], margin[1]):
        axis = 0 if _lt(margin[0], margin[2]) else 2
    else:
        axis = 1 if _lt(margin[1], margin[2]) else 2
    sel = margin[axis]
    u = list(UNIT_AXES[axis])
    if _lt(loc[axis], 0):
        u = _vneg(u)
    n_w = _vadd(_vmul(frame_b[2], _bc(u[2]), r_),
                _vadd(_vmul(frame_b[1], _bc(u[1]), r_), _vmul(frame_b[0], _bc(u[0]), r_), r_), r_)
    depth = _add(sel, radius, r_) ^ SIGN
    p_b = _vadd(_vmul(_bc(sel), n_w, r_), t_a, r_)
    p_a = _vsub(t_a, _vmul(n_w, _bc(radius), r_), r_)
    return _record(_vneg(n_w), depth, p_a, p_b)


# --- sphere vs capsule (0x19d53b0) -----------------------------------------------------

def _capsule_perp(d):
    """Degenerate-branch axis choice (min |component| test against the zero constant)."""
    ax, ay, az = d[0] & ABS, d[1] & ABS, d[2] & ABS
    c4 = _lt(_sub(ay, ax, 'sse'), CAPSULE_ZERO)
    c6 = _lt(_sub(_minps(ax, ay), az, 'sse'), CAPSULE_ZERO)
    if c6:
        return [d[2], 0, d[0] ^ SIGN, 0] if c4 else [0, d[2], d[1] ^ SIGN, 0]
    return [d[1], d[0] ^ SIGN, 0, 0]


def sphere_capsule_core(radius_a, frame_a, half_height, radius_b, frame_b, mask=XYZ_MASK,
                        nan_rule='sse'):
    """radius_a: sphere+0x40; half_height, radius_b: capsule+0x40/+0x44 (bits)."""
    r_, m = nan_rule, _m(mask)
    t_a = frame_a[3]
    r0, r1, r2, t_b = frame_b
    neg_h = half_height ^ SIGN
    two_h = _add(half_height, half_height, r_)
    p0 = _vadd(_vmul(r2, _bc(0), r_),
               _vadd(_vadd(_vmul(r0, _bc(0), r_), t_b, r_), _vmul(r1, _bc(neg_h), r_), r_), r_)
    seg = _vadd(_vmul(r2, _bc(0), r_), _vadd(_vmul(r1, _bc(two_h), r_), _vmul(r0, _bc(0), r_), r_), r_)
    e = _vsub(t_a, p0, r_)
    t = _div(_dot(seg, e, m, r_), _dot(seg, seg, m, r_), r_)
    t = _maxps(_minps(t, ONE), 0)
    closest = _vadd(_vmul(seg, _bc(t), r_), p0, r_)
    diff = _vsub(closest, t_a, r_)
    rsum = _add(radius_b, radius_a, r_)
    dist2 = _dot(diff, diff, m, r_)
    if not _lt(dist2, _mul(rsum, rsum, r_)):
        return None
    threshold = _mul(_add(radius_a, radius_b, r_), CAPSULE_EPSILON, r_)
    if _le(dist2 & ABS, threshold):
        vec = _capsule_perp(seg)
        depth = 0
    else:
        vec = diff
        depth = _sub(_sqrt(dist2), rsum, r_)
    length = _sqrt(_dot(vec, vec, m, r_))
    inv = _div(ONE, length, r_)
    n = _vmul(vec, _bc(inv), r_)
    p_a = _vadd(_vmul(n, _bc(radius_a), r_), t_a, r_)
    p_b = _vsub(closest, _vmul(_bc(radius_b), n, r_), r_)
    return _record(n, depth, p_a, p_b)


# --- sphere vs convex (0x19d58b0) ------------------------------------------------------

def _plane_better(candidate, best):
    return _lt(candidate, best)


def sphere_convex_core(radius, frame_a, frame_b, query, planes, mask=XYZ_MASK, nan_rule='sse'):
    """query: (dist, on_hull, on_point) 4-lane bits from the supplied 0x18f0a70.
    planes: callable returning the raw (nx, ny, nz, d) words of the hull's face planes;
    only called when the centre is within 2^-23 of the hull (deep branch).
    """
    r_, m = nan_rule, _m(mask)
    t_a = frame_a[3]
    dist, on_hull, on_point = query
    if all(_lt(radius, dist[k]) for k in range(3)):
        return None
    if all(_lt(CONVEX_EPSILON, dist[k]) for k in range(3)):
        depth = _sub(dist[0], radius, r_)
        v = _vsub(on_hull, on_point, r_)
        inv = _div(ONE, _sqrt(_dot(v, v, m, r_)), r_)
        n = _vmul(v, _bc(inv), r_)
        p_a = _vadd(_vmul(n, _bc(radius), r_), t_a, r_)
        return _record(n, depth, p_a, on_hull)
    r0, r1, r2, t_b = frame_b
    best, best_n = _bc(FLT_MAX), [0, 0, 0, 0]
    for nx, ny, nz, d in planes():
        lm = _vand([nx, ny, nz, d], m)
        n_w = _vadd(_vmul(r2, _bc(lm[2]), r_),
                    _vadd(_vmul(r0, _bc(lm[0]), r_), _vmul(r1, _bc(lm[1]), r_), r_), r_)
        d_w = _add(_dot(t_b, n_w, m, r_), d, r_)
        n_m = _vand([n_w[0], n_w[1], n_w[2], d_w], m)
        s = _sub(_dot(t_a, n_m, m, r_), d_w, r_) ^ SIGN
        if all(_plane_better(s, best[k]) for k in range(3)):
            best, best_n = _bc(s), n_m
    p_b = _vadd(_vmul(best_n, best, r_), t_a, r_)
    p_a = _vadd(_vmul(_bc(radius ^ SIGN), best_n, r_), t_a, r_)
    depth = _add(best[0], radius, r_) ^ SIGN
    return _record(_vneg(best_n), depth, p_a, p_b)


# --- flat-memory entries --------------------------------------------------------------

def _rows(raw, m):
    return [[v & k for v, k in zip(struct.unpack_from('<4I', raw, 16 * r), m)] for r in range(4)]


def _u32(mem, address):
    return struct.unpack('<I', bytes(mem.view(address, 4)))[0]


def _entry(mem, geom, mask):
    m = _m(mask)
    raw = bytes(mem.view(geom, 0x90))
    shape_a, shape_b = struct.unpack_from('<QQ', raw, 0x80)
    if not shape_a or not shape_b:
        raise ValueError('null shape: the native core dereferences it')
    return _rows(raw[:0x40], m), _rows(raw[0x40:0x80], m), shape_a, shape_b


def _store(mem, out, words):
    if words is None:
        return 0
    mem.view(out, RECORD_STRIDE)[:] = struct.pack('<12I', *words)
    return 1


def sphere_box_tester(mem, geom, out, capacity=500, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d5260(tester, geom, out, capacity). capacity is never read."""
    fa, fb, sa, sb = _entry(mem, geom, mask)
    ext = list(struct.unpack('<4I', bytes(mem.view(sb + 0x40, 16))))
    return _store(mem, out, sphere_box_core(_u32(mem, sa + 0x40), fa, ext, fb, mask, nan_rule))


def sphere_capsule_tester(mem, geom, out, capacity=500, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d5720(tester, geom, out, capacity). capacity is never read."""
    fa, fb, sa, sb = _entry(mem, geom, mask)
    return _store(mem, out, sphere_capsule_core(_u32(mem, sa + 0x40), fa, _u32(mem, sb + 0x40),
                                                _u32(mem, sb + 0x44), fb, mask, nan_rule))


def convex_planes(mem, shape):
    """Face planes of a convex shape: block = shape+0x100 (q), array = block+8 (q),
    count = block+0x22 (u16), stride 0x14."""
    block = mem.q(shape + 0x100)
    base, count = mem.q(block + 8), mem.w(block + 0x22)
    return [struct.unpack('<4I', bytes(mem.view(base + 0x14 * k, 16))) for k in range(count)]


def sphere_convex_tester(mem, geom, out, capacity=500, *, point_query, mask=XYZ_MASK,
                         nan_rule='sse'):
    """0x19d5c90(tester, geom, out, capacity). point_query(frame_b_rows, shape_b, point)
    is the supplied 0x18f0a70 (16 iterations). capacity is never read."""
    fa, fb, sa, sb = _entry(mem, geom, mask)
    query = point_query(fb, sb, fa[3])
    words = sphere_convex_core(_u32(mem, sa + 0x40), fa, fb, query, lambda: convex_planes(mem, sb),
                               mask, nan_rule)
    return _store(mem, out, words)


# --- swap post-process (0x1994f60) and swapped entries ---------------------------------

def flip_contact_records(mem, begin, end):
    """0x1994f60(begin, end): per 0x30-byte record, negate normal xyz and exchange the
    point words +0x10..+0x1b with +0x20..+0x2b. Depth, +0x1c and +0x2c are kept."""
    for rec in range(begin, end, RECORD_STRIDE):
        raw = bytearray(mem.view(rec, RECORD_STRIDE))
        w = list(struct.unpack('<12I', raw))
        w[0:3] = [x ^ NEGATE for x in w[0:3]]
        w[4:7], w[8:11] = w[8:11], w[4:7]
        mem.view(rec, RECORD_STRIDE)[:] = struct.pack('<12I', *w)


def swapped_geom(raw, lane3=0):
    """The geom block the swap wrapper builds from the original 0x93 bytes: frameA' = old
    frameB rows (xyz copied, lane 3 = `lane3`), frameB' = old frameA, shapes exchanged,
    bytes +0x90..+0x92 copied unchanged."""
    out = bytearray(0x98)
    for r in range(4):
        out[0x10 * r:0x10 * r + 12] = raw[0x40 + 0x10 * r:0x40 + 0x10 * r + 12]
        out[0x40 + 0x10 * r:0x40 + 0x10 * r + 12] = raw[0x10 * r:0x10 * r + 12]
        struct.pack_into('<I', out, 0x10 * r + 12, lane3)
        struct.pack_into('<I', out, 0x40 + 0x10 * r + 12, lane3)
    a, b = struct.unpack_from('<QQ', raw, 0x80)
    struct.pack_into('<QQ', out, 0x80, b, a)
    out[0x90:0x93] = raw[0x90:0x93]
    return bytes(out)


def swapped_tester(forward, mem, geom, out, capacity=500, *, lane3=0, **kw):
    """Swap wrapper (3,2)/(4,2)/(5,2): forward tester on the swapped geom, then flip."""
    tmp = SWAP_GEOM_ADDRESS
    tmp_mem = _Overlay(mem, tmp, swapped_geom(bytes(mem.view(geom, 0x93)), lane3))
    count = forward(tmp_mem, tmp, out, capacity, **kw)
    flip_contact_records(mem, out, out + RECORD_STRIDE * count)
    return count


class _Overlay:
    """Read/write view over `mem` plus one scratch region for the swapped geom."""

    def __init__(self, mem, base, raw):
        self._mem, self._base, self._raw = mem, base, bytearray(raw)

    def view(self, address, size):
        if self._base <= address and address + size <= self._base + len(self._raw):
            o = address - self._base
            return memoryview(self._raw)[o:o + size]
        return self._mem.view(address, size)

    def q(self, address): return struct.unpack('<Q', bytes(self.view(address, 8)))[0]
    def w(self, address): return struct.unpack('<H', bytes(self.view(address, 2)))[0]


def bind_sphere_testers(*, point_query, mask=XYZ_MASK, nan_rule='sse'):
    """Kind pair -> tester(mem, geom, out, capacity) for the sphere rows and their swaps."""
    fwd = {
        (2, 3): lambda mem, g, o, c=500: sphere_box_tester(mem, g, o, c, mask=mask, nan_rule=nan_rule),
        (2, 4): lambda mem, g, o, c=500: sphere_capsule_tester(mem, g, o, c, mask=mask, nan_rule=nan_rule),
        (2, 5): lambda mem, g, o, c=500: sphere_convex_tester(mem, g, o, c, point_query=point_query,
                                                              mask=mask, nan_rule=nan_rule),
    }
    out = dict(fwd)
    for pair, (_, forward) in SWAP_ENTRIES.items():
        out[pair] = (lambda f: lambda mem, g, o, c=500: swapped_tester(f, mem, g, o, c))(fwd[forward])
    return out
