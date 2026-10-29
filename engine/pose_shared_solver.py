"""One-body shared-row iteration; LINK_SOLVER.md, Shared patch iteration."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read


def iterate_pose_shared_row(row,*,body_data,body_state,results):
    """Consume a prepared208-byte row; inverse response matrix must be supplied."""
    if len(row)!=208:raise ValueError('Complete208-byte shared row required')
    body=struct.unpack_from('<H',row)[0];index=struct.unpack_from('<I',row,4)[0]
    data,state,result=body_data[body],body_state[body],results[index]
    if len(data)!=64 or len(state)!=32 or len(result)!=16:raise ValueError('Complete body and result records required')
    def transform(rows,v):
        return [f32(f32(rows[2][j]*v[2])+f32(f32(rows[1][j]*v[1])+f32(rows[0][j]*v[0]))) for j in range(4)]
    def dot4(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+p[3]))
    linear=[_read(row,o) for o in (0x20,0x30,0x40)]
    angular=[_read(row,o) for o in (0x50,0x60,0x70)]
    inverse=[_read(row,o) for o in (0x80,0x90,0xa0)]
    old=_read(result,0);accum=_read(row,0xb0);coefficient=_read(row,0xc0)
    limit=[f32(a*b) for a,b in zip(accum,coefficient)]
    row[0xb0:0xc0]=bytes(16)
    linear_speed=transform(linear,_read(state,0));angular_speed=transform(angular,_read(state,16))
    speed=[-f32(a+b) for a,b in zip(linear_speed,angular_speed)]
    correction=transform(inverse,speed);candidate=[f32(a+b) for a,b in zip(old,correction)]
    squared=[f32(x*x) for x in candidate[:3]]
    length=f32(math.sqrt(f32(f32(squared[0]+squared[1])+f32(squared[2]+0.0))))
    if all(limit[j]<length for j in range(3)):
        if length==0:raise ValueError('Nonsingular projection required')
        candidate=[f32(candidate[j]*f32(limit[j]/length)) for j in range(4)]
    delta=[f32(a-b) for a,b in zip(candidate,old)]
    updated=[f32(a+b) for a,b in zip(old,delta)]
    mass=_read(data,48);weighted=[f32(a*b) for a,b in zip(mass,delta)]
    linear_change=[dot4(r,weighted) for r in linear]+[0.0]
    previous=_read(state,0)
    struct.pack_into('<4f',state,0,*[f32(a+b) for a,b in zip(previous,linear_change)])
    torque=[dot4(r,delta) for r in angular]+[0.0]
    angular_change=transform([_read(data,o) for o in (0,16,32)],torque)
    previous=_read(state,16)
    struct.pack_into('<4f',state,16,*[f32(a+b) for a,b in zip(angular_change,previous)])
    struct.pack_into('<4f',result,0,*updated)
