"""Recovered two-body primary-row numerical preparation and iteration.

Evidence: LINK_SOLVER.md, Paired-body primary numerical solver.
"""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read, _dot, _apply, _accumulate_primary_result


def _inputs(row,body_data,body_state,results):
    if len(row)<128:raise ValueError('Complete paired row required')
    first,second,index=struct.unpack_from('<HHI',row)
    data=[body_data[first],body_data[second]]
    states=[body_state[first],body_state[second]]
    result=results[index]
    if any(len(v)!=64 for v in data) or any(len(v)!=32 for v in states) or len(result)!=16:
        raise ValueError('Complete data/state/result records required')
    direction=_read(row,0x20)
    axes=[_read(row,0x30),_read(row,0x70)]
    weights=[]
    for i,(d,a) in enumerate(zip(data,axes)):
        x,y,z,m=[_read(d,j*16) for j in range(4)]
        linear=[f32(m[j]*(direction[j] if i==0 else -direction[j])) for j in range(4)]
        angular=[f32(f32(z[j]*a[2])+f32(f32(y[j]*a[1])+f32(x[j]*a[0]))) for j in range(4)]
        weights.append((linear,angular))
    return data,states,result,direction,axes,weights


def _apply_pair(states,weights,amount):
    # Native captures second-body state before writing the first. For coincident
    # indices the second update wins, rather than accumulating both updates.
    snapshots=[bytearray(s) for s in states]
    for snapshot,(linear,angular) in zip(snapshots,weights):
        _apply(snapshot,linear,angular,amount)
    for state,snapshot in zip(states,snapshots):state[:]=snapshot


def prepare_pose_paired_primary_row(row,*,body_data,body_state,results):
    data,states,result,direction,axes,weights=_inputs(row,body_data,body_state,results)
    square=_dot(direction,direction)
    contributions=[f32(_dot(w[1],a)+f32(_read(d,0x30)[0]*square))
                   for d,a,w in zip(data,axes,weights)]
    denominator=f32(f32(contributions[0]+contributions[1])+_read(row,0x60)[0])
    if denominator==0 or not math.isfinite(denominator):
        raise ValueError('Finite nonsingular denominator required')
    reciprocal=-f32(1.0/denominator)
    struct.pack_into('<4f',row,0x40,*([reciprocal]*4))
    _apply_pair(states,weights,_read(result,0))


def iterate_pose_paired_primary_row(row,*,body_data,body_state,results,arena=None,row_offset=0):
    data,states,result,direction,axes,weights=_inputs(row,body_data,body_state,results)
    angular=f32(_dot(axes[1],_read(states[1],16))+_dot(axes[0],_read(states[0],16)))
    linear=f32(_dot([-x for x in direction],_read(states[1],0))+_dot(direction,_read(states[0],0)))
    speed=f32(linear+angular)
    old=_read(result,0);response=_read(row,0x10);inverse=_read(row,0x40)
    updated=[]
    for i in range(4):
        value=f32(f32(inverse[i]*f32(speed+response[i]))+old[i])
        updated.append(value if value>0 else 0.0)
    _apply_pair(states,weights,[f32(a-b) for a,b in zip(updated,old)])
    _accumulate_primary_result(row,updated,arena=arena,row_offset=row_offset)
    struct.pack_into('<4f',result,0,*updated)
