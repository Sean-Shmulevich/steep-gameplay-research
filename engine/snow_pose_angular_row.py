"""Recovered state0 angular row selection and caller header completion.

Evidence: CENTRAL_IMPULSE.md, State0 angular row caller.
Prepared world-space vectors and context layout remain supplied inputs.
"""
import math
import struct
from reference.central_impulse import f32
from .snow_pose_solver_counts import HARD_THRESHOLD
from .snow_pose_soft_row import build_soft_pose_row
from .snow_pose_hard_row import build_hard_pose_row


def build_pose_angular_spring_row(*, stiffness, damping, body_indices,
                                  hard_layout, soft_layout, **common):
    """Build one reached state0 row; select only the needed layout.

    Layout contains initial_row, base_row, class_count. Common fields are the
    chosen helper's other inputs. Body indices are raw uint32, stored as low16.
    State1 skip, state2 limit rows and other caller branches remain external.
    """
    k=f32(stiffness)
    if not math.isfinite(k):raise ValueError('Finite stiffness required')
    if len(body_indices)!=2 or any(type(x) is not int or not 0<=x<=0xffffffff for x in body_indices):
        raise ValueError('Two raw uint32 body indices required')
    if k<HARD_THRESHOLD:
        result=build_soft_pose_row(**soft_layout,stiffness=[k]*4,damping=[damping]*4,**common)
        kind='soft'
    else:
        result=build_hard_pose_row(**hard_layout,**common)
        kind='hard'
    out=bytearray(result['row']);struct.pack_into('<HH',out,0,*(x&0xffff for x in body_indices))
    result['row']=bytes(out);result['kind']=kind
    return result
