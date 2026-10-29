"""Paired shared-row iteration; LINK_SOLVER.md, Paired shared patch iteration."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read


def iterate_pose_paired_shared_row(row,*,body_data,body_state,results):
    """Consume a prepared256-byte row, updating both bodies sequentially."""
    if len(row)!=256:raise ValueError('Complete256-byte shared row required')
    first,second,index=struct.unpack_from('<HHI',row)
    data=[body_data[first],body_data[second]];states=[body_state[first],body_state[second]];result=results[index]
    if any(len(v)!=64 for v in data) or any(len(v)!=32 for v in states) or len(result)!=16:
        raise ValueError('Complete body and result records required')
    def transform(rows,v):
        return [f32(f32(rows[2][j]*v[2])+f32(f32(rows[1][j]*v[1])+f32(rows[0][j]*v[0]))) for j in range(4)]
    def add(a,b):return [f32(x+y) for x,y in zip(a,b)]
    def dot4(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+p[3]))
    linear=[_read(row,o) for o in (0x20,0x30,0x40)]
    angular=[[_read(row,o+16*j) for j in range(3)] for o in (0x50,0x80)]
    inverse=[_read(row,o) for o in (0xb0,0xc0,0xd0)]
    speed=add(transform(linear,_read(states[0],0)),transform(angular[0],_read(states[0],16)))
    speed=[f32(a-b) for a,b in zip(speed,transform(linear,_read(states[1],0)))]
    speed=add(speed,transform(angular[1],_read(states[1],16)))
    correction=transform(inverse,speed);old=_read(result,0)
    candidate=[f32(-a+b) for a,b in zip(correction,old)]
    limit=[f32(a*b) for a,b in zip(_read(row,0xe0),_read(row,0xf0))]
    squared=[f32(x*x) for x in candidate[:3]]
    length=f32(math.sqrt(f32(f32(squared[0]+squared[1])+f32(squared[2]+0.0))))
    row[0xe0:0xf0]=bytes(16)
    if all(limit[j]<length for j in range(3)):
        if length==0:raise ValueError('Nonsingular projection required')
        candidate=[f32(candidate[j]*f32(limit[j]/length)) for j in range(4)]
    delta=[f32(a-b) for a,b in zip(candidate,old)]
    for i,(d,state) in enumerate(zip(data,states)):
        weighted=[f32(a*b) for a,b in zip(_read(d,48),delta)]
        change=[dot4(r,weighted) for r in linear]+[0.]
        if i:change=[-x for x in change]
        struct.pack_into('<4f',state,0,*add(change,_read(state,0)))
        torque=[dot4(r,delta) for r in angular[i]]+[0.]
        change=transform([_read(d,o) for o in (0,16,32)],torque)
        struct.pack_into('<4f',state,16,*add(change,_read(state,16)))
    struct.pack_into('<4f',result,0,*add(old,delta))
