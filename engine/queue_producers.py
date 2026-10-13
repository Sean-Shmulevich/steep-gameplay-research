"""Recovered worker initialization and enqueue destination rules.

Evidence: SCHEDULER_QUEUE_PRODUCERS.md, shared default, worker mask and enqueue
sections. Pure functions do not allocate workers, acquire locks or submit work.
"""
from .queue_policy import _mask, _i32


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


def base_job_limit(byte_argument, shared_default):
    """Base constructor signed comparison, followed by uint8 storage conversion.

    Later job constructors may overwrite this initial limit.
    """
    if type(byte_argument) is not int or not 0 <= byte_argument <= 255:
        raise ValueError('byte argument must be uint8')
    _i32(shared_default)
    return min(byte_argument, shared_default) & 255


def range_configuration(requested):
    """Recovered chunk setter; constructor defaults are a separate path.

    See SCHEDULER_BATCH_EPOCH.md and MOTION_QUEUE_ASSIGNMENTS.md. Extreme
    signed results need not satisfy the bounded MixedScheduler adapter schema.
    """
    _i32(requested)
    chunk = max(requested, 1)
    tail = ((2 * chunk + 2**31) % 2**32) - 2**31 if chunk < 2**31 - 1 else 0
    return dict(chunk_size=chunk, tail_threshold=tail)
