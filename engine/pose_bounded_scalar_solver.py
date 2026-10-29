"""Categories16/17; LINK_SOLVER.md, Bounded scalar constraint solvers."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read,_dot,_apply
from .pose_paired_primary_solver import _apply_pair
from .pose_paired_angular_solver import _transform


def _inputs(row,body_data,body_state,results,paired):
    if len(row)!=(112 if paired else 96):raise ValueError('Complete bounded scalar row required')
    a,b,index=struct.unpack_from('<HHI',row)
    indices=[a,b] if paired else [a]
    data=[body_data[i] for i in indices];states=[body_state[i] for i in indices]
    direction=_read(row,32);axes=[_read(row,48)]
    if paired:axes.append(_read(row,80))
    weights=[]
    for i,(d,axis) in enumerate(zip(data,axes)):
        mass=_read(d,48)
        linear=[f32(m*(v if i==0 else -v)) for m,v in zip(mass,direction)]
        angular=_transform([_read(d,j*16) for j in range(3)],axis)
        weights.append((linear,angular))
    return data,states,results[index],direction,axes,weights


def _apply_all(states,weights,amount,paired):
    if paired:_apply_pair(states,weights,amount)
    else:_apply(states[0],*weights[0],amount)


def prepare_pose_bounded_scalar_row(row,*,body_data,body_state,results,paired=False):
    data,states,result,direction,axes,weights=_inputs(row,body_data,body_state,results,paired)
    # Both denominator linear terms use the positive direction before squaring.
    linear=[_dot(direction,[f32(m*v) for m,v in zip(_read(d,48),direction)]) for d in data]
    denominator=f32(_dot(weights[0][1],axes[0])+linear[0])
    if paired:
        denominator=f32(denominator+linear[1])
        denominator=f32(denominator+_dot(weights[1][1],axes[1]))
    softness=_read(row,0x60 if paired else 0x50)
    inverse=[]
    for j in range(4):
        value=f32(denominator+softness[j])
        if not value or not math.isfinite(value):raise ValueError('Finite nonsingular scalar response required')
        inverse.append(f32(1./-value) if j<3 else 0.)
    struct.pack_into('<4f',row,64,*inverse)
    _apply_all(states,weights,_read(result,0),paired)


def iterate_pose_bounded_scalar_row(row,*,body_data,body_state,results,paired=False):
    data,states,result,direction,axes,weights=_inputs(row,body_data,body_state,results,paired)
    speed=f32(_dot(axes[0],_read(states[0],16))+_dot(direction,_read(states[0],0)))
    if paired:
        second=f32(_dot(axes[1],_read(states[1],16))+_dot([-v for v in direction],_read(states[1],0)))
        speed=f32(speed+second)
    old=_read(result,0);response=_read(row,16);inverse=_read(row,64)
    delta=[]
    for j in range(4):
        value=f32(inverse[j]*f32(speed+response[j if j<3 else 0]))
        if not paired:value=f32(f32(value+old[j])-old[j])
        capped=value if response[3]>=value else response[3]
        delta.append(capped if capped>-response[3] else -response[3])
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply_all(states,weights,delta,paired)
    struct.pack_into('<4f',result,0,*updated)
