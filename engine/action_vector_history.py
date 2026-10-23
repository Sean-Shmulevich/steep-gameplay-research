"""Decoded outer input-history update, with an explicit feature-helper boundary.

Evidence: INPUT_TO_ACTION_ROUTE.md, "Context preamble and vector history".
Snapshot layout is build-specific. Detached stable input only; no native clock,
locking, source selection, or frame cadence is inferred.
"""
import math
import struct
from .action_sample import f32


def update_vector_history(snapshot, vector, *, now, update_features):
    """Shift ten raw vectors, invoke features, then shift magnitudes and times.

    update_features(shifted_snapshot, raw_vector) returns same-sized bytes. It
    represents original helper 0x9599a0 and must be explicitly supplied. A no-op
    is a substitute, not recovered complete history behavior. Input vector is
    stable for this call; native callbacks that mutate its source are excluded.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) < 0x308:
        raise ValueError('history bytes must cover offset 0x307')
    if not isinstance(vector, bytes) or len(vector) != 16:
        raise ValueError('four raw float32 lanes required')
    if type(now) is not int or not 0 <= now < 1 << 64:
        raise ValueError('opaque uint64 time required')
    lanes = [f32(x) for x in struct.unpack('<4f', vector)]
    squares = [f32(x*x) for x in lanes]
    length = f32(math.sqrt(f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))))
    value = bytearray(snapshot)
    value[0x70:0x100] = snapshot[0x60:0xf0]
    value[0x60:0x70] = vector
    result = update_features(bytes(value), vector)
    if not isinstance(result, bytes) or len(result) != len(snapshot):
        raise ValueError('feature callback must return same-size bytes')
    value = bytearray(result)
    value[0x2e4:0x308] = result[0x2e0:0x304]
    struct.pack_into('<f', value, 0x2e0, min(length, 1.0))
    value[8:0x50] = result[:0x48]
    struct.pack_into('<Q', value, 0, now)
    return bytes(value)
