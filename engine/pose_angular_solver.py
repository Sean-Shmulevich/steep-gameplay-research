"""Category12 angular row; LINK_SOLVER.md, Single angular increment solver."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform,_inverse_matrix,_apply


def _inputs(row,body_data,body_state,results):
    if len(row)!=80:raise ValueError('Complete80-byte angular row required')
    body=struct.unpack_from('<H',row)[0];index=struct.unpack_from('<I',row,4)[0]
    return body_data[body],body_state[body],results[index]


def prepare_pose_angular_row(row,*,body_data,body_state,results):
    data,state,result=_inputs(row,body_data,body_state,results)
    mass=_read(data,48);matrix=[]
    for i in range(3):
        tensor=_read(data,i*16)
        matrix.append([f32(f32(float(i==j)*mass[j])+tensor[j]) for j in range(4)])
    trace=f32(f32(matrix[0][0]+matrix[1][1])+matrix[2][2])
    if not trace or not math.isfinite(trace):raise ValueError('Finite nonzero response trace required')
    scale=f32(1./trace);lanes=[scale,scale,scale,0.]
    normalized=[[f32(v*s) for v,s in zip(column,lanes)] for column in matrix]
    for i,column in enumerate(_inverse_matrix(normalized)):
        struct.pack_into('<4f',row,0x20+i*16,*[f32(v*s) for v,s in zip(column,lanes)])
    _apply([data],[state],_read(result,0))


def iterate_pose_angular_row(row,*,body_data,body_state,results):
    data,state,result=_inputs(row,body_data,body_state,results)
    old=_read(result,0);response=_read(row,16);angular=_read(state,16)
    speed=[f32(angular[j]+response[j]) for j in range(3)]+[0.]
    candidate=[-x for x in _transform([_read(row,o) for o in (0x20,0x30,0x40)],speed)]
    cap=response[3];lower=-cap
    delta=[v if cap>=v else cap for v in candidate]
    delta=[v if v>lower else lower for v in delta]
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply([data],[state],delta)
    struct.pack_into('<4f',result,0,*updated)
