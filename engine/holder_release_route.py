"""Local holder-release routing, not a lifetime or scheduler-drain guarantee.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, holder release versus callback drain.
Models the inspected routine with stable inputs and successful ring capacity.
Does not execute cleanup, grow a queue, model atomics, or name unknown flags.
"""


def holder_release_route(status, *, payload_present, global_suppress,
                         manager_mode, thread_kind):
    if type(status) is not int or not 0 <= status <= 0xffffffff:
        raise ValueError('status must be uint32')
    if type(payload_present) is not bool or type(global_suppress) is not bool:
        raise ValueError('presence and suppression must be boolean')
    for value in (manager_mode, thread_kind):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('mode and thread kind must be uint32')
    if status & (1 << 26) or status & 0xffffff:
        return dict(route='no_action', status=status, post_unlock_service=False)
    if not payload_present or status & (1 << 27) or global_suppress:
        return dict(route='cleanup_helper', status=status, post_unlock_service=False)
    if status & (1 << 24):
        return dict(route='no_action', status=status, post_unlock_service=False)
    return dict(route='enqueue', status=status | (1 << 24),
                post_unlock_service=manager_mode == 1 and thread_kind != 3)
