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
