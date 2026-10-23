"""Serial pointer-ring resize with supplied storage services.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Holder ring resize implementation.
No native allocation, pointer dereference, concurrency or exception guarantee.
"""


def resize_holder_ring(ring, capacity, preserve, *, allocate, copy, free):
    """Resize valid nonnegative int32 rings; services own opaque storage tokens.

    allocate receives uint32(capacity*8); copy(dst, src, start, count) copies
    logical read-order items and must reject invalid storage rather than silently
    lose records. free(storage) abstracts allocator lookup and virtual free.
    Normal-return behavior only. Services must not mutate the ring header.
    """
    if type(capacity) is not int or not 0 <= capacity <= 0x7fffffff:
        raise ValueError('nonnegative int32 capacity required')
    if ring['capacity'] == capacity:
        if not preserve:
            ring.update(count=0, tail=0, head=0)
        return
    retained = min(ring['count'], capacity)
    if preserve and retained > 0:
        new_storage = allocate((capacity * 8) & 0xffffffff)
        copy(new_storage, ring['storage'], ring['head'], retained)
        ring.update(count=0, tail=0, head=0)
        if ring['owns_storage'] and ring['storage'] is not None:
            free(ring['storage'])
        ring.update(storage=new_storage, owns_storage=True, capacity=capacity,
                    count=retained, tail=retained)
    else:
        ring.update(count=0, tail=0, head=0)
        if ring['owns_storage'] and ring['storage'] is not None:
            free(ring['storage'])
        ring.update(storage=None, capacity=0, owns_storage=True)
        if capacity:
            storage = allocate((capacity * 8) & 0xffffffff)
            ring['storage'] = storage
            ring['capacity'] = capacity if storage is not None else 0
