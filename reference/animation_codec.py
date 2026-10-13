"""Small Studio-documented codec primitives, tested with invented inputs only."""
import math
import struct


def quaternion32(word):
    if not isinstance(word, int) or not 0 <= word <= 0xffffffff:
        raise ValueError("Expected unsigned 32-bit integer")
    omitted = word >> 30
    values = [((word >> shift) & 1023) - 511 for shift in (20, 10, 0)]
    values = [v / (511 * math.sqrt(2)) for v in values]
    values.insert(omitted, math.sqrt(max(0., 1. - sum(v*v for v in values))))
    return tuple(values)


def time_keys(payload, count, format_id):
    """Return integer ticks and consumed bytes; caller owns tick-to-time conversion."""
    if count < 1 or format_id not in (0, 1, 2):
        raise ValueError("Invalid count or format")
    if count == 1:
        return [0], 0
    if format_id in (0, 1):
        size = (count - 1) * (format_id + 1)
        if len(payload) < size:
            raise ValueError("Truncated times")
        values = list(payload[:size]) if format_id == 0 else list(struct.unpack('<' + 'H'*(count-1), payload[:size]))
        if any(b < a for a, b in zip([0] + values, values)):
            raise ValueError("Descending time keys")
        return [0] + values, size
    if not payload:
        raise ValueError("Missing mask mode")
    shift, size = payload[0] >> 6, payload[0] & 63
    if not size or len(payload) < size + 1:
        raise ValueError("Truncated or empty mask")
    mask = int.from_bytes(payload[1:1+size], 'little')
    if not mask & 1 or mask.bit_count() != count:
        raise ValueError("Mask count/first-key mismatch")
    return [i << shift for i in range(size*8) if mask & (1 << i)], size + 1
