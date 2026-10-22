"""Guarded skeleton refresh effect order, with explicitly supplied service results.

Evidence: CENTRAL_IMPULSE.md, Lazy getters can rotate and refresh a skeleton.
This is a branch/effect model, not a pose evaluator or synchronization primitive.
"""


def plan_guarded_refresh(dirty, force, pending, locked_dirty, rotated, bank_flags,
                         primary_present=True, current_present=True, disabled=0,
                         primary_flags=0, component_flags=0x38, secondary=1):
    for value in (dirty, pending, locked_dirty, disabled, component_flags, secondary):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('uint8 state required')
    for value in (bank_flags, primary_flags):
        if type(value) is not int or not 0 <= value < 2**32:
            raise ValueError('uint32 bank flags required')
    for value in (force, rotated, primary_present, current_present):
        if type(value) is not bool:
            raise ValueError('boolean predicate required')
    events = []
    if not (dirty >= 128 or (pending & 1 and force)):
        return dict(events=events, dirty_after=dirty)
    if not primary_present or not current_present or disabled:
        return dict(events=events, dirty_after=dirty)
    events.append(dict(service='lock'))
    dirty = locked_dirty
    if dirty >= 128:
        events.extend([dict(service='prepare'), dict(service='parent', bank='primary'),
                       dict(service='rotate'), dict(service='parent', bank='current')])
        if rotated or ((bank_flags | primary_flags) & (1 << 27)):
            events.append(dict(service='process', mask=(component_flags >> 3) & 7))
        dirty &= 127
    if force and pending & 1:
        events.append(dict(service='evaluate', secondary=secondary, dirty_seen=dirty))
    events.append(dict(service='unlock'))
    return dict(events=events, dirty_after=dirty)


def plan_pose_propagation(publish, callback_present, child_present, secondary,
                          dirty, pending):
    """Per-linked-object tail; callback effects and recursive refresh are opaque.

    Returned bytes are those before recursive refresh, whose writes are unknown.
    No cycle prevention or lifetime retention is supplied by this planner.
    """
    for value in (publish, callback_present, child_present):
        if type(value) is not bool:
            raise ValueError('boolean predicate required')
    for value in (secondary, dirty, pending):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('uint8 state required')
    events = []
    if callback_present:
        events.append('transform_callback')
        publish = True
    if publish:
        events.append('transform_event')
    events.append('find_skeleton')
    if child_present:
        dirty |= 128
        pending |= 1
        if secondary:
            events.append('refresh_child')
    return dict(events=events, dirty_after=dirty, pending_after=pending)


def plan_skeleton_post_list(entities):
    """Observed list-adapter order with externally supplied lookup outcomes.

    Each item is (world_present, skeleton_present). Real pointers and lifecycle
    stay with the caller; this does not invoke a game job or evaluate a skeleton.
    """
    entities = list(entities)
    if len(entities) > 65535:
        raise ValueError('uint16 entity count required')
    events = []
    for i, item in enumerate(entities):
        if not isinstance(item, (list, tuple)) or len(item) != 2 or any(type(v) is not bool for v in item):
            raise ValueError('boolean world/skeleton pair required')
        world, skeleton = item
        if world:
            events.append(['lookup', i])
            if skeleton:
                events.append(['update', i])
    return events
