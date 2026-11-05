"""Flat-memory contact payload updater, RVA 0x198fdc0, as called by pair contact generation.

Evidence: docs/reconstruction/LINK_SOLVER.md "Pair contact generation" (caller 0x18dd400,
call site 0x18dda92: rcx = payload, rdx = 0x14-byte pair descriptor on the caller stack,
r8 = owner+0x58 scratch records, r9d = handler count) and CENTRAL_IMPULSE.md
"Paired-frame payload update" (dict model engine.pose_link_update). Static read of
0x198fdc0..0x1990032: a leaf with no calls.

Recovered behavior (this module restates it over flat memory, register-level):

- On entry: old count c = payload+0x110; cached words w_k = payload+0x40+0x40k when
  c >u k (else 0), and old IDs payload+0x2c+0x40k, k = 0..3, are snapshotted.
- The pair descriptor's two body pointers give frames at body+0x40/+0x50/+0x60 (basis
  rows) and +0x70 (translation), each ANDed with the 16-byte XYZ mask at 0x3336890.
- For each of `count` 48-byte records (no upper bound; rows past the fourth run into
  payload+0x110 and beyond):
    row = payload + 0x10 + 0x40*i
    d   = (record.v10 & mask) - t1          (subps, 4 lanes)
    l1k = (b1k.x*d.x + b1k.y*d.y) + (b1k.z*d.z + b1k.w*d.w)   (mulps, haddps x2)
    same for record.v20 with body 2 -> l2
    row[0:48] = record[0:48]                (three 16-byte copies)
    row+0x10..0x18 = (l1 & mask).xyz;  row+0x20..0x28 = (l2 & mask).xyz
    row+0x38 = pair.u16@0x10; row+0x3a = pair.u16@0x12; row+0x34 = 0
    row+0x30 = cached word whose old ID equals record.u32@0x1c, testing k = 3,2,1,0 with
               later tests overriding (lowest matching k wins); 0 when none match
- Finally payload+0x110 = count. Row+0x3c..0x3f and rows >= count are untouched.

Every SSE lane op is restated on float32 bit patterns: round to nearest even, no
FTZ/DAZ (the harness MXCSR is 0x1f80), a single NaN operand is returned quieted, and an
invalid operation yields the default NaN 0xffc00000. When both operands are NaN the
choice is a parameter: 'sse' follows the Intel manual (first operand), 'x87' follows
the emulator used by the harness. Neither the live MXCSR nor the hardware two-NaN
choice is observed here.

Authored choices: the pair descriptor arrives as bytes (the service signature used by
pose_pair_contact_generation), records are read from flat memory per record, and
overlap between records, payload and pair is not modelled beyond native store order.
Native uses movaps on record+0x10/+0x20 and body+0x40..+0x70 (16-byte alignment); the
model does not check alignment.
"""
import struct

ROUTINE_RVA = 0x198FDC0
RECORD_STRIDE = 0x30
ROW_STRIDE = 0x40
ROWS_OFFSET = 0x10
COUNT_OFFSET = 0x110
# Runtime value of the XYZ mask at RVA 0x3336890 (zero in the memory image; set by an
# initializer, see CENTRAL_IMPULSE.md "Geometric four-record selection").
XYZ_MASK = b'\xff' * 12 + b'\x00' * 4
DEFAULT_NAN = 0xFFC00000


def _is_nan(bits):
    return (bits & 0x7F800000) == 0x7F800000 and (bits & 0x7FFFFF) != 0


def _to_float(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def _to_bits(value):
    try:
        return struct.unpack('<I', struct.pack('<f', value))[0]
    except OverflowError:
        return 0x7F800000 if value > 0 else 0xFF800000


def _is_snan(bits):
    return _is_nan(bits) and not bits & 0x400000


def _pick_nan(a, b, rule):
    """Two-operand NaN choice. a is the first (destination) operand.

    'sse': Intel SDM vol. 1 table 4-7 for SSE: the first NaN operand, quieted. Taken
    from the manual, not observed on hardware here.
    'x87': the rule of the QEMU softfloat inside Unicorn (pick_nan/pickNaN, x86 branch):
    an SNaN loses to a QNaN; between two NaNs of one kind the larger fraction wins, and
    on equal fractions a wins only when a is positive and b negative. The harness needs
    it because the emulator applies it to SSE lanes.
    """
    an, bn = _is_nan(a), _is_nan(b)
    if rule == 'sse' or not (an and bn):
        return (a if an else b) | 0x400000
    if _is_snan(a) != _is_snan(b):
        return (b if _is_snan(a) else a) | 0x400000
    fa, fb = a & 0x7FFFFF, b & 0x7FFFFF
    a_larger = fa > fb or (fa == fb and (a >> 31) < (b >> 31))
    return (a if a_larger else b) | 0x400000


def _op(a, b, fn, rule):
    """One SSE lane: NaN operands by `rule`, else exact double then one f32 rounding."""
    if _is_nan(a) or _is_nan(b):
        return _pick_nan(a, b, rule)
    r = fn(_to_float(a), _to_float(b))
    if r != r:
        return DEFAULT_NAN
    return _to_bits(r)


def _sub(a, b, rule): return _op(a, b, lambda x, y: x - y, rule)
def _mul(a, b, rule): return _op(a, b, lambda x, y: x * y, rule)
def _add(a, b, rule): return _op(a, b, lambda x, y: x + y, rule)


def _lanes(raw, mask):
    return [v & m for v, m in zip(struct.unpack('<4I', bytes(raw)), mask)]


def _frame(mem, body, mask):
    return [_lanes(mem.view(body + 0x40 + 0x10 * r, 16), mask) for r in range(4)]


def transform_pose_contact_point(rows, point, nan_rule='sse'):
    """Lane bits of (point - t) through basis rows: products, then haddps pair order.

    rows: four masked 4-lane bit lists (b0, b1, b2, t); point: masked 4-lane bits.
    Returns 4 lanes (the fourth duplicates the third, as haddps xmm,xmm2 leaves it).
    """
    d = [_sub(p, t, nan_rule) for p, t in zip(point, rows[3])]
    out = []
    for r in range(3):
        p = [_mul(rows[r][k], d[k], nan_rule) for k in range(4)]
        out.append(_add(_add(p[0], p[1], nan_rule), _add(p[2], p[3], nan_rule), nan_rule))
    return out + [out[2]]


def update_pose_contact_payload(mem, payload, pair, records, count, *, mask=XYZ_MASK, nan_rule='sse'):
    """0x198fdc0(payload, pair, records, count) over flat memory.

    pair: the 0x14-byte descriptor (first body q, second body q, u16 i, u16 j).
    nan_rule: 'sse' (manual rule, default) or 'x87' (emulator rule) for two-NaN lanes.
    """
    m = struct.unpack('<4I', mask)
    first, second, index_a, index_b = struct.unpack_from('<QQHH', pair)
    old = mem.d(payload + COUNT_OFFSET)
    ids = [mem.d(payload + 0x2C + ROW_STRIDE * k) for k in range(4)]
    cached = [mem.d(payload + 0x40 + ROW_STRIDE * k) if old > k else 0 for k in range(4)]
    frame_a = _frame(mem, first, m)
    frame_b = _frame(mem, second, m)
    count &= 0xFFFFFFFF
    for i in range(count):
        record = records + RECORD_STRIDE * i
        row = payload + ROWS_OFFSET + ROW_STRIDE * i
        feature = mem.d(record + 0x1C)
        local_a = transform_pose_contact_point(frame_a, _lanes(mem.view(record + 0x10, 16), m), nan_rule)
        local_b = transform_pose_contact_point(frame_b, _lanes(mem.view(record + 0x20, 16), m), nan_rule)
        for k in range(3):
            mem.view(row + 0x10 * k, 16)[:] = bytes(mem.view(record + 0x10 * k, 16))
        local_a = [v & mk for v, mk in zip(local_a, m)]
        local_b = [v & mk for v, mk in zip(local_b, m)]
        mem.view(row + 0x10, 12)[:] = struct.pack('<3I', *local_a[:3])
        mem.view(row + 0x20, 12)[:] = struct.pack('<3I', *local_b[:3])
        mem.put('<H', row + 0x38, index_a)
        mem.put('<H', row + 0x3A, index_b)
        mem.set_d(row + 0x34, 0)
        value = 0
        for k in (3, 2, 1, 0):
            if feature == ids[k]:
                value = cached[k]
        mem.set_d(row + 0x30, value)
    mem.set_d(payload + COUNT_OFFSET, count)


def bind_pose_contact_payload_update(mem, *, mask=XYZ_MASK, nan_rule='sse'):
    """Service with the pose_pair_contact_generation signature (payload, pair, scratch, count)."""
    def update_payload(payload, pair, scratch, count):
        update_pose_contact_payload(mem, payload, pair, scratch, count, mask=mask, nan_rule=nan_rule)
    return update_payload
