"""Body state setters that notify the controller group transition.

Evidence: RVA 0x18aa520 (linear velocity), 0x18aa360 (angular velocity) and
0x18a8c20 (pose), analysis/thread-census/probes/step_hold_safe_point_static_probe.md
and docs/reconstruction/LINK_SOLVER.md, Controller group-transition wrapper.

Object layout used (offsets are evidence anchors, not API fields):
  body+0x30 -> metadata; metadata+0x20 -> holder; holder+0x20 -> controller;
  metadata+0x53 low nibble is the body kind (2 = the kind the force flag guards);
  body+0x1a0..0x1a8 linear velocity, body+0x1ac..0x1b4 angular velocity.
The controller token is passed unchanged to the (already reconstructed)
transition wrapper `engine.pose_body_controller_transition`. Nothing here
claims original-engine equivalence; the wrapper and the dynamic virtual 0xa0
pose store are injected services.
"""
import struct


def _controller(body, metadata, holders):
    meta = metadata[struct.unpack_from('<Q', body, 0x30)[0]]
    holder = holders[struct.unpack_from('<Q', meta, 0x20)[0]]
    return meta, struct.unpack_from('<Q', holder, 0x20)[0]


def _set_velocity(body, vector, force, offset, metadata, holders, notify, body_token):
    meta, _ = _controller(body, metadata, holders)
    force = bool(force & 255)
    # Kind-2 bodies accept the vector only when the force flag is nonzero.
    if meta[0x53] & 15 != 2 or force:
        body[offset:offset + 12] = bytes(vector[:12])
    # Metadata and controller are reloaded after the store (no intervening call).
    _, controller = _controller(body, metadata, holders)
    if controller and force:
        notify(controller, body_token)


def set_pose_body_linear_velocity(body, vector, force, *, metadata, holders, notify,
                                  body_token):
    """RVA 0x18aa520. Raw 12-byte store to body+0x1a0 unless (kind==2 and not force).

    notify(controller_token, body_token) is the 0x18b8380 wrapper; it is reached
    only when force != 0 and the controller is non-null, even when the store
    was skipped.
    """
    _set_velocity(body, vector, force, 0x1a0, metadata, holders, notify, body_token)


def set_pose_body_angular_velocity(body, vector, force, *, metadata, holders, notify,
                                   body_token):
    """RVA 0x18aa360. Same gates as the linear setter, store at body+0x1ac."""
    _set_velocity(body, vector, force, 0x1ac, metadata, holders, notify, body_token)


def set_pose_body_pose(body, matrix, *, metadata, holders, store_pose, notify,
                       body_token):
    """RVA 0x18a8c20. Repack 12 floats and call dynamic virtual 0xa0, then notify.

    matrix is 48 raw bytes (four rows of three floats). store_pose(body_token,
    rows) receives four 12-byte rows; native passes a 16-byte-stride buffer whose
    padding words are uninitialised stack, so only the 12-byte rows are defined.
    The notify call needs only a non-null controller (no force flag), and the
    metadata/controller are reloaded after the virtual call.
    """
    raw = bytes(matrix[:48])
    store_pose(body_token, tuple(raw[i:i + 12] for i in range(0, 48, 12)))
    _, controller = _controller(body, metadata, holders)
    if controller:
        notify(controller, body_token)
