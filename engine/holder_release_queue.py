"""Serial holder release with explicit capacity-growth and synchronization services.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Holder queue growth and failed insertion.
No native lock, concurrent acquisition, allocator or disposal completion is supplied.
"""
from .holder_release_route import holder_release_route


def release_holder_to_queue(holder, registry, *, global_suppress, lock, unlock,
                            grow, cleanup, classify_thread, post_unlock):
    """Execute the stable-input route with supplied normal-return services.

    registry has mode and ring; ring has slots/count/tail/head/capacity. grow gets
    (ring, uint32(old_capacity+0x4000), True) and may replace its storage/header.
    Its return value is ignored, as in the original call. Failed growth may leave
    the holder flagged but not inserted. Returned diagnostics are authored API.
    Caller serializes access; supplied services must maintain valid ring state.
    No exception cleanup or rollback contract is claimed.
    """
    lock(registry)
    route = holder_release_route(holder['status'],
        payload_present=holder['payload'] is not None,
        global_suppress=global_suppress, manager_mode=registry['mode'], thread_kind=3)
    enqueued = False
    growth_requested = False
    run_service = False
    if route['route'] == 'cleanup_helper':
        cleanup(registry, holder)
    elif route['route'] == 'enqueue':
        holder['status'] = route['status']
        ring = registry['ring']
        if ring['capacity'] <= ring['count']:
            growth_requested = True
            grow(ring, (ring['capacity'] + 0x4000) & 0xffffffff, True)
        if ring['capacity'] > ring['count']:
            ring['slots'][ring['tail']] = holder
            ring['count'] += 1
            ring['tail'] = (ring['tail'] + 1) % ring['capacity']
            enqueued = True
        if registry['mode'] == 1:
            run_service = classify_thread() != 3
    unlock(registry)
    if run_service:
        post_unlock(registry)
    return dict(route=route['route'], growth_requested=growth_requested,
                enqueued=enqueued, post_unlock_service=run_service)
