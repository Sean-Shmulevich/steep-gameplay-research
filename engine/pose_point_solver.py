"""Category10 coupled solve; LINK_SOLVER.md, Single point solver."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform,_inverse_matrix
from .pose_paired_point_solver import _axes,_apply


def _inputs(row,body_data,body_state,results):
    if len(row)!=128:raise ValueError('Complete128-byte coupled row required')
    body=struct.unpack_from('<H',row)[0];index=struct.unpack_from('<I',row,4)[0]
    return body_data[body],body_state[body],results[index]


def prepare_pose_point_row(row,*,body_data,body_state,results):
    data,state,result=_inputs(row,body_data,body_state,results)
    mass=_read(data,48);axes=_axes(row,0)
    weighted=[_transform(axes,_read(data,j*16)) for j in range(3)]
    contribution=[_transform(weighted,[axes[j][i] for j in range(3)]) for i in range(3)]
    matrix=[[f32(f32(float(i==j)*mass[j])+contribution[i][j]) for j in range(4)] for i in range(3)]
    trace=f32(f32(matrix[0][0]+matrix[1][1])+matrix[2][2])
    if not trace or not math.isfinite(trace):raise ValueError('Finite nonzero response trace required')
    scale=f32(1./trace);lanes=[scale,scale,scale,0.]
    normalized=[[f32(v*s) for v,s in zip(column,lanes)] for column in matrix]
    for i,column in enumerate(_inverse_matrix(normalized)):
        struct.pack_into('<4f',row,0x50+i*16,*[f32(v*s) for v,s in zip(column,lanes)])
    _apply(row,[data],[state],_read(result,0))


def iterate_pose_point_row(row,*,body_data,body_state,results):
    data,state,result=_inputs(row,body_data,body_state,results)
    response=_read(row,16);old=_read(result,0)
    angular=_transform(_axes(row,0),_read(state,16));linear=_read(state,0)
    speed=[f32((response[j] if j<3 else 0.)+f32(angular[j]+linear[j])) for j in range(4)]
    candidate=[-x for x in _transform([_read(row,o) for o in (0x50,0x60,0x70)],speed)]
    cap=response[3];lower=-cap
    delta=[v if cap>=v else cap for v in candidate]
    delta=[v if v>lower else lower for v in delta]
    updated=[f32(o+d) for o,d in zip(old,delta)]
    _apply(row,[data],[state],delta)
    struct.pack_into('<4f',result,0,*updated)
