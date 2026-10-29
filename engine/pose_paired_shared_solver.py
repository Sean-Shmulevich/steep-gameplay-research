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


def prepare_pose_paired_shared_row(row,*,body_data,body_state,results):
    """Build the recovered decoupled response matrix and apply cached result."""
    if len(row)!=256:raise ValueError('Complete256-byte shared row required')
    first,second,index=struct.unpack_from('<HHI',row)
    data=[body_data[first],body_data[second]];states=[body_state[first],body_state[second]];result=results[index]
    if any(len(v)!=64 for v in data) or any(len(v)!=32 for v in states) or len(result)!=16:
        raise ValueError('Complete body and result records required')
    def mul(a,b):return [f32(x*y) for x,y in zip(a,b)]
    def add(a,b):return [f32(x+y) for x,y in zip(a,b)]
    def transform(rows,v):return add(mul(rows[2],[v[2]]*4),add(mul(rows[1],[v[1]]*4),mul(rows[0],[v[0]]*4)))
    def dot4(a,b):
        p=mul(a,b);return f32(f32(p[0]+p[1])+f32(p[2]+p[3]))
    linear=[_read(row,o) for o in (0x20,0x30,0x40)]
    angular=[[_read(row,o+16*j) for j in range(3)] for o in (0x50,0x80)]
    tensors=[[_read(d,o) for o in (0,16,32)] for d in data];masses=[_read(d,48) for d in data]
    axes=([1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.])
    matrix=None
    for k in range(2):
        weighted=[transform(linear,mul(axis,masses[k])) for axis in axes]
        contribution=[transform(weighted,[linear[j][i] for j in range(3)]) for i in range(3)]
        matrix=contribution if matrix is None else [add(contribution[i],matrix[i]) for i in range(3)]
        weighted=[transform(angular[k],t) for t in tensors[k]]
        matrix=[add(matrix[i],transform(weighted,[angular[k][j][i] for j in range(3)])) for i in range(3)]
    mass=add(masses[1],masses[0])
    matrix[0]=mul(matrix[0],[1.,1.,0.,0.]);matrix[1]=mul(matrix[1],[1.,1.,0.,0.])
    matrix[2]=mul(matrix[2],axes[2])
    length=f32(math.sqrt(dot4(matrix[2],matrix[2])))
    if length==0 or not math.isfinite(length):raise ValueError('Nonsingular third response required')
    reciprocal=f32(1./length)
    matrix[2]=mul(mul(matrix[2],[reciprocal]*4),mass)
    def cross(a,b):return [f32(f32(a[(j+1)%3]*b[(j+2)%3])-f32(a[(j+2)%3]*b[(j+1)%3])) for j in range(3)]
    cof=[cross(matrix[1],matrix[2]),cross(matrix[2],matrix[0]),cross(matrix[0],matrix[1])]
    determinant=dot4(matrix[0],[*cof[0],0.])
    if determinant==0 or not math.isfinite(determinant):raise ValueError('Nonsingular response matrix required')
    inv=f32(1./determinant)
    columns=[[f32(v*inv) for v in c] for c in cof]
    inverse=[[columns[j][i] for j in range(3)]+[0.] for i in range(3)]
    inverse[2]=mul([reciprocal]*4,axes[2])
    for o,v in zip((0xb0,0xc0,0xd0),inverse):struct.pack_into('<4f',row,o,*v)
    row[0xe0:0xf0]=bytes(16)
    cached=_read(result,0)
    for k,state in enumerate(states):
        weighted=mul(masses[k],cached)
        change=[dot4(r,weighted) for r in linear]+[0.]
        if k:change=[-x for x in change]
        struct.pack_into('<4f',state,0,*add(_read(state,0),change))
        torque=[dot4(r,cached) for r in angular[k]]+[0.]
        struct.pack_into('<4f',state,16,*add(transform(tensors[k],torque),_read(state,16)))
