"""Connect retained group membership to indexed solver body buffers.

Evidence: LINK_SOLVER.md, Group membership and solver body indices.
The adapter and its validation policy are authored; the membership and buffer
operations it connects are independently reconstructed.
"""
from engine.pose_body_buffers import build_pose_body_buffers


def build_pose_group_body_buffers(group, *, bodies, scalar, vector,
                                  damping_response=None):
    """Build buffers in group order after checking retained membership.

    Each body combines membership fields with build_pose_body_buffers inputs.
    Records must remain stable for the call. This is not a live snapshot, lock,
    ownership transfer, native validation routine or automatic index repair.
    """
    count = group['count']
    if type(count) is not int or not 0 <= count <= 0xffff:
        raise ValueError('Body count must fit the retained solver layout')
    if count > len(group['slots']):
        raise ValueError('Complete active group slots required')
    tokens = list(group['slots'][:count])
    ordered = []
    for index, token in enumerate(tokens):
        body = bodies[token]
        if (body['token'] != token or body['group'] != group['token']
                or type(body['index']) is not int or body['index'] != index):
            raise ValueError('Body membership does not match its group slot')
        ordered.append(body)
    buffers = build_pose_body_buffers(
        ordered, scalar=scalar, vector=vector, damping_response=damping_response)
    return dict(body_tokens=tokens,
                body_data=dict(enumerate(buffers['body_data'])),
                body_state=dict(enumerate(buffers['body_state'])))
