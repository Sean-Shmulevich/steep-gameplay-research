"""Recovered per-body solver-data and initial-state construction.

Evidence: CENTRAL_IMPULSE.md, Solver body-buffer production.
"""
import math
import struct
from reference.central_impulse import f32


def build_pose_body_buffers(bodies, *, scalar, vector, damping_response=None):
    """Return 64-byte data and32-byte state records in supplied body-array order.

    Damping's four-lane library response is an explicit service when reached.
    Inputs are retained and constant during this call. Physical units are not
    assigned to scalar/vector or raw body fields by this API.
    """
    def values(v,n):
        if len(v)!=n:raise ValueError('Unexpected vector length')
        out=[f32(x) for x in v]
        if not all(math.isfinite(x) for x in out):raise ValueError('Finite components required')
        return out
    s=values([scalar],1)[0];external=values(vector,3)+[0.0]
    data=[];state=[]
    for body in bodies:
        fixed=bool(body['metadata_flags52']&8)
        if len(body['basis'])!=3:raise ValueError('Three basis rows required')
        basis=[values(row,3)+[0.0] for row in body['basis']]
        if fixed:tensor=[[0.0]*4 for _ in range(3)]
        else:
            if len(body['tensor170'])!=3:raise ValueError('Three tensor rows required')
            tensor=[values(row,3)+[0.0] for row in body['tensor170']]
        transformed=[]
        for j in range(3):
            temp=[f32(f32(f32(tensor[1][k]*basis[1][j])+f32(tensor[0][k]*basis[0][j]))+f32(tensor[2][k]*basis[2][j])) for k in range(4)]
            transformed.append([f32(f32(basis[2][k]*temp[2])+f32(f32(basis[1][k]*temp[1])+f32(basis[0][k]*temp[0]))) for k in range(4)])
        linear=values(body['motion1a0'],3)+[0.0];angular=values(body['motion1ac'],3)+[0.0]
        mass=0.0
        if not fixed:
            mass=values([body['scalar124']],1)[0]
            selected=[0.0]*4 if body['flagsaa']&8 else external
            linear=[f32(linear[i]+f32(selected[i]*s)) for i in range(4)]
            multiplier=[1.0]*4
            damping=body.get('damping1b8')
            if damping is not None and s!=0:
                if damping_response is None:raise ValueError('Unrecovered damping response service required')
                base=[f32(1.0-x) for x in values(damping,4)]
                multiplier=values(damping_response(base,s),4)
            linear=[f32(linear[i]*multiplier[i]) for i in range(4)]
            angular=[f32(x*multiplier[3]) for x in angular]
        data.append(bytearray(struct.pack('<16f',*[x for row in transformed for x in row],*([mass]*4))))
        state.append(bytearray(struct.pack('<8f',*linear,*angular)))
    return dict(body_data=data,body_state=state)
