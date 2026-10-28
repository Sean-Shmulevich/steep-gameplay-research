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


def find_contact_payload(collection, first, second, detail):
    """Return first full-key match; lookup truncates keys to16/16/32 bits."""
    from .pose_link_record import pack_link_key
    key=pack_link_key(first,second,detail)
    for row in collection['slots'][:collection['count']]:
        if struct.unpack_from('<Q',row)[0]==key:
            return struct.unpack_from('<Q',row,8)[0]
    return 0


def acquire_recycled_contact_payload(collection, first, second, detail, recycled,
                                     *, owner, payloads, supply_batch, append_entry):
    """Reached non-null recycler branch of contact-group acquisition.

    Batch service supplies ten initialized payload identities. Append service owns
    cache storage growth. Existing matches bypass both. The no-recycler global
    allocation/locking branch is deliberately not represented by this function.
    """
    identity=find_contact_payload(collection,first,second,detail)
    if identity:
        return identity
    if recycled['count']==0:
        required=recycled['count']+10
        if required>recycled['capacity']:
            capacity=max(required,2*recycled['capacity'])
            recycled['slots'].extend([0]*(capacity-len(recycled['slots'])))
            recycled['capacity']=capacity
        start=recycled['count']
        recycled['count']+=10
        identities=supply_batch(10)
        if len(identities)!=10:
            raise ValueError('Batch service must provide ten initialized identities')
        recycled['slots'][start:start+10]=identities
    recycled['count']-=1
    identity=recycled['slots'][recycled['count']]
    if not identity:
        raise ValueError('Native acquisition would dereference a null payload')
    struct.pack_into('<Q',payloads[identity],0,owner)
    append_entry(collection,first,second,detail,identity)
    return identity


def retire_stale_contact_groups(collection, records, first, second, recycled, *,
                                payloads, key_width):
    """Reached retirement scan before acquisition; records are already sorted.

    Preserve the forward record cursor across cache entries and advance the cache
    index after swap-last removal. Neither cursor is restarted by this routine.
    Return retired identities as authored diagnostics.
    """
    from .pose_link_record import remove_link_key
    if key_width not in (16,32) or any(len(r)!=48 for r in records):
        raise ValueError('48-byte records and explicit key width required')
    mask=(1<<key_width)-1
    def detail(index):
        return struct.unpack_from('<I',records[index],0x2c)[0]&mask
    cursor=0;index=0;retired=[]
    while index<collection['count']:
        row=collection['slots'][index]
        a,b,key,identity=struct.unpack('<HHIQ',row)
        if (a,b)==(first,second):
            found=False
            while cursor<len(records):
                current=detail(cursor);end=cursor+1
                while end<len(records) and detail(end)==current:end+=1
                if key==current:
                    found=True
                    break
                cursor=end
            if not found:
                remove_link_key(collection,first,second,key)
                struct.pack_into('<I',payloads[identity],0x110,0)
                if recycled['count']==recycled['capacity']:
                    capacity=2*recycled['capacity'] if recycled['capacity'] else 8
                    recycled['slots'].extend([0]*(capacity-len(recycled['slots'])))
                    recycled['capacity']=capacity
                recycled['slots'][recycled['count']]=identity
                recycled['count']+=1
                retired.append(identity)
        index+=1
    return retired
