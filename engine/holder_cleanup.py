"""Serial holder detachment and free-list publication, with supplied services.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Holder cleanup gates and recycling.
Field names are descriptive. No payload destructor, allocator or native lock.
"""


def cleanup_holder(holder, *, release_payload_token, remove_token, locate_pool):
    """Apply inspected normal-return gates and state changes.

    holder has status, count, payload, token, address. payload has flags; pool
    returned by locate_pool(holder) has base and head. Services may update status
    and pool state; subsequent reads observe updates. The token is captured once.
    Returned diagnostics are authored, not a native result or disposal receipt.
    """
    status=holder['status']
    if status & ((1<<26)|(1<<24)) or holder['count'] != 0 or status & 0xffffff:
        return dict(detached=False,recycled=False)
    payload=holder['payload'];token=holder['token']
    if payload is not None:
        payload['flags'] &= 0xfff80000
        if payload['flags'] & (1<<28):
            release_payload_token(token)
        holder['payload']=None
        holder['status'] &= ~(1<<31)
    holder['status'] |= 1<<26
    recycled=False
    if token != 0:
        in_reserved_range=((token-0xf0000000)&0xffffffffffffffff) <= 0x7ffffff
        if not in_reserved_range and not holder['status'] & (1<<28):
            remove_token(token)
        pool=locate_pool(holder)
        holder['count']=pool['head']
        difference=(holder['address']-pool['base'])&0xffffffffffffffff
        if difference & (1<<63):difference-=1<<64
        index=abs(difference)//24
        if difference<0:index=-index
        pool['head']=index&0xffffffff
        recycled=True
    return dict(detached=True,recycled=recycled)
