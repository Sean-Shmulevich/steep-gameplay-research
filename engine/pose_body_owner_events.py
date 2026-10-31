"""Registered ownership-manager body listener for events10..12.

Evidence: docs/reconstruction/LINK_SOLVER.md, Registered body listener identities.
"""
import struct


def dispatch_pose_body_owner_event(body_token,event,*,bodies,get_manager,
                                   remove_body,remove_link,update_body):
    """Forward event10/11/12 with recovered argument choice.

    Services receive(manager_token,argument_token). Event11 uses bodyb0 as a raw
    qword, not metadata.owner or body itself. Other events do not dereference body.
    Manager global is loaded once even when the event is ignored.
    """
    manager=get_manager()
    event &= 0xffffffff
    if event==10:remove_body(manager,body_token)
    elif event==11:remove_link(manager,struct.unpack_from('<Q',bodies[body_token],0xb0)[0])
    elif event==12:update_body(manager,body_token)
