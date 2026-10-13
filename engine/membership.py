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


def claim_range(remaining, chunk_size=1, tail_threshold=0):
    """Recovered ordinary range arithmetic; caller owns atomic CAS and lifetime.

    Source: docs/reconstruction/SCHEDULER_BATCH_EPOCH.md. This pure function
    computes one successful-claim proposal, not a thread-safe claim. Count zero
    means no unclaimed entries, not that already claimed callbacks completed.
    Signed overflow/sentinel configurations are deliberately rejected.
    """
    if any(type(value) is not int for value in (remaining,chunk_size,tail_threshold)):
        raise ValueError('Range settings must be integers')
    if not 0<=remaining<=0x7fffffff or chunk_size<1 or tail_threshold<0 or chunk_size+tail_threshold>0x7fffffff:
        raise ValueError('Range settings outside ordinary signed domain')
    if remaining==0:
        return None
    if remaining>tail_threshold:
        proposed=remaining-chunk_size if remaining>=tail_threshold+chunk_size else tail_threshold
    else:
        proposed=remaining-1
    return {'start':proposed,'count':remaining-proposed,'remaining':proposed,
            'end_exclusive':remaining,'completion_established':False}


def configured_chunk(requested):
    """Recovered ordinary setter: clamp chunk to one; threshold is twice chunk."""
    if type(requested) is not int or requested>0x3fffffff or requested< -0x80000000:
        raise ValueError('Chunk outside supported nonoverflowing setter domain')
    chunk=max(1,requested)
    return {'chunk_size':chunk,'tail_threshold':2*chunk}
