"""Recovered hard angular pose-row builder.

Evidence: CENTRAL_IMPULSE.md, Hard pose-row helper.
Caller owns row storage, native phases and remaining header completion.
"""
import math
import struct
from reference.central_impulse import f32
from .snow_pose_angle import pose_row_angle


def build_hard_pose_row(initial_row, *, class_byte, base_row, class_count,
                        row_region_offset, result_count, context_scalar,
                        context_flags, axis, reference, target, atan2):
    """Return complete helper writes and next counters for supplied storage."""
    if type(class_byte) is not int or not 0<=class_byte<=255:raise ValueError('Raw class byte required')
    for v in (base_row,class_count,row_region_offset,result_count,context_flags):
        if type(v) is not int or not 0<=v<=0xffffffff:raise ValueError('Raw uint32 fields required')
    stride=4 if class_byte else 5
    if len(initial_row)!=stride*16:raise ValueError('Initial row size must match class')
    scalar=f32(context_scalar)
    if not math.isfinite(scalar):raise ValueError('Finite context scalar required')
    angle=pose_row_angle(axis,reference,target,atan2)
    gain=f32(.4) if context_flags&0x18000000==0x08000000 else 0.
    term=f32(gain*f32(angle['angle']*scalar))
    if not math.isfinite(term):raise ValueError('Finite angular term required')
    row=bytearray(initial_row)
    struct.pack_into('<I',row,4,result_count)
    struct.pack_into('<4f',row,0x10,*([term]*4))
    axis_bytes=struct.pack('<4f',*axis);row[0x20:0x30]=axis_bytes
    if not class_byte:
        row[0x40:0x50]=struct.pack('<4I',*(v^0x80000000 for v in struct.unpack('<4I',axis_bytes)))
    return dict(row=bytes(row),relative_offset=row_region_offset+(((base_row+class_count*stride)&0xffffffff)<<4),
                next_class_count=(class_count+1)&0xffffffff,next_result_count=(result_count+1)&0xffffffff,
                angle=angle,gain=gain)
