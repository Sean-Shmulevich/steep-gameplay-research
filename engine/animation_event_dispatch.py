"""Local Kino queued-event call planning, not event evaluation or lifetime control.

Evidence: docs/reconstruction/ANIMATION_COMPONENT_DISPATCH.md, Queued event drain.
Each row is (event_pointer, (first_payload, first_status_u32),
             (second_payload, second_status_u32)). Status bit31 enables payload.
"""

def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError('expected unsigned integer')
    return value


def _handle(value):
    payload, status = value
    return _uint(payload, 64) if _uint(status, 32) & 0x80000000 else 0


def plan_event_dispatch(rows, *, suppress=False):
    """Return ordered slot-0x50 calls; never dereference pointers or call handlers.

    Suppression skips calls, not the original routine's later queue clearing.
    Reference release, callback mutations and queue clearing remain external.
    Pointer-like values are opaque caller-supplied tokens, not portable assets.
    """
    if type(suppress) is not bool:
        raise ValueError('suppress must be boolean')
    rows = list(rows)
    if len(rows) > 65535:
        raise ValueError('queue exceeds uint16 count')
    calls = []
    for event, first, second in rows:
        event = _uint(event, 64)
        if suppress or not event:
            continue
        calls.append(dict(event=event, first=_handle(first), second=_handle(second), extra=0))
    return calls
