"""Recovered paired tangent preparation and primary-result-bounded iteration.

Evidence: LINK_SOLVER.md, Paired tangent numerical solver.
"""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read, _dot
from .pose_paired_primary_solver import _inputs, _apply_pair


def _tangent_inputs(row,body_data,body_state,results):
    if len(row)<128:raise ValueError('Complete paired tangent row required')
    # Reuse the weighted-body arithmetic with the tangent layout's second axis.
    adapted=bytearray(row)
    adapted[0x70:0x80]=row[0x50:0x60]
    return _inputs(adapted,body_data,body_state,results)


def prepare_pose_paired_tangent_row(row,*,body_data,body_state,results):
    data,states,result,direction,axes,weights=_tangent_inputs(row,body_data,body_state,results)
    positive_second=[f32(a*b) for a,b in zip(_read(data[1],0x30),direction)]
    denominator=f32(f32(f32(_dot(weights[0][1],axes[0])+_dot(direction,weights[0][0]))+
                          _dot(positive_second,direction))+_dot(weights[1][1],axes[1]))
    if denominator==0 or not math.isfinite(denominator):
        raise ValueError('Finite nonsingular denominator required')
    inverse=f32(1.0/-denominator)
    struct.pack_into('<4f',row,0x40,*([inverse]*4))
    _apply_pair(states,weights,_read(result,0))


def iterate_pose_paired_tangent_row(row,*,body_data,body_state,results):
    data,states,result,direction,axes,weights=_tangent_inputs(row,body_data,body_state,results)
    linked=struct.unpack_from('<I',row,0x60)[0]
    primary=_read(results[linked],0);coefficient=_read(row,0x70)
    bound=[f32(a*b) for a,b in zip(primary,coefficient)]
    first=f32(_dot(axes[0],_read(states[0],16))+_dot(direction,_read(states[0],0)))
    second=f32(_dot(axes[1],_read(states[1],16))+_dot([-x for x in direction],_read(states[1],0)))
    speed=f32(first+second)
    old=_read(result,0);inverse=_read(row,0x40);updated=[]
    for i in range(4):
        candidate=f32(f32(-speed*inverse[i])+old[i])
        upper=candidate if candidate<bound[i] else bound[i]
        lower=-bound[i]
        updated.append(upper if upper>lower else lower)
    _apply_pair(states,weights,[f32(a-b) for a,b in zip(old,updated)])
    struct.pack_into('<4f',result,0,*updated)
