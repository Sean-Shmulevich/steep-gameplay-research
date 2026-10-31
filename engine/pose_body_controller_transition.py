"""Controller gate and synchronization boundary for body group transitions.

Evidence: docs/reconstruction/LINK_SOLVER.md, Controller group-transition wrapper.
"""
import struct


def transition_controller_pose_body(controller, body, *, controller_token,
                                    body_token, metadata, enter, leave,
                                    transition, reset_body):
    """Supply synchronization, context transition and dynamic virtual28 effects.

    The context token is loaded after enter. No exception cleanup or concrete lock
    implementation is inferred from the protected synchronization call sites.
    """
    meta = metadata[struct.unpack_from('<Q', body, 0x30)[0]]
    if meta[0x52] & 1 or not struct.unpack_from('<Q', body, 0x10)[0]:
        return
    sync = controller_token + 0x50
    enter(sync)
    transition(struct.unpack_from('<Q', controller, 0x30)[0], body_token)
    reset_body(body_token)
    leave(sync)
