"""Recovered angular limit-row helper with explicit prepared inputs.

Evidence: CENTRAL_IMPULSE.md, Angular limit-row helper.
No angular-bound producer or downstream solve is supplied here.
"""
import math
import struct
from reference.central_impulse import f32


def build_pose_limit_row(initial_row, *, class_byte, base_row, class_count,
                         row_region_offset, result_count, context_scalar,
                         context_flags, axis, angle, sign, bound):
    """Build complete helper writes; four-lane inputs retain native branch scope."""
    if type(class_byte) is not int or not 0<=class_byte<=255:raise ValueError('Raw class byte required')
    for v in (base_row,class_count,row_region_offset,result_count,context_flags):
        if type(v) is not int or not 0<=v<=0xffffffff:raise ValueError('Raw uint32 fields required')
    stride=7 if class_byte else 8
    if len(initial_row)!=16*stride:raise ValueError('Initial row size must match class')
    if any(len(v)!=4 for v in (axis,angle,sign,bound)):raise ValueError('Four lanes required')
    a,t,d,b=[list(map(f32,v)) for v in (axis,angle,sign,bound)];s=f32(context_scalar)
    if not all(math.isfinite(v) for vec in (a,t,d,b,[s]) for v in vec):raise ValueError('Finite inputs required')
    residual=[f32(f32(t[i]*d[i])+b[i]) for i in range(4)]
    ungained=all(x>=0 for x in residual)
    gain=f32(.4) if context_flags&0x18000000==0x08000000 else 0.
    term=[f32(s*x) for x in residual]
    if not ungained:term=[f32(gain*x) for x in term]
    direction=[f32(a[i]*d[i]) for i in range(4)]
    if not all(math.isfinite(v) for v in residual+term+direction):raise ValueError('Finite intermediate values required')
    row=bytearray(initial_row)
    struct.pack_into('<I',row,4,result_count)
    struct.pack_into('<4f',row,0x10,*term)
    row[0x20:0x30]=bytes(16);struct.pack_into('<4f',row,0x30,*direction)
    row[0x50:0x58]=bytes(8);row[0x60:0x70]=bytes(16)
    if not class_byte:
        struct.pack_into('<4f',row,0x70,*(f32(a[i]*(-d[i])) for i in range(4)))
    return dict(row=bytes(row),relative_offset=row_region_offset+(((base_row+stride*class_count)&0xffffffff)<<4),next_class_count=(class_count+1)&0xffffffff,next_result_count=(result_count+1)&0xffffffff,residual=residual,ungained=ungained)
