"""Drive row production; LINK_SOLVER.md, Angular drive row producer."""
import math
import struct
from reference.central_impulse import f32
from .pose_constraint_limit import _vector


def build_pose_angular_drive_row(context, *, single, mode, axis, sample,
                                 impulse_bound, reference=None, rate_bound=None):
    """Append category14/15; caller writes endpoint indices afterward.

    Mode2 directly negates sample XYZ. Other modes scale sample-reference by
    context_c and clamp it before negation. Physical units remain unestablished.
    """
    axis, sample, bound = map(_vector, (axis, sample, impulse_bound))
    if type(mode) is not int or not 0 <= mode <= 0xffffffff:
        raise ValueError('Unsigned 32-bit mode required')
    u32 = lambda off: struct.unpack_from('<I', context, off)[0]
    scalar, scale = struct.unpack_from('<2f', context, 0xc)
    if not math.isfinite(scalar) or not math.isfinite(scale):
        raise ValueError('Finite context scalars required')
    category, stride = (14,80) if single else (15,96)
    count_offset = 0xa4+4*category
    count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
    if row+stride > len(context):
        raise ValueError('Complete retained angular drive row required')
    response = sample
    if mode != 2:
        reference, cap = map(_vector, (reference, rate_bound))
        response = [f32(f32(x-r)*scalar) for x,r in zip(sample,reference)]
        # SSE MAX/MIN return their second operand on equality.
        response = [x if x > -c else -c for x,c in zip(response,cap)]
        response = [x if x < c else c for x,c in zip(response,cap)]
    response = [-x for x in response]
    response[3] = f32(bound[0]*scale)
    struct.pack_into('<I', context, count_offset, (count+1)&0xffffffff)
    index = u32(0x180)
    struct.pack_into('<I', context, 0x180, (index+1)&0xffffffff)
    struct.pack_into('<I', context, row+4, index)
    struct.pack_into('<4f', context, row+0x10, *response)
    struct.pack_into('<4f', context, row+0x20, 0.,0.,0.,0.)
    struct.pack_into('<4f', context, row+0x30, *axis)
    if not single:
        struct.pack_into('<4f', context, row+0x50, *[-x for x in axis])
    return row
