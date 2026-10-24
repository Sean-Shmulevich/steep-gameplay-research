"""Recovered one-body tangent preparation and primary-result-bounded iteration.

Evidence: CENTRAL_IMPULSE.md, Tangent row numerical preparation and coupling.
"""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read,_dot,_weighted,_storage,_apply


def prepare_pose_tangent_row(row,*,body_data,body_state,results):
    """Prepare inverse response without adding the row60 coupling coefficient."""
    data,state,result=_storage(row,body_data,body_state,results)
    cached=_read(result,0);d,a,linear,angular=_weighted(row,data)
    denominator=f32(_dot(angular,a)+_dot(d,linear))
    if denominator==0 or not math.isfinite(denominator):raise ValueError('Finite nonsingular denominator required')
    reciprocal=f32(1.0/-denominator)
    struct.pack_into('<4f',row,0x40,*([reciprocal]*4))
    _apply(state,linear,angular,cached)


def iterate_pose_tangent_row(row,*,body_data,body_state,results):
    """Clamp accumulated lanes to coefficient times linked primary result.

    State receives old-minus-new result, unlike the primary row's new-minus-old.
    Preserve sequential MINPS/MAXPS operand selection; do not reorder inverted
    bounds. Row10 response fields are not consumed by this iteration routine.
    """
    data,state,result=_storage(row,body_data,body_state,results)
    old=_read(result,0);d,a,linear,angular=_weighted(row,data)
    linked=struct.unpack_from('<I',row,0x50)[0]
    primary=_read(results[linked],0);coefficient=_read(row,0x60)
    bound=[f32(coefficient[i]*primary[i]) for i in range(4)]
    speed=f32(_dot(a,_read(state,16))+_dot(d,_read(state,0)))
    inverse=_read(row,0x40);updated=[]
    for i in range(4):
        candidate=f32(f32(-speed*inverse[i])+old[i])
        upper=candidate if candidate<bound[i] else bound[i]
        lower=-bound[i]
        updated.append(upper if upper>lower else lower)
    change=[f32(old[i]-updated[i]) for i in range(4)]
    _apply(state,linear,angular,change)
    struct.pack_into('<4f',result,0,*updated)
