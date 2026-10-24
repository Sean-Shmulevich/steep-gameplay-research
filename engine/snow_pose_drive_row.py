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
