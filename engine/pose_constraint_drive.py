"""Drive row production; LINK_SOLVER.md, Angular drive row producer."""
import math
import struct
from .pose_constraint_limit import _vector
from .snow_pose_drive_row import build_pose_drive_row


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
    built = build_pose_drive_row(
        bytes(context[row:row+stride]), class_byte=int(bool(single)),
        base_row=u32(0x40+4*category), class_count=count,
        row_region_offset=u32(0x16c), result_count=u32(0x180), mode=mode,
        context_scalar=scalar, context_scale=scale, axis=axis, target=sample,
        current=reference, cap=rate_bound, strength=bound)
    context[row:row+stride] = built['row']
    struct.pack_into('<I', context, count_offset, built['next_class_count'])
    struct.pack_into('<I', context, 0x180, built['next_result_count'])
    return row
