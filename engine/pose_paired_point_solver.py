"""Category11 coupled linear/angular solve; LINK_SOLVER.md, Paired point solver."""
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform,_inverse_matrix


def _inputs(row,body_data,body_state,results):
    if len(row)!=176:raise ValueError('Complete176-byte coupled row required')
    a,b,index=struct.unpack_from('<HHI',row)
    return [body_data[a],body_data[b]],[body_state[a],body_state[b]],results[index]


def _axes(row,endpoint):return [_read(row,off) for off in ((0x20,0x30,0x40) if endpoint==0 else (0x80,0x90,0xa0))]
def _dot4(a,b):
    p=[f32(x*y) for x,y in zip(a,b)]
    return f32(f32(p[0]+p[1])+f32(p[2]+p[3]))


def _apply(row,data,states,impulse):
    for i,(d,s) in enumerate(zip(data,states)):
        mass=_read(d,48);old=_read(s,0)
        change=[f32(x*y) for x,y in zip(mass,impulse)]
        struct.pack_into('<4f',s,0,*[f32(o+c) if i==0 else f32(o-c) for o,c in zip(old,change)])
        torque=[_dot4(a,impulse) for a in _axes(row,i)]+[0.]
        angular=_transform([_read(d,j*16) for j in range(3)],torque)
        struct.pack_into('<4f',s,16,*[f32(c+o) for c,o in zip(angular,_read(s,16))])


def prepare_pose_paired_point_row(row,*,body_data,body_state,results):
    data,states,result=_inputs(row,body_data,body_state,results)
    matrix=[]
    for i in range(3):matrix.append([f32(float(i==j)*_read(data[0],48)[j]) for j in range(4)])
    for endpoint,d in enumerate(data):
        axes=_axes(row,endpoint)
        if endpoint:
            mass=_read(d,48)
            matrix=[[f32(f32(float(i==j)*mass[j])+matrix[i][j]) for j in range(4)] for i in range(3)]
        weighted=[_transform(axes,_read(d,j*16)) for j in range(3)]
        contribution=[_transform(weighted,[axes[j][i] for j in range(3)]) for i in range(3)]
        matrix=[[f32(matrix[i][j]+contribution[i][j]) for j in range(4)] for i in range(3)]
    for i,column in enumerate(_inverse_matrix(matrix)):
        struct.pack_into('<4f',row,0x50+i*16,*column)
    _apply(row,data,states,_read(result,0))


def iterate_pose_paired_point_row(row,*,body_data,body_state,results):
    data,states,result=_inputs(row,body_data,body_state,results)
    response=_read(row,16);old=_read(result,0)
    angular=[_transform(_axes(row,i),_read(s,16)) for i,s in enumerate(states)]
    v1,v2=[_read(s,0) for s in states]
    speed=[f32(f32(f32(angular[0][j]+v1[j])-v2[j])+angular[1][j]) for j in range(4)]
    speed=[f32(v+(response[j] if j<3 else 0.)) for j,v in enumerate(speed)]
    candidate=[-x for x in _transform([_read(row,o) for o in (0x50,0x60,0x70)],speed)]
    cap=response[3];lower=-cap
    delta=[v if cap>=v else cap for v in candidate]
    delta=[v if v>lower else lower for v in delta]
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply(row,data,states,delta)
    struct.pack_into('<4f',result,0,*updated)
