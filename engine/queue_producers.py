"""Recovered worker initialization and enqueue destination rules.

Evidence: SCHEDULER_QUEUE_PRODUCERS.md, shared default, worker mask and enqueue
sections. Pure functions do not allocate workers, acquire locks or submit work.
"""
from .queue_policy import _mask


def worker_configuration(requested, upper_bound):
    """Return exact uint32 clamp and signed auxiliary arithmetic, no allocation."""
    _mask(requested)
    _mask(upper_bound)
    selected = min(max(requested, 1), upper_bound)
    previous = ((selected - 1 + 2**31) % 2**32) - 2**31
    signed_default = ((selected + 2**31) % 2**32) - 2**31
    return dict(worker_count=selected, shared_default=signed_default,
                auxiliary_count=max(previous, 1))


def worker_mask(index):
    """Rotate the initial uint32 bit; counts above 32 have unknown reachability."""
    _mask(index)
    return 1 << (index % 32)


def enqueue_destination(category, required_mask, worker_slots):
    """Resolve local/shared queue identity using explicit worker presence.

    Each slot is a boolean indicating a non-null worker pointer. Out-of-bounds
    lookup raises rather than inventing a native fallback. Category validation
    is adapter policy for the ordinary three-category selector.
    """
    if type(category) is not int or category not in range(3):
        raise ValueError('ordinary queue category must be 0, 1 or 2')
    _mask(required_mask)
    if not isinstance(worker_slots, (list, tuple)) or any(type(v) is not bool for v in worker_slots):
        raise ValueError('worker slots must explicitly indicate pointer presence')
    index = None
    if required_mask:
        index = (required_mask & -required_mask).bit_length() - 1
        if index >= len(worker_slots):
            raise ValueError('required mask references an unavailable worker slot')
        if worker_slots[index]:
            return dict(category=category, queue='local', worker_index=index)
    return dict(category=category, queue='shared', worker_index=None)
