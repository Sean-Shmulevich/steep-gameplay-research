"""Recovered link payload-array clearing and optional transfer.

Evidence: CENTRAL_IMPULSE.md, Link payload clearing and transfer.
"""


def clear_pose_link_payloads(source, destination, *, payloads, release, grow):
    """Clear active entries after processing a captured extent.

    source has count and slots of {key,payload}; destination is None or a retained
    count/capacity/token-slots array. Payload dictionaries expose raw count110.
    release(token) supplies the unresolved protected pool-return block.
    grow(destination, capacity) supplies storage. No exception cleanup is added.
    """
    slots=source['slots'];count=source['count']
    for i in range(count):
        token=slots[i]['payload']
        if destination is None:
            if token:release(token)
        else:
            payloads[token]['count110']=0
            capacity=destination['capacity']
            if destination['count']==capacity:
                grow(destination,8 if capacity==0 else (capacity*2)&0xffffffff)
            n=destination['count']
            destination['slots'][n]=token
            destination['count']=(n+1)&0xffffffff
    source['count']=0


def clear_pose_link_contacts(link, *, entry_arrays, release):
    """Run the no-transfer clearing wrapper on a retained raw link.

    Evidence: LINK_SOLVER.md, Inactive body rings and contact retirement.
    Capture link58 array identity and link60 count, re-read each 16-byte entry's
    payload at +8, release nonnull payloads, then clear only link60. Release is
    an explicit pool service; keys, capacity and inactive entry bytes persist.
    """
    import struct
    pointer,count=struct.unpack_from('<QI',link,0x58)
    if count:
        entries=entry_arrays[pointer]
        if len(entries)<16*count:raise ValueError('Complete retained contact entries required')
        for i in range(count):
            payload=struct.unpack_from('<Q',entries,16*i+8)[0]
            if payload:release(payload)
    struct.pack_into('<I',link,0x60,0)
