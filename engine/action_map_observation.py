"""Bounded read-only compact action-map observer, not the full radix decoder.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Tagged action-map observation.
Unsupported roots are never reported as missing keys. No game calls or writes.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class MapObservation:
    status: str
    value_slot: int = 0
    action: int = 0
    count: int = 0


def observe_compact_map(read, root: int, key: int) -> MapObservation:
    """At most six reads, 528 bytes, two matching observations.

    Supports null root and inspected tag-1 leaves with 1..31 sorted keys.
    Tag-3 radix trees require another decoder. Matching copies do not pin memory
    or establish atomicity, lifetime, writer generation or ownership.
    """
    if any(type(x) is not int or not 0 <= x < 1 << 64 for x in (root, key)):
        raise ValueError('root and key must be uint64')
    if root == 0:
        return MapObservation('missing')
    if root & 7 != 1:
        return MapObservation('unsupported')
    base = root & ~7
    def get(offset, n):
        address=base+offset
        if address >= 1 << 64 or address+n > 1 << 64 or not base:
            raise ValueError('address overflow/null base')
        value=read(address,n)
        if not isinstance(value, bytes) or len(value)!=n:
            raise ValueError('incomplete read')
        return value
    def sample():
        last=struct.unpack('<Q',get(0,8))[0]
        if last >= 31:
            return MapObservation('unsupported'),last,()
        count=last+1
        keys=struct.unpack('<'+'Q'*count,get(8,count*8))
        if any(a>=b for a,b in zip(keys,keys[1:])):
            raise ValueError('unordered or duplicate keys')
        if key not in keys:
            return MapObservation('missing',count=count),last,keys
        index=keys.index(key)
        # Inspected value-area alignment tiers for last-index 0..30.
        offset=next(n for n in (2,3,4,6,8,12,16,24,32) if n>=count+1)
        slot=base+(offset+index)*8
        action=struct.unpack('<Q',get((offset+index)*8,8))[0]
        return MapObservation('found',slot,action,count),last,keys
    try:
        first,second=sample(),sample()
        return first[0] if first==second else MapObservation('unstable')
    except (OSError,ValueError,struct.error):
        return MapObservation('invalid')
