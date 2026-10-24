"""Recovered raw solver-state writeback into body motion fields.

Evidence: LINK_SOLVER.md, Solver body-state feedback.
"""


def write_pose_body_feedback(body_tokens, *, bodies, body_state):
    """Copy XYZ lanes in array order, preserving every other body byte.

    State records have32 bytes. Bodies are retained writable buffers through1b8.
    Duplicate identities are processed repeatedly; later entries overwrite earlier
    motion fields. Source/destination overlap and concurrent mutation are excluded.
    """
    count=len(body_tokens)
    if len(body_state)<count:raise ValueError('A state record for every body-array entry is required')
    for index in range(count):
        body=bodies[body_tokens[index]];state=body_state[index]
        if len(body)<0x1b8 or len(state)!=32:raise ValueError('Complete retained body and state storage required')
        body[0x1a0:0x1ac]=state[:12]
        body[0x1ac:0x1b8]=state[16:28]
