"""Recovered root-cache edge timestamps after selected-device publication.

Evidence: INPUT_UPDATE_ORDER.md, Root-cache edge timestamps.
This cache differs from the separate 256-key/20-byte packet service cache.
"""
import struct
from engine.action_cache_exchange import CACHE_SPAN


def stamp_input_cache(snapshot, now):
    """Advance clocks and stamp 32 ordinary plus 8 derived rising edges.

    now is an explicit opaque uint64 timer value. No monotonicity or unit
    conversion is imposed. Held inputs and falling edges retain their stamps.
    The caller must populate current/previous derived bytes before this step.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) != CACHE_SPAN:
        raise ValueError('exact 0x818-byte snapshot required')
    if type(now) is not int or not 0 <= now < 1 << 64:
        raise ValueError('uint64 timer value required')
    result = bytearray(snapshot)
    result[0x50:0x58] = snapshot[0x58:0x60]
    struct.pack_into('<Q', result, 0x58, now)
    for current, previous, stamps, count in ((0x30, 0x10, 0x60, 32),
                                             (0x7c8, 0x7d0, 0x7d8, 8)):
        for index in range(count):
            if snapshot[current+index] and not snapshot[previous+index]:
                struct.pack_into('<Q', result, stamps+index*8, now)
    return bytes(result)
