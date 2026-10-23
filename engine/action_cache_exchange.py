"""Recovered raw input-cache field exchange, preserving all bit patterns.

Evidence: INPUT_UPDATE_ORDER.md, Cache exchange around the holder cycle.
Detached disjoint snapshots only; no locks, pointer lifetime or atomicity claim.
"""

CACHE_SPAN = 0x818
EXCHANGED_RANGES = ((0x10,0x1e8),(0x1f0,0x210),(0x7c8,0x818))


def exchange_input_cache(left, right):
    """Return two snapshots with the native exchanged fields swapped.

    Each input is exactly 0x818 bytes. Bytes outside the exchanged ranges stay
    with their original snapshot. Same-identity native calls are no-ops; this
    API models distinct objects, not partially overlapping memory ranges.
    """
    if any(not isinstance(v,bytes) or len(v)!=CACHE_SPAN for v in (left,right)):
        raise ValueError('two exact 0x818-byte snapshots required')
    a,b=bytearray(left),bytearray(right)
    for start,end in EXCHANGED_RANGES:
        a[start:end],b[start:end]=right[start:end],left[start:end]
    return bytes(a),bytes(b)
