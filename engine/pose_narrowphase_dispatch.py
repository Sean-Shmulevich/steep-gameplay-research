"""Narrow-phase tester table, tester selection and the sphere-sphere tester.

Evidence: docs/reconstruction/LINK_SOLVER.md "Narrow-phase tester table and
sphere-sphere tester". Static reads of:

- 0x18dc300: the provider constructor allocates the 0x208-byte dispatcher, stores
  vtable 0x29ca780, calls 0x198cf70 and keeps it at provider+0x68 (already recorded in
  "Resource-pair dispatch lookup" and checked live in "Live thread and lock
  observation").
- 0x18de680, the dispatcher's vtable slot 1 (vt[8]):
      return *(dispatcher + 8 + 8*((shapeA.w28 & 0x7fff)*8 + (shapeB.w28 & 0x7fff)))
  There is no bound check: a masked kind above 7 indexes past the 64-entry table.
  engine.pose_contact_dispatch.select_contact_handler is the list-based API with an
  authored range guard; select_pose_tester here is the flat-memory binding, which
  keeps the unchecked read (an unmapped read raises KeyError).
- 0x198cf70: memset(dispatcher+8, 0, 0x200), then one 8-byte, 16-aligned allocation
  (tag 10) per filled cell, each storing a tester vtable. A failed allocation stores 0.
  Cells with a kind of 0 or 1, and the terrain-terrain cells (6,6) (6,7) (7,6) (7,7),
  stay null.
- 0x19d4d20 (the (2,2) tester's vt[0x18]) and its core 0x19d4bd0: sphere-sphere.

Kinds: 2 is a sphere (radius float at shape+0x40, established here by the
sphere-sphere core). Kind 3 is the box and kind 7 the grid terrain of earlier resource
evidence ("Resource-pair dispatch lookup"); 6 and 7 are the kinds 0x18dd400 routes to
its terrain wrappers. Kinds 4 and 5 are not identified in this module.

Calling convention of every tester slot 3 (vt[0x18]): (tester, geom, out, capacity),
where geom is the 0x93-byte block built by 0x18dd400: frameA rows at +0x00..+0x3f,
frameB rows at +0x40..+0x7f (basis rows then translation), shapeA at +0x80, shapeB at
+0x88. The caller passes capacity 500 and owner+0x58 as `out`. Records are 0x30 bytes.

The sphere-sphere tester ignores the capacity argument and returns 0 or 1.

Float32 lane semantics follow engine.pose_contact_payload_update: exact double then
one rounding, no FTZ/DAZ, default NaN 0xffc00000. Two-NaN lane choice is a
parameter ('sse' manual rule or 'x87' emulator rule); with the standard XYZ mask a
NaN input makes the test fail before any NaN reaches a stored lane, so the choice
matters only for non-standard masks.

Authored choices: the table is described by kind pair, not by vtable address as a
portable field; vtable and code addresses are evidence anchors for this build only.
"""
import math
import struct

from engine.pose_contact_payload_update import (
    DEFAULT_NAN,
    XYZ_MASK,
    _add,
    _is_nan,
    _mul,
    _pick_nan,
    _sub,
    _to_bits,
    _to_float,
)

SELECT_RVA = 0x18DE680
INIT_RVA = 0x198CF70
DISPATCHER_VTABLE_RVA = 0x29CA780
TABLE_OFFSET = 8
KIND_MASK = 0x7FFF
RECORD_STRIDE = 0x30
SPHERE_EPSILON_BITS = 0x36A7C5AC          # float32 at RVA 0x1ef69e0, about 5e-6
FALLBACK_NORMAL = (0, 0, 0x3F800000, 0)   # RVA 0x1df4060: (0, 0, 1, 0)
SPHERE_FEATURE_WORD = 0xFFFF0000          # record +0x2c
SPHERE_SPHERE_ENTRY_RVA = 0x19D4D20
SPHERE_SPHERE_CORE_RVA = 0x19D4BD0

# Kind pair -> (tester vtable RVA, slot-3 entry RVA, forward pair when the entry swaps).
# Read from 0x198cf70; slot values from each vtable. Swapped entries call the forward
# entry and then 0x1994f60.
TESTER_TABLE = {
    (2, 2): (0x29CB1C0, 0x19D4D20, None),
    (2, 3): (0x29CB1E8, 0x19D5260, None),
    (2, 4): (0x29CB210, 0x19D5720, None),
    (2, 5): (0x29CB238, 0x19D5C90, None),
    (2, 6): (0x29CB3F0, 0x198B270, None),
    (2, 7): (0x29CB418, 0x198AC30, None),
    (3, 2): (0x29CB440, 0x198B400, (2, 3)),
    (3, 3): (0x29CB260, 0x19D8CD0, None),
    (3, 4): (0x29CB288, 0x19DB670, None),
    (3, 5): (0x29CB2B0, 0x19DBBA0, None),
    (3, 6): (0x29CB468, 0x198ADC0, None),
    (3, 7): (0x29CB490, 0x198A780, None),
    (4, 2): (0x29CB4B8, 0x198B590, (2, 4)),
    (4, 3): (0x29CB4E0, 0x198A2D0, (3, 4)),
    (4, 4): (0x29CB2D8, 0x19DCD40, None),
    (4, 5): (0x29CB300, 0x19DDBC0, None),
    (4, 6): (0x29CB508, 0x198AF50, None),
    (4, 7): (0x29CB530, 0x198A910, None),
    (5, 2): (0x29CB558, 0x198B720, (2, 5)),
    (5, 3): (0x29CB580, 0x198A460, (3, 5)),
    (5, 4): (0x29CB5A8, 0x198A5F0, (4, 5)),
    (5, 5): (0x29CB328, 0x19DDE00, None),
    (5, 6): (0x29CB5D0, 0x198B0E0, None),
    (5, 7): (0x29CB5F8, 0x198AAA0, None),
    (6, 2): (0x29CB120, 0x19C7050, None),
    (6, 3): (0x29CB148, 0x19C9640, None),
    (6, 4): (0x29CB170, 0x19CC160, None),
    (6, 5): (0x29CB198, 0x19D1FA0, None),
    (7, 2): (0x29CB3A0, 0x19E3360, None),
    (7, 3): (0x29CB350, 0x19DDE20, None),
    (7, 4): (0x29CB378, 0x19E0430, None),
    (7, 5): (0x29CB3C8, 0x19E4610, None),
}

# Allocation order in 0x198cf70 (table cell order: row-major by kind pair).
INIT_ORDER = sorted(TESTER_TABLE)


def table_cell_offset(kind_a, kind_b):
    """Byte offset of the cell 0x18de680 reads, after masking both kinds with 0x7fff."""
    return TABLE_OFFSET + 8 * ((kind_a & KIND_MASK) * 8 + (kind_b & KIND_MASK))


def select_pose_tester(mem, dispatcher, shape_a, shape_b):
    """0x18de680(dispatcher, shapeA, shapeB): the stored tester pointer (may be 0)."""
    kind_a = mem.view(shape_a + 0x28, 2)
    kind_b = mem.view(shape_b + 0x28, 2)
    ka = struct.unpack('<H', bytes(kind_a))[0]
    kb = struct.unpack('<H', bytes(kind_b))[0]
    return struct.unpack('<Q', bytes(mem.view(dispatcher + table_cell_offset(ka, kb), 8)))[0]


def build_pose_tester_table(mem, dispatcher, allocate, image_base=0x140000000):
    """0x198cf70(dispatcher) with a supplied allocator.

    allocate(size, align, tag) -> address or 0. Called once per filled cell in
    INIT_ORDER with (8, 16, 10). Stores the vtable VA into each allocation and the
    allocation (or 0) into the cell. Returns the list of allocations.
    """
    mem.view(dispatcher + TABLE_OFFSET, 0x200)[:] = bytes(0x200)
    made = []
    for pair in INIT_ORDER:
        obj = allocate(8, 16, 10)
        if obj:
            mem.view(obj, 8)[:] = struct.pack('<Q', image_base + TESTER_TABLE[pair][0])
        mem.view(dispatcher + table_cell_offset(*pair), 8)[:] = struct.pack('<Q', obj)
        made.append(obj)
    return made


# --- float32 lane helpers beyond the shared add/sub/mul ---------------------------

def _div(a, b, rule):
    if _is_nan(a) or _is_nan(b):
        return _pick_nan(a, b, rule)
    x, y = _to_float(a), _to_float(b)
    if y == 0.0:
        if x == 0.0:
            return DEFAULT_NAN
        sign = (a ^ b) & 0x80000000
        return sign | 0x7F800000
    if math.isinf(x) and math.isinf(y):
        return DEFAULT_NAN
    return _to_bits(x / y)


def _sqrt(a):
    if _is_nan(a):
        return a | 0x400000
    if a == 0x80000000:
        return a
    if a & 0x80000000:
        return DEFAULT_NAN
    x = _to_float(a)
    if math.isinf(x):
        return a
    return _to_bits(math.sqrt(x))


def _lt(a, b):
    """cmpltps lane: false when either operand is NaN."""
    if _is_nan(a) or _is_nan(b):
        return False
    return _to_float(a) < _to_float(b)


def _le(a, b):
    if _is_nan(a) or _is_nan(b):
        return False
    return _to_float(a) <= _to_float(b)


def _minps(a, b):
    """minps a, b: a when a < b (ordered), else b (also for NaN and equal zeros)."""
    return a if _lt(a, b) else b


def _hadd_sum(v, rule):
    """haddps v,v twice: (v0 + v1) + (v2 + v3)."""
    return _add(_add(v[0], v[1], rule), _add(v[2], v[3], rule), rule)


# --- sphere-sphere ------------------------------------------------------------------

def sphere_sphere_core(radius_a, frame_a, radius_b, frame_b, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d4bd0 on lane bits. Frames are four already-masked 4-lane rows; only row 3
    (translation) is read. Returns None (count 0) or the 12 record words.
    """
    m = struct.unpack('<4I', mask)
    t_a, t_b = frame_a[3], frame_b[3]
    d = [_sub(b, a, nan_rule) for a, b in zip(t_a, t_b)]                      # tB - tA
    sq = [_mul(x, x, nan_rule) & mk for x, mk in zip(d, m)]
    dist2 = _hadd_sum(sq, nan_rule)
    rsum = _add(radius_b, radius_a, nan_rule)                                 # bcast rB + bcast rA
    if not _le(dist2, _mul(rsum, rsum, nan_rule)):
        return None
    eps = _mul(_add(radius_b, radius_a, nan_rule), SPHERE_EPSILON_BITS, nan_rule)  # addss, mulss
    dist = _sqrt(dist2)
    if _lt(eps, dist):
        n = [_div(x, dist, nan_rule) for x in d]
        p_a = [_add(t, _mul(x, radius_a, nan_rule), nan_rule) for t, x in zip(t_a, n)]
        p_b = [_sub(t, _mul(x, radius_b, nan_rule), nan_rule) for t, x in zip(t_b, n)]
    else:
        n = list(FALLBACK_NORMAL)
        p_a, p_b = list(t_a), list(t_b)
    depth = _minps(_sub(dist, rsum, nan_rule), 0)
    return [n[0], n[1], n[2], depth, p_a[0], p_a[1], p_a[2], 0, p_b[0], p_b[1], p_b[2],
            SPHERE_FEATURE_WORD]


def _masked_rows(raw, m):
    return [[v & mk for v, mk in zip(struct.unpack_from('<4I', raw, 16 * r), m)] for r in range(4)]


def sphere_sphere_tester(mem, geom, out, capacity=500, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x19d4d20(tester, geom, out, capacity) over flat memory: returns the count.

    The entry wrapper copies and masks all eight geom rows, passes shape+0x40 (or a null
    pointer for a null shape) as each radius pointer and forwards `capacity`, which the
    core never reads. A null shape would fault natively; this model raises instead.
    """
    m = struct.unpack('<4I', mask)
    raw = bytes(mem.view(geom, 0x90))
    frame_a = _masked_rows(raw[0x00:0x40], m)
    frame_b = _masked_rows(raw[0x40:0x80], m)
    shape_a, shape_b = struct.unpack_from('<QQ', raw, 0x80)
    if not shape_a or not shape_b:
        raise ValueError('null shape: the native core dereferences address 0')
    radius_a = struct.unpack('<I', bytes(mem.view(shape_a + 0x40, 4)))[0]
    radius_b = struct.unpack('<I', bytes(mem.view(shape_b + 0x40, 4)))[0]
    words = sphere_sphere_core(radius_a, frame_a, radius_b, frame_b, mask, nan_rule)
    if words is None:
        return 0
    mem.view(out, RECORD_STRIDE)[:] = struct.pack('<12I', *words)
    return 1
