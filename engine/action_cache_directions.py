"""Recovered vector-to-direction bytes and the composed publication tail.

Evidence: INPUT_UPDATE_ORDER.md, Derived directional inputs.
This does not poll devices or choose the selected cache.
"""
import struct
from engine.action_cache_exchange import CACHE_SPAN
from engine.action_cache_publication import publish_selected_cache
from engine.action_cache_timestamps import stamp_input_cache

DIRECTION_THRESHOLD = struct.unpack('<f', bytes.fromhex('9a99993e'))[0]


def derive_input_directions(snapshot):
    """Copy eight derived bytes to previous, then choose at most one per XY pair.

    Strict abs(component)>float32(0.3); ties choose Y. Slots per vector are
    negative Y, negative X, positive Y, positive X. Z/W do not participate.
    NaN comparisons follow the original unordered branch outcomes; this models
    stored results, not processor floating-point exception flags or traps.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) != CACHE_SPAN:
        raise ValueError('exact 0x818-byte snapshot required')
    result = bytearray(snapshot)
    result[0x7d0:0x7d8] = snapshot[0x7c8:0x7d0]
    result[0x7c8:0x7d0] = bytes(8)
    for vector_index, offset in enumerate((0x1f0, 0x200)):
        x, y = struct.unpack_from('<2f', snapshot, offset)
        ax, ay = abs(x), abs(y)
        if ax > DIRECTION_THRESHOLD or ay > DIRECTION_THRESHOLD:
            if ax > ay:
                direction = 3 if x > 0 else 1
            else:
                direction = 2 if y > 0 else 0
            result[0x7c8 + vector_index*4 + direction] = 1
    return bytes(result)


def publish_derived_and_stamp(root, selected, now):
    """Compose selected publication, derived directions and edge stamping.

    Explicit stable cache snapshots and opaque uint64 timer value. This is the
    known root-update tail, not the complete device update or scheduler loop.
    """
    return stamp_input_cache(derive_input_directions(
        publish_selected_cache(root, selected)), now)
