"""Counter arithmetic for loading-thread destruction publication.

Evidence: LOADING_THREAD_LIFECYCLE.md, Staging and publication producer.
These functions model separate atomic boundaries, not one atomic snapshot.
Ring insertion, resource ownership, locks and callbacks remain external.
"""
from .queue_policy import _i32


def _wrap(value):
    return ((value + 2**31) % 2**32) - 2**31


def stage_increment(staged):
    _i32(staged)
    return _wrap(staged + 1)


def take_staged(staged):
    _i32(staged)
    return dict(staged=0, captured=staged)


def publish_captured(pending, captured):
    _i32(pending)
    _i32(captured)
    return dict(pending=_wrap(pending + captured), notify_worker=captured != 0)


def take_pending(pending):
    """Called after busy is set; preserves signed positive loop condition."""
    _i32(pending)
    return dict(pending=0, captured=pending, iterations=max(pending, 0))


def stop_poll_passes(observed_pending, observed_busy):
    """Exact two-read predicate. It is not a safe-destruction predicate."""
    _i32(observed_pending)
    _i32(observed_busy)
    return observed_pending == 0 and observed_busy == 0


def ring_resize_plan(capacity, count, read_index, write_index, requested, *, preserve=True):
    """Recovered copy geometry for a valid ring, excluding allocator behavior.

    Adapter scope requires nonnegative bounded capacities and canonical indices.
    The resized write index is retained_count, even when equal to capacity.
    """
    for value in (capacity, count, read_index, write_index, requested):
        if type(value) is not int or value < 0:
            raise ValueError('ring geometry must contain nonnegative integers')
    if type(preserve) is not bool or max(capacity, requested) > (2**31-1)//8:
        raise ValueError('invalid preserve flag or allocation-size scope')
    if count > capacity or (capacity == 0 and (count or read_index or write_index)):
        raise ValueError('inconsistent ring occupancy')
    if capacity and (read_index >= capacity or write_index > capacity):
        raise ValueError('ring index outside geometry')
    if requested == capacity:
        return dict(action='unchanged' if preserve else 'clear', segments=[],
                    capacity=capacity, count=count if preserve else 0,
                    read_index=read_index if preserve else 0,
                    write_index=write_index if preserve else 0)
    retained = min(count, requested) if preserve else 0
    segments = []
    if retained:
        first = min(retained, capacity-read_index)
        segments.append(dict(source_index=read_index, destination_index=0, count=first))
        if retained > first:
            segments.append(dict(source_index=0, destination_index=first, count=retained-first))
    return dict(action='copy_and_replace' if retained else 'clear_and_allocate',
                segments=segments, capacity=requested, count=retained,
                read_index=0, write_index=retained)
