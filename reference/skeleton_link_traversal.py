"""Recovered selector/provider ordering over supplied linked-object observations.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Skeleton selector traversal ordering.
Provider arithmetic, later target gates and publication are external.
"""


def plan_skeleton_link_traversal(selectors, visible, requested, pending):
    if len(selectors) != len(visible):
        raise ValueError('one visibility result per selector required')
    if any(type(x) is not int or not 0 <= x <= 65535 for x in [requested,*selectors]):
        raise ValueError('uint16 selectors required')
    if type(pending) is not int or not 0 <= pending <= 255:
        raise ValueError('uint8 pending byte required')
    if any(type(x) is not bool for x in visible):
        raise ValueError('boolean resolved visibility required')
    cached = 65535
    initialized = False
    events = []
    for index, (selector, present) in enumerate(zip(selectors, visible)):
        if requested != 65535 and selector != requested:
            continue
        if selector != cached:
            events.append(dict(event='provider',index=index,selector=selector))
            cached = selector
            initialized = True
        events.append(dict(event='resolve',index=index,selector=selector))
        if present:
            events.append(dict(event='target',index=index,selector=selector,
                               provider_initialized=initialized))
    return dict(events=events,pending=pending & 254 if requested == 65535 else pending)
