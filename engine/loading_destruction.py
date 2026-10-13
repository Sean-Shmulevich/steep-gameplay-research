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
