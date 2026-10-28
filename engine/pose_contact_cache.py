"""Pair removal and recycling; LINK_SOLVER.md, Empty-pair cache recycling.

Collections retain inactive slots. Payload identities are supplied opaque integers;
Python owns list growth, not the original allocator or synchronization.
"""
import struct


def remove_pair_payload(collection, first, second):
    """Remove last matching pair irrespective of detail; return raw identity.

    A zero identity is returned both for absence and a removed null entry, as in
    the original. Arguments are compared as uint32, not truncated to uint16.
    """
    if any(type(v) is not int or not 0 <= v <= 0xffffffff for v in (first,second)):
        raise ValueError('Unsigned 32-bit comparison keys required')
    for index in range(collection['count']-1,-1,-1):
        row=collection['slots'][index]
        a,b=struct.unpack_from('<HH',row)
        if (a,b)!=(first,second):
            continue
        identity=struct.unpack_from('<Q',row,8)[0]
        collection['count']-=1
        collection['slots'][index]=collection['slots'][collection['count']]
        return identity
    return 0


def clear_contact_pair(collection, first, second, recycled, *, payloads):
    """Remove matching entries, reset counts and append identities for reuse.

    Payload buffers must be mutable and at least 0x114 bytes. Recycled has count,
    capacity and retained slots. Capacity growth follows native 0->8 or doubling;
    newly reserved Python slots are authored placeholders. No payload is freed.
    """
    processed=0
    while True:
        identity=remove_pair_payload(collection,first,second)
        if not identity:
            return processed
        payload=payloads[identity]
        struct.pack_into('<I',payload,0x110,0)
        if recycled['count']==recycled['capacity']:
            capacity=2*recycled['capacity'] if recycled['capacity'] else 8
            recycled['slots'].extend([0]*(capacity-len(recycled['slots'])))
            recycled['capacity']=capacity
        recycled['slots'][recycled['count']]=identity
        recycled['count']+=1
        processed+=1
