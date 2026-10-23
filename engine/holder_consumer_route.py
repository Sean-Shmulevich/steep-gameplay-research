"""Per-item retirement consumer behavior with stable fields and enough output space.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, deferred holder consumer.
External callbacks and cleanup are reported, not executed. No lifetime guarantee.
"""


def holder_consumer_route(status, *, payload_present, manager_mode):
    if type(status) is not int or not 0 <= status <= 0xffffffff:
        raise ValueError('status must be uint32')
    if type(payload_present) is not bool:
        raise ValueError('payload presence must be boolean')
    if type(manager_mode) is not int or not 0 <= manager_mode <= 0xffffffff:
        raise ValueError('mode must be uint32')
    events = []
    if status & 0xffffff == 0:
        if payload_present:
            events += ['payload_virtual48', 'dispatch_payload' if manager_mode == 0 else 'append_output']
        events += ['clear_queued_bit', 'cleanup_holder']
    else:
        events += ['clear_queued_bit']
    return dict(status=status & ~(1 << 24), events=events)
