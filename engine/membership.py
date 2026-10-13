"""Recovered conditional receiver-array replacement under a caller-owned snapshot.

See docs/reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md. This models list-copy
semantics only: native synchronization, lifetime, worker accounting and request
identity are NOT supplied. Receiver handles are immutable strings or integers
chosen by the caller; their values do not establish native object identity.
"""


def copy_registered_receivers(source, destination):
    """Mutate destination list, preserving order/duplicates and retaining on empty.

    Caller must provide a stable source snapshot and exclusively own destination.
    For nonempty source, replace active destination entries. For empty source,
    leave destination intact. Reset belongs to an explicit outer lifecycle, e.g.
    destination.clear(), not this helper. No object refcount or lifetime modeled.
    """
    if not isinstance(source, (list, tuple)) or not isinstance(destination, list):
        raise ValueError('source must be a stable list/tuple; destination must be a list')
    if any(type(item) not in (int, str) for item in (*source, *destination)):
        raise ValueError('receiver handles must be immutable integer or string tokens')
    snapshot = list(source)
    previous_count = len(destination)
    if snapshot:
        destination[:] = snapshot
    return {'source_count': len(snapshot), 'previous_destination_count': previous_count,
            'destination_count': len(destination), 'retained_on_empty': not bool(snapshot),
            'request_epoch_established': False, 'receiver_lifetime_established': False,
            'synchronization': 'caller supplied stable source snapshot and exclusive destination'}
