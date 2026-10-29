"""Category13 angular row; LINK_SOLVER.md, Paired angular increment solver."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read


def _transform(columns,v):
    return [f32(f32(columns[2][j]*v[2])+f32(f32(columns[1][j]*v[1])+f32(columns[0][j]*v[0]))) for j in range(4)]


def _inputs(row,body_data,body_state,results):
    if len(row)!=80:raise ValueError('Complete80-byte angular row required')
    a,b,index=struct.unpack_from('<HHI',row)
    return [body_data[a],body_data[b]],[body_state[a],body_state[b]],results[index]


def _apply(data,states,impulse):
    for i,(d,s) in enumerate(zip(data,states)):
        change=_transform([_read(d,j*16) for j in range(3)],impulse)
        old=_read(s,16)
        struct.pack_into('<4f',s,16,*[f32(o+c) if i==0 else f32(o-c) for o,c in zip(old,change)])


def prepare_pose_paired_angular_row(row,*,body_data,body_state,results):
    data,states,result=_inputs(row,body_data,body_state,results)
    matrix=[]
    for i in range(3):
        axis=[float(i==j) for j in range(4)]
        a,b=[_read(d,i*16) for d in data];ma,mb=[_read(d,48) for d in data]
        v=[f32(f32(axis[j]*ma[j])+a[j]) for j in range(4)]
        v=[f32(f32(axis[j]*mb[j])+v[j]) for j in range(4)]
        matrix.append([f32(b[j]+v[j]) for j in range(4)])
    for i,column in enumerate(_inverse_matrix(matrix)):
        struct.pack_into('<4f',row,0x20+i*16,*column)
    _apply(data,states,_read(result,0))


def iterate_pose_paired_angular_row(row,*,body_data,body_state,results):
    data,states,result=_inputs(row,body_data,body_state,results)
    old=_read(result,0);response=_read(row,0x10)
    first,second=[_read(s,16) for s in states]
    speed=[f32(response[j]+f32(first[j]-second[j])) for j in range(3)]+[0.]
    candidate=[-x for x in _transform([_read(row,o) for o in (0x20,0x30,0x40)],speed)]
    cap=response[3];lower=-cap
    delta=[v if cap>=v else cap for v in candidate]
    delta=[v if v>lower else lower for v in delta]
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply(data,states,delta)
    struct.pack_into('<4f',result,0,*updated)


def _inverse_matrix(matrix):
    def cross(a,b):return [f32(f32(a[(j+1)%3]*b[(j+2)%3])-f32(a[(j+2)%3]*b[(j+1)%3])) for j in range(3)]
    cof=[cross(matrix[1],matrix[2]),cross(matrix[2],matrix[0]),cross(matrix[0],matrix[1])]
    products=[f32(matrix[0][j]*cof[0][j]) for j in range(3)]
    determinant=f32(f32(products[0]+products[1])+f32(products[2]+0.))
    if not determinant or not math.isfinite(determinant):raise ValueError('Finite nonsingular angular response required')
    inverse=f32(1./determinant)
    columns=[[f32(x*inverse) for x in c] for c in cof]
    return [[columns[j][i] for j in range(3)]+[0.] for i in range(3)]
