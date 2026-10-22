"""Initial angular proposal, before equipment remap and acceptance/feedback.

Evidence: docs/systems/body/CLIENT_GUIDE.txt, Controller input to rotation
proposal; MOTION_MEMBERSHIP_OBSERVATION.md, Connected rotation proposal.
No torque, body assignment, integration or world-space interpretation implied.
"""
import math
from .motion_input_latches import InputLatches, _f32


def initial_rotation_proposal(primary_x, primary_y, secondary_y,
                              latches: InputLatches, angular_limit):
    """Finite-input float32 prefix; returned local XYZ is radians/time unit.

    Limit units inherit the caller's clock. Inputs are not clamped or normalized.
    Native equipment remapping and acceptance gates happen after this prefix.
    """
    values = tuple(_f32(v) for v in (primary_x, primary_y, secondary_y, angular_limit))
    if not all(math.isfinite(v) for v in values):
        raise ValueError('finite float32 inputs required by this inspection API')
    x,y,z,limit = values
    if not latches.first:
        x=y=0.0
    elif abs(y) < _f32(0.3):
        y=0.0
    if not latches.second or abs(z) < _f32(0.4):
        z=0.0
    direction=(z,_f32(y*_f32(1.414)),_f32(x*_f32(-1.414)))
    squares=[_f32(v*v) for v in direction]
    length=_f32(math.sqrt(_f32(_f32(squares[0]+squares[2])+squares[1])))
    if length <= _f32(0.01):
        scale=0.0
    else:
        primary_length=_f32(math.sqrt(_f32(_f32(x*x)+_f32(y*y))))
        amplitude=max(primary_length,abs(z))
        scale=_f32(_f32(_f32(_f32(amplitude*limit)*_f32(math.pi))/180.0)/length)
    return tuple(_f32(v*scale) for v in direction)
