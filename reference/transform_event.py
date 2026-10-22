"""Entity transform event ordering; external effects and lock ownership supplied.

Source: CENTRAL_IMPULSE.md, Entity transform event scope and component callbacks.
This models normal-return order, not concurrent locking or callback semantics.
"""


def plan_transform_event(variant, initial_depth, component_count):
    if variant not in ('base', 'derived_a', 'derived_b'):
        raise ValueError('unsupported observed entity variant')
    if type(initial_depth) is not int or not 0 <= initial_depth < 0xffffffff:
        raise ValueError('nonoverflowing caller-owned recursion depth required')
    if type(component_count) is not int or not 0 <= component_count <= 65535:
        raise ValueError('uint16 component count required')
    # A nonzero depth assumes the calling thread already owns the entity lock.
    # Lists are separate traversals. Count/storage mutation inside callbacks is
    # outside this fixed-list planner.
    events = []
    depth = initial_depth + 1
    for i in range(component_count):
        events.append(dict(service='component_before', component=i, lock_depth=depth))
    events.extend([dict(service='apply_transform', lock_depth=depth),
                   dict(service='refresh_entity', lock_depth=depth)])
    for i in range(component_count):
        events.append(dict(service='component_after', component=i, lock_depth=depth))
    if variant != 'base':
        events.append(dict(service='derived_propagation', lock_depth=initial_depth))
    return dict(events=events, final_depth=initial_depth,
                lock_released=initial_depth == 0, callback_completion_established=False)


def skeleton_after_transform(dirty, pending):
    """Exact SkeletonComponent after-event flag writes; event contents unused.

    The corresponding before-event callback is a no-op. Neither evaluates pose.
    """
    for value in (dirty, pending):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('uint8 skeleton state required')
    return dict(dirty=dirty | 128, pending=pending | 1)
