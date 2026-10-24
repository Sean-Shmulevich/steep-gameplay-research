"""Recovered auxiliary observer routing; supplied operations retain unknown effects.

Evidence: CENTRAL_IMPULSE.md, Registered pose notification consumers.
Event numbers are raw values, not inferred gameplay event names.
"""


def route_auxiliary_pose_notification(body, event, *, manager, read_body_link,
                                      event10, event11, event12):
    for token in (body,manager):
        if type(token) is not int or not 0<=token<=0xffffffffffffffff:
            raise ValueError('Raw uint64 identities required')
    if type(event) is not int or not 0<=event<=0xffffffff:
        raise ValueError('Raw uint32 event required')
    if event==10:event10(manager,body)
    elif event==11:event11(manager,read_body_link(body))
    elif event==12:event12(manager,body)
    return event in (10,11,12)
