"""Recovered animation-resource handle-to-pointer cache finalization.

Evidence: CENTRAL_IMPULSE.md, Animation resource raw-pointer cache.
The cache contains logical pointer values, not retained object references.
"""


def finalize_pointer_cache(records, thread_mask, cached_values=()):
    """Build only when cached count is zero, preserving null/masked entries.

    List lengths stand for the inspected uint16 source/cache count fields.
    Supplied lists must faithfully describe those counts. No concurrency modeled.
    """
    if type(thread_mask) is not int or not 0 <= thread_mask < 2**64:
        raise ValueError('uint64 mask required')
    if len(records) > 65535 or len(cached_values) > 65535:
        raise ValueError('uint16 counts required')
    if any(type(v) is not int or not 0 <= v < 2**64 for v in cached_values):
        raise ValueError('uint64 cached pointers required')
    if cached_values:
        return dict(values=list(cached_values), rebuilt=False, lock_requested=False,
                    lifetime_retained=False)
    values = []
    for record in records:
        pointer, status = record['pointer'], record['status']
        if type(pointer) is not int or not 0 <= pointer < 2**64:
            raise ValueError('uint64 pointer required')
        if type(status) is not int or not 0 <= status < 2**32:
            raise ValueError('uint32 status required')
        mask = 2**64 - 1 if status & 0x80000000 else thread_mask
        values.append(pointer & mask)
    return dict(values=values, rebuilt=True, lock_requested=True,
                lifetime_retained=False)
