"""Recovered cached boolean query gates; device update producers remain separate.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Cached boolean source queries.
Callbacks preserve native read order and permit changed values between lookups.
"""
import struct


def special_timestamp_slot(query_id, swapped):
    """Index into the ten uint64 fields beginning at service+0x1268."""
    if not 240 <= query_id <= 249:raise ValueError('special query ID required')
    return ((1 if swapped else 0), (0 if swapped else 1), 2, 8, 9, 3, 4, 5, 6, 7)[query_id-240]


def special_button_state(query_id, packet, *, swapped):
    """Packet is 20 bytes starting at service+0x21c; no device identity inferred."""
    if not isinstance(packet,bytes) or len(packet)!=20:raise ValueError('20 packet bytes required')
    if not 240 <= query_id <= 249:return False
    index=query_id-240
    if index in (3,4):
        value=struct.unpack_from('<i',packet,8)[0]
        return value>0 if index==3 else value<0
    offset=(13 if swapped else 12) if index==0 else (12 if swapped else 13) if index==1 else 14 if index==2 else index+10
    return bool(packet[offset]&128)


def query_cached_button(query_id, *, owners, requested_owner, enabled, cutoff,
                        resolve_index, timestamp, key_byte, special_timestamp,
                        special_value):
    """Return bool with explicit ownership, timestamp and cache dependencies.

    resolve_index is called twice on the ordinary accepted path. timestamp(-1)
    represents the original preceding-slot read for an unmapped ID; it must not
    be silently converted to a missing-value fallback. All times are uint64
    comparison values; physical units are not established.
    """
    if type(query_id) is not int or not 0<=query_id<1<<32:raise ValueError('uint32 query ID required')
    if type(cutoff) is not int or not 0<=cutoff<1<<64:raise ValueError('uint64 cutoff required')
    owners=tuple(owners)
    if owners and owners[-1]!=requested_owner:return False
    special=240<=query_id<=249
    stamp=special_timestamp(query_id) if special else timestamp(resolve_index(query_id))
    if type(stamp) is not int or not 0<=stamp<1<<64:raise ValueError('uint64 timestamp required')
    if stamp<=cutoff or query_id==65535 or not enabled:return False
    if special:return bool(special_value(query_id))
    index=resolve_index(query_id)
    return False if index==-1 else bool(key_byte(index))


def release_button_owner(owners, target, *, cutoff, current_timestamp):
    """Remove the last matching owner; top removal advances the freshness cutoff.

    This is detached sequence arithmetic, not a synchronization/lifetime API.
    Duplicate owners remain distinct. The original compacting tail copy is
    represented by tuple deletion; unused storage beyond the new count is not.
    """
    owners=tuple(owners)
    if len(owners)>65535:raise ValueError('uint16 owner count required')
    for value in (*owners,target,cutoff,current_timestamp):
        if type(value) is not int or not 0<=value<1<<64:raise ValueError('uint64 owner/time required')
    for index in range(len(owners)-1,-1,-1):
        if owners[index]==target:
            return dict(owners=owners[:index]+owners[index+1:],
                        cutoff=current_timestamp if index==len(owners)-1 else cutoff,
                        removed_index=index)
    return dict(owners=owners,cutoff=cutoff,removed_index=None)
