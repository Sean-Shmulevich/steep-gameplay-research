"""Recovered optional angular row helper, with unresolved physical field units.

Evidence: CENTRAL_IMPULSE.md, Optional angular drive row.
Drive is our descriptive name, not a recovered engine class name.
"""
import math
import struct
from reference.central_impulse import f32


def build_pose_drive_row(initial_row, *, class_byte, base_row, class_count,
                         row_region_offset, result_count, mode, context_scalar,
                         context_scale, axis, target, current=None, cap=None,
                         strength):
    for v in (base_row,class_count,row_region_offset,result_count,mode):
        if type(v) is not int or not 0<=v<=0xffffffff:
            raise ValueError('Raw uint32 fields required')
    if type(class_byte) is not int or not 0<=class_byte<=255:
        raise ValueError('Raw class byte required')
    stride=5 if class_byte else 6
    if len(initial_row)!=16*stride:raise ValueError('Row size must match class')
    def vector(v):
        if v is None or len(v)!=4:raise ValueError('Four lanes required')
        out=list(map(f32,v))
        if not all(map(math.isfinite,out)):raise ValueError('Finite vectors required')
        return out
    a,t,k=map(vector,(axis,target,strength))
    scale=f32(context_scale)
    if not math.isfinite(scale):raise ValueError('Finite scale required')
    value=t
    if mode!=2:
        c,limit=map(vector,(current,cap));s=f32(context_scalar)
        if not math.isfinite(s):raise ValueError('Finite scalar required')
        value=[]
        for i in range(4):
            x=f32(f32(t[i]-c[i])*s)
            # SSE MAX/MIN select the second operand on equality, including zero.
            x=x if x>-limit[i] else -limit[i]
            x=x if x<limit[i] else limit[i]
            value.append(x)
    packed=[-x for x in value[:3]]+[f32(k[0]*scale)]
    if not all(map(math.isfinite,packed)):raise ValueError('Finite row values required')
    row=bytearray(initial_row)
    struct.pack_into('<I',row,4,result_count)
    struct.pack_into('<4f',row,0x10,*packed)
    row[0x20:0x30]=bytes(16)
    struct.pack_into('<4f',row,0x30,*a)
    if not class_byte:struct.pack_into('<4f',row,0x50,*(-x for x in a))
    return dict(row=bytes(row),relative_offset=row_region_offset+(((base_row+stride*class_count)&0xffffffff)<<4),next_class_count=(class_count+1)&0xffffffff,next_result_count=(result_count+1)&0xffffffff)


def build_optional_pose_drive(*, state, enabled_byte, suppress_notification_byte,
                              swap_byte, primary_axis, swapped_axis, target,
                              strength, body_indices, body_group_present,
                              body_context_present, **layout):
    """First optional angular caller; notification intent, not callback execution.

    Evidence: CENTRAL_IMPULSE.md, Optional angular caller and observer boundary.
    Presence flags describe already resolved caller links; no live dereference.
    """
    if type(state) is not int or not 0<=state<=0xffffffff:
        raise ValueError('Raw uint32 state required')
    if state==0:return dict(row=None,notification_requested=False)
    if type(enabled_byte) is not int or not 0<=enabled_byte<=255:
        raise ValueError('Raw enable byte required')
    if enabled_byte==0:return dict(row=None,notification_requested=False)
    for v in (swap_byte,suppress_notification_byte):
        if type(v) is not int or not 0<=v<=255:raise ValueError('Raw byte required')
    if len(body_indices)!=2 or any(type(v) is not int or not 0<=v<=0xffffffff for v in body_indices):
        raise ValueError('Two raw uint32 body indices required')
    for v in (body_group_present,body_context_present):
        if type(v) is not bool:raise ValueError('Explicit presence flags required')
    row=build_pose_drive_row(axis=swapped_axis if swap_byte else primary_axis,
        target=[target]*4,strength=[strength]*4,mode=2,context_scalar=None,**layout)
    out=bytearray(row['row']);struct.pack_into('<HH',out,0,*(x&0xffff for x in body_indices))
    row['row']=bytes(out)
    return dict(row=row,notification_requested=(suppress_notification_byte==0 and
        body_group_present and body_context_present))
