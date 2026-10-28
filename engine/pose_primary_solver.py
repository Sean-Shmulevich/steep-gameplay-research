"""Recovered one-body primary-row preparation and projected iteration.

Evidence: LINK_SOLVER.md, Primary row numerical preparation and iteration.
"""
import math
import struct
from reference.central_impulse import f32


def _read(buffer,offset):
    v=struct.unpack_from('<4f',buffer,offset)
    if not all(math.isfinite(x) for x in v):raise ValueError('Finite row/state/data lanes required')
    return v


def _dot(a,b):
    p=[f32(a[i]*b[i]) for i in range(3)]
    return f32(f32(p[0]+p[1])+f32(p[2]+0.0))


def _weighted(row,data):
    d=_read(row,0x20);a=_read(row,0x30)
    x,y,z,m=[_read(data,i*16) for i in range(4)]
    linear=[f32(m[i]*d[i]) for i in range(4)]
    angular=[f32(f32(z[i]*a[2])+f32(f32(y[i]*a[1])+f32(x[i]*a[0]))) for i in range(4)]
    return d,a,linear,angular


def _storage(row,body_data,body_state,results):
    if len(row)<112:raise ValueError('Retained row storage required')
    body=struct.unpack_from('<H',row)[0];index=struct.unpack_from('<I',row,4)[0]
    data,state,result=body_data[body],body_state[body],results[index]
    if len(data)!=64 or len(state)!=32 or len(result)!=16:raise ValueError('Complete body data/state/result records required')
    return data,state,result


def _apply(state,linear,angular,amount):
    for offset,weighted in ((0,linear),(16,angular)):
        previous=_read(state,offset)
        values=[f32(f32(amount[i]*weighted[i])+previous[i]) for i in range(4)]
        struct.pack_into('<4f',state,offset,*values)


def prepare_pose_primary_row(row,*,body_data,body_state,results):
    """Write reciprocal response and apply the retained result to one body's state."""
    data,state,result=_storage(row,body_data,body_state,results)
    cached=_read(result,0);d,a,linear,angular=_weighted(row,data)
    denominator=f32(f32(_dot(angular,a)+_dot(d,linear))+_read(row,0x60)[0])
    if denominator==0 or not math.isfinite(denominator):raise ValueError('Finite nonsingular denominator required')
    reciprocal=f32(1.0/-denominator)
    struct.pack_into('<4f',row,0x40,*([reciprocal]*4))
    _apply(state,linear,angular,cached)


def iterate_pose_primary_row(row,*,body_data,body_state,results,arena=None,row_offset=0):
    """Update nonnegative result lanes and apply their increments to body state.

    Nonzero row+50 is a signed row-relative16-byte slot index. An explicit arena
    and row_offset allow targets before the row; without them, row is its arena.
    """
    data,state,result=_storage(row,body_data,body_state,results)
    old=_read(result,0);d,a,linear,angular=_weighted(row,data)
    speed=f32(_dot(a,_read(state,16))+_dot(d,_read(state,0)))
    response=_read(row,0x10);inverse=_read(row,0x40)
    updated=[]
    for i in range(4):
        candidate=f32(f32(inverse[i]*f32(speed+response[i]))+old[i])
        updated.append(candidate if candidate>0 else 0.0)
    change=[f32(updated[i]-old[i]) for i in range(4)]
    _apply(state,linear,angular,change)
    _accumulate_primary_result(row,updated,arena=arena,row_offset=row_offset)
    struct.pack_into('<4f',result,0,*updated)


def _accumulate_primary_result(row,updated,*,arena=None,row_offset=0):
    """Resolve the signed native relative link in caller-owned retained storage."""
    slot=struct.unpack_from('<q',row,0x50)[0]
    if not slot:return
    storage=row if arena is None else arena
    if arena is None and row_offset!=0:raise ValueError('Row offset requires explicit arena')
    offset=row_offset+slot*16
    if offset<0 or offset+16>len(storage):raise ValueError('Accumulator outside retained arena')
    old=_read(storage,offset)
    struct.pack_into('<4f',storage,offset,*[f32(old[i]+updated[i]) for i in range(4)])
