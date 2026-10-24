"""Recovered temporary body-state application after the secondary solver pass.

Evidence: LINK_SOLVER.md, Secondary-pass temporary body update.
"""


def apply_pose_secondary_body_state(body_tokens, *, bodies, body_state, update_body):
    """Temporarily expose solved XYZ pairs to a supplied body update service.

    update_body(token, raw_body, 1.0) supplies the virtual-slot+0x10 method.
    The entry count is captured; slots and state are read on each iteration.
    On normal return the original 24 motion bytes are restored. Other callback
    effects persist. Exceptions, buffer aliasing and live ownership are outside
    the contract; no exception-safe rollback is invented.
    """
    count = len(body_tokens)
    for index in range(count):
        token = body_tokens[index]
        body = bodies[token]
        state = body_state[index]
        if len(body) < 0x1b8 or len(state) < 32:
            raise ValueError('Retained body motion and complete state record required')
        previous = bytes(body[0x1a0:0x1b8])
        body[0x1a0:0x1ac] = state[:12]
        body[0x1ac:0x1b8] = state[16:28]
        update_body(token, body, 1.0)
        body[0x1a0:0x1b8] = previous
