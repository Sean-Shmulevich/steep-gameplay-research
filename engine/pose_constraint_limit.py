"""Angular limit row production; LINK_SOLVER.md, Angular limit row producer."""
import math
import struct
from reference.central_impulse import f32

THRESHOLD = f32(1e12)
EPSILON = f32(1e-6)


def _vector(value):
    if len(value) != 4 or not all(math.isfinite(x) for x in value):
        raise ValueError('Four finite input lanes required')
    return [f32(x) for x in value]


def _divide(a, b):
    if not b or not math.isfinite(b):
        raise ValueError('Finite nonzero response denominator required')
    return f32(a/b)


def build_pose_angular_limit_row(context, *, single, axis, coordinate, sign,
                                 offset, response_term, response_mix):
    """Append category8/9 and return its arena offset; caller writes body indices.

    Names describe the arithmetic arguments, not recovered physical units.
    Raw four-lane inputs preserve the native all-lane nonnegative test. No result
    initialization or traversal-count publication is supplied.
    """
    axis, coordinate, sign, offset, term, mix = map(
        _vector, (axis, coordinate, sign, offset, response_term, response_mix))
    u32 = lambda off: struct.unpack_from('<I', context, off)[0]
    flags = u32(0x38)
    scalar = struct.unpack_from('<f', context, 0xc)[0]
    if not math.isfinite(scalar):
        raise ValueError('Finite context scalar required')
    category, stride = (8,112) if single else (9,128)
    count_offset = 0xa4+4*category
    count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
    if row+stride > len(context):
        raise ValueError('Complete retained angular limit row required')
    error = [f32(f32(c*s)+o) for c,s,o in zip(coordinate,sign,offset)]
    nonnegative = all(x >= 0 for x in error)
    if all(x < THRESHOLD for x in term[:3]):
        added = term[:]
        gain = [f32(.4)]*4
        if abs(scalar) > EPSILON:
            iterations = f32((flags>>2)&0x3fff)
            divisor = f32(iterations*scalar)
            added = [f32(_divide(1.,f32(_divide(t,divisor)+m))*scalar)
                     for t,m in zip(term,mix)]
            gain = [_divide(t,f32(t+f32(iterations*f32(scalar*m)))) for t,m in zip(term,mix)]
        if nonnegative:
            response = [THRESHOLD]*4
            added = [0.]*4
        else:
            response = [f32(f32(scalar*e)*g) for e,g in zip(error,gain)]
    else:
        added = [0.]*4
        response = [f32(scalar*e) for e in error]
        if not nonnegative:
            gain = f32(.4) if flags&0x18000000 == 0x08000000 else 0.
            response = [f32(gain*r) for r in response]
    struct.pack_into('<I', context, count_offset, (count+1)&0xffffffff)
    index = u32(0x180)
    struct.pack_into('<I', context, 0x180, (index+1)&0xffffffff)
    struct.pack_into('<I', context, row+4, index)
    struct.pack_into('<4f', context, row+0x10, *response)
    struct.pack_into('<4f', context, row+0x20, 0.,0.,0.,0.)
    struct.pack_into('<4f', context, row+0x30, *[f32(a*s) for a,s in zip(axis,sign)])
    struct.pack_into('<Q', context, row+0x50, 0)
    struct.pack_into('<4f', context, row+0x60, *added)
    if not single:
        struct.pack_into('<4f', context, row+0x70, *[f32(a*(-s)) for a,s in zip(axis,sign)])
    return row
