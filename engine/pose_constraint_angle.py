"""Kind3 angle inputs; LINK_SOLVER.md, Kind3 angle interval selection."""
import math
import struct
from reference.central_impulse import f32
from .pose_constraint_limit import _vector

TAU = f32(6.2831854820251465)


def select_pose_angle_interval(angle, lower, upper):
    """Select one adjacent revolution, preserving the native XYZ aggregate gate.

    This is not a clamp or repeated modulo wrap. Bounds are not sorted. All four
    lanes are selected after the first three lanes trigger the outer branch.
    """
    angle, lower, upper = map(_vector, (angle, lower, upper))
    if not (all(u<a for a,u in zip(angle[:3],upper[:3])) or
            all(a<l for a,l in zip(angle[:3],lower[:3]))):
        return angle
    out = []
    for a,l,u in zip(angle,lower,upper):
        plus = f32(a+TAU) if f32(a-u)<0 else a
        minus = f32(a-TAU) if f32(l-a)<0 else a
        difference = f32(f32(l-minus)-f32(plus-u))
        out.append(minus if difference<0 else plus)
    return out


def pose_constraint_drive_sample(constraint):
    """Reconstruct the scalar getter using its subtract-and-compare ordering."""
    lower = struct.unpack_from('<f', constraint, 0xd0)[0]
    upper = struct.unpack_from('<f', constraint, 0xd4)[0]
    current = struct.unpack_from('<f', constraint, 0xdc)[0]
    if not all(math.isfinite(v) for v in (lower,upper,current)):
        raise ValueError('Finite retained scalar inputs required')
    selected = lower if f32(lower-current)>=0 else current
    return selected if f32(upper-selected)>=0 else upper
