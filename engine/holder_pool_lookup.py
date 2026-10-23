"""Recovered pool-descriptor selection; not a pointer-validity check.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Holder pool lookup arithmetic.
Pool descriptors are supplied dictionaries; the first matching object is returned.
"""


def holder_slot_index(address, base):
    """Low32 of signed wrapped address difference divided by 24 toward zero."""
    for value in (address,base):
        if type(value) is not int or not 0 <= value <= 0xffffffffffffffff:
            raise ValueError('uint64 address tokens required')
    delta=(address-base)&0xffffffffffffffff
    if delta & (1<<63):delta-=1<<64
    result=abs(delta)//24
    return (-result if delta<0 else result)&0xffffffff


def locate_holder_pool(address, pools):
    """Return first descriptor whose uint32 capacity exceeds computed low32 index.

    Original descriptor list count is uint16 and each descriptor is 16 bytes.
    No alignment or full-width range test is performed. Do not use this alone
    to validate pointers accepted from mods. Missing descriptor returns None.
    """
    if len(pools)>0xffff:
        raise ValueError('descriptor count must fit uint16')
    for pool in pools:
        capacity=pool['capacity']
        if type(capacity) is not int or not 0 <= capacity <= 0xffffffff:
            raise ValueError('uint32 capacity required')
        if holder_slot_index(address,pool['base'])<capacity:
            return pool
    return None
