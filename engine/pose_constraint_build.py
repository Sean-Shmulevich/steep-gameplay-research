"""Pose builder dispatch; LINK_SOLVER.md, Constraint builder eligibility and dispatch."""
import struct
from .pose_constraint_motion import build_pose_motion_constraint
from .pose_constraint_point import build_pose_point_constraint
from .pose_constraint_hinge import build_pose_hinge_constraint
from .pose_constraint_commands import build_pose_command_constraint


def build_pose_constraints(context, slots, *, constraints, bodies, metadata,
                           get_kind, atan2=None, notify=None, additional_builders=None):
    """Run the retained pointer-list eligibility loop and six-way kind dispatch.

    get_kind(token) supplies the virtual type service. Reconstructed kinds1/3/4/6
    run directly; reached kinds2/5 require explicit additional_builders[kind]
    accepting (context, constraint_token). Unknown uint32 kinds emit no rows.
    The pointer selected before get_kind is retained even if that service edits
    the slot. No traversal-count or result-cache policy is invented here.
    """
    def disabled(token):
        meta_token = struct.unpack_from('<Q', bodies[token], 0x30)[0]
        return bool(metadata[meta_token][0x52]&1)
    for i in range(len(slots)):
        token = slots[i]
        constraint = constraints[token]
        first, second = struct.unpack_from('<2Q', constraint, 8)
        if disabled(first) or (second and disabled(second)):
            continue
        kind = get_kind(token)
        if type(kind) is not int or not 0 <= kind <= 0xffffffff:
            raise ValueError('Unsigned virtual kind result required')
        if kind == 1:
            build_pose_point_constraint(context,constraint,bodies=bodies,metadata=metadata)
        elif kind == 3:
            if atan2 is None:
                raise ValueError('Kind3 requires explicit atan2 service')
            build_pose_hinge_constraint(context,constraint,bodies=bodies,metadata=metadata,
                                        atan2=atan2,notify=notify)
        elif kind == 4:
            build_pose_command_constraint(context,constraint,bodies=bodies)
        elif kind == 6:
            build_pose_motion_constraint(context,constraint,bodies=bodies,metadata=metadata)
        elif kind in (2,5):
            if additional_builders is None or kind not in additional_builders:
                raise ValueError(f'Kind{kind} builder remains an explicit dependency')
            additional_builders[kind](context,token)
