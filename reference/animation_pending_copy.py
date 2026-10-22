"""Recovered animation side-state copy; vector storage remains a service.

Evidence: CENTRAL_IMPULSE.md, Pending animation side-state copy.
"""


def copy_pending_state(destination, source, *, copy_vector):
    """Copy provider vector, flag bit zero, auxiliary vector, then uint32 word.

    copy_vector(destination, source, field) performs vector assignment. It may
    mutate source/destination, so scalar fields are read at their native points.
    Owner identity and reference count are not copied. No exception rollback.
    Field names are authored; the extra word's meaning remains unresolved.
    """
    if destination is not source:
        copy_vector(destination, source, 'providers')
    destination['flags'] = (destination['flags'] & 0xfe) | (source['flags'] & 1)
    if destination is not source:
        copy_vector(destination, source, 'auxiliary')
    destination['word'] = source['word'] & 0xffffffff
