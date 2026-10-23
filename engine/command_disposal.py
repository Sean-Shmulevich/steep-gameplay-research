"""Serial command-buffer disposal with caller-supplied lifetime services.

Recovered contract: REQUEST_COMMAND_LIFECYCLE.md, Buffer disposal is not callback
 delivery. This is not a native manager destructor or plugin cancellation API.
Storage is an opaque token; cleanup receives (storage, slot_index). Services must
not mutate the ring header or reenter disposal. Caller owns serialization and
record lifetimes. Validation is authored policy for valid, bounded ring states.
"""


def _validate(ring):
    for name in ('capacity', 'count', 'read', 'write'):
        value = ring[name]
        if type(value) is not int or not 0 <= value <= 0x7fffffff:
            raise ValueError('nonnegative int32 ring fields required')
    capacity = ring['capacity']
    if ring['count'] > capacity:
        raise ValueError('count exceeds capacity')
    if capacity:
        if ring['read'] >= capacity or ring['write'] >= capacity:
            raise ValueError('cursor outside capacity')
        if ring['storage'] is None:
            raise ValueError('backing storage required for nonzero capacity')
    elif ring['read'] or ring['write'] or ring['count']:
        raise ValueError('zero-capacity ring must be empty with zero cursors')
    if type(ring['owns_storage']) is not bool:
        raise ValueError('boolean storage ownership required')


def clear_records(ring, *, cleanup):
    """Release occupied records in read order; never dispatch their invokers.

    cleanup is an opaque record-lifetime service, not a gameplay callback.
    Header resets happen only after all cleanup calls return. If a supplied
    service raises, earlier side effects remain and no rollback is attempted;
    this exposes partial progress, not recovered native exception semantics.
    Pointer, capacity and ownership remain unchanged.
    """
    _validate(ring)
    first = min(ring['count'], ring['capacity'] - ring['read'])
    for index in range(ring['read'], ring['read'] + first):
        cleanup(ring['storage'], index)
    for index in range(ring['count'] - first):
        cleanup(ring['storage'], index)
    ring['write'] = 0
    ring['read'] = 0
    ring['count'] = 0


def release_buffer(ring, *, cleanup, allocation_lookup, free):
    """Clear records then release owned storage and reset allocation fields.

    Borrowed storage still has its occupied records cleaned, but is not freed.
    Lookup precedes free(storage, allocation_info); no allocator is invented.
    No pending scheduler budget is changed or cancellation receipt generated.
    """
    clear_records(ring, cleanup=cleanup)
    if ring['owns_storage'] and ring['storage'] is not None:
        info = allocation_lookup(ring['storage'])
        free(ring['storage'], info)
    ring['owns_storage'] = True
    ring['storage'] = None
    ring['capacity'] = 0
