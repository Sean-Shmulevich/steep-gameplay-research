"""Categories18/19; LINK_SOLVER.md, Unbounded angular axis solvers."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read,_dot
from .pose_paired_angular_solver import _transform


def _inputs(row,body_data,body_state,results,paired,softened=False):
    if len(row)!=(80 if paired else 64)+(16 if softened else 0):raise ValueError('Complete angular axis row required')
    a,b,index=struct.unpack_from('<HHI',row)
    indices=[a,b] if paired else [a]
    axes=[_read(row,32)]
    if paired:axes.append(_read(row,64))
    return [body_data[i] for i in indices],[body_state[i] for i in indices],results[index],axes


def _apply(data,states,axes,impulse):
    # Componentwise multiply precedes tensor multiplication; endpoint writes are sequential.
    for d,s,axis in zip(data,states,axes):
        torque=[f32(a*p) for a,p in zip(axis,impulse)]
        change=_transform([_read(d,j*16) for j in range(3)],torque)
        struct.pack_into('<4f',s,16,*[f32(o+c) for o,c in zip(_read(s,16),change)])


def prepare_pose_axis_angular_row(row,*,body_data,body_state,results,paired=False,softened=False):
    data,states,result,axes=_inputs(row,body_data,body_state,results,paired,softened)
    terms=[_dot(_transform([_read(d,j*16) for j in range(3)],a),a) for d,a in zip(data,axes)]
    denominator=f32(terms[1]+terms[0]) if paired else terms[0]
    extra=_read(row,80 if paired else 64) if softened else None
    inverse=[]
    for j in range(4):
        value=f32(denominator+extra[j]) if softened else denominator
        if not value or not math.isfinite(value):raise ValueError('Finite nonsingular angular response required')
        inverse.append(f32(1./-value) if j<3 else 0.)
    struct.pack_into('<4f',row,48,*inverse)
    _apply(data,states,axes,_read(result,0))


def iterate_pose_axis_angular_row(row,*,body_data,body_state,results,paired=False,softened=False):
    data,states,result,axes=_inputs(row,body_data,body_state,results,paired,softened)
    terms=[_dot(_read(s,16),a) for s,a in zip(states,axes)]
    speed=f32(terms[1]+terms[0]) if paired else terms[0]
    old=_read(result,0);response=_read(row,16);inverse=_read(row,48)
    delta=[f32(f32(f32(inv*f32(speed+r))+o)-o) for inv,r,o in zip(inverse,response,old)]
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply(data,states,axes,delta)
    struct.pack_into('<4f',result,0,*updated)
