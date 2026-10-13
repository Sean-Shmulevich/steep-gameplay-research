"""Local worker counter transitions, not an OS event implementation.

Evidence: docs/reconstruction/WORKER_THREAD_CONTEXT.md, Idle and notification
counter protocol. Each function models one successful atomic operation. Callers
must serialize shared state themselves; these pure functions provide no locking.
"""
from .queue_policy import _i32


def _wrap(value):
    return ((value + 2**31) % 2**32) - 2**31


def idle_transition(counter):
    """Fetch-sub one; request the wait adapter when subtraction sets SF.

    The original CMP/JNS tests the sign of wrapped old-minus-one, not a Python
    signed comparison. Extreme values have no established native reachability.
    """
    _i32(counter)
    next_counter = _wrap(counter - 1)
    return dict(counter=next_counter, call_wait_adapter=next_counter < 0)


def notify_transition(counter):
    """Successful CAS result and whether the old value requests notification."""
    _i32(counter)
    return dict(counter=min(_wrap(counter + 1), 1),
                call_notify_adapter=counter < 0)
