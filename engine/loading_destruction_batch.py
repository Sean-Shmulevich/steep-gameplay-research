"""Recovered serial loading destruction batch, including retained-pointer behavior.

Evidence: LOADING_THREAD_LIFECYCLE.md, Executable destruction batch.
No native memory access. Caller retains owner/storage and supplies all services.
"""


def process_loading_destructions(owner, *, lock, unlock, allocation_lookup,
                                 destroy_payload, free_storage):
    """Take pending uint32 once; consume while its signed interpretation is positive.

    owner: pending, busy, ring; ring: slots/count/head/capacity, with valid
    nonnegative geometry. Null slots use None. Callbacks may publish later work.
    Destruction runs outside the ring lock, with metadata captured beforehand.
    The retained pointer persists on an empty ring, intentionally matching the
    original. Services must use synthetic tokens when testing shortages. There
    is no exception recovery, concurrency guarantee or safe-unload claim.
    """
    owner['busy'] = 1
    captured = owner['pending'] & 0xffffffff
    owner['pending'] = 0
    remaining = captured if captured < 0x80000000 else captured - 0x100000000
    retained = None
    iterations = 0
    calls = 0
    while remaining > 0:
        lock(owner)
        ring = owner['ring']
        if ring['count'] > 0:
            index = ring['head']
            ring['head'] = (index + 1) % ring['capacity']
            ring['count'] -= 1
            retained = ring['slots'][index]
        unlock(owner)
        if retained is not None:
            metadata = allocation_lookup(retained)
            destroy_payload(retained, 0)
            free_storage(retained, metadata)
            calls += 1
        remaining -= 1
        iterations += 1
    owner['busy'] = 0
    return dict(captured=captured, iterations=iterations, destruction_calls=calls)
