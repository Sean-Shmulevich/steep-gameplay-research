"""Angular response producer; LINK_SOLVER.md, Quaternion angular-drive response."""
import math
import struct
from reference.central_impulse import f32
from .pose_constraint_limit import _vector
from .pose_quaternion import pose_matrix_to_quaternion, multiply_pose_quaternions
from .pose_scalar_asin import pose_scalar_asin
from .pose_paired_angular_solver import _transform


def _normalize(q, *, y_first):
    squares = [f32(v*v) for v in q]
    a,b = (1,0) if y_first else (0,1)
    total = f32(f32(f32(squares[a]+squares[b])+squares[2])+squares[3])
    length = f32(math.sqrt(total))
    if not length or not math.isfinite(length):
        raise ValueError('Finite nonzero quaternion norm required')
    reciprocal = f32(1./length)
    return [f32(v*reciprocal) for v in q]


def build_pose_vector_drive_row(context, *, single, cap, strength, gain,
                                frame_a, frame_b, output_frame, additive):
    """Append category12/13; caller supplies body indices after this call.

    Cap applies only when all XYZ cap lanes are strictly below the magnitude.
    Physical units and active gameplay ownership remain unestablished.
    """
    cap,strength,gain,additive = map(_vector,(cap,strength,gain,additive))
    if len(output_frame)!=3:
        raise ValueError('Three four-lane output-frame columns required')
    output_frame = [_vector(c) for c in output_frame]
    scalar,scale = struct.unpack_from('<2f',context,0xc)
    if not all(math.isfinite(v) for v in (scalar,scale)):
        raise ValueError('Finite context scalars required')
    b = _normalize(pose_matrix_to_quaternion(frame_b),y_first=True)
    a = _normalize(pose_matrix_to_quaternion(frame_a),y_first=True)
    products = [f32(x*y) for x,y in zip(a,b)]
    dot = f32(f32(f32(products[1]+products[0])+products[2])+products[3])
    if dot<0:
        a = [-v for v in a]
    conjugate_b = [-b[0],-b[1],-b[2],b[3]]
    q = _normalize(multiply_pose_quaternions(conjugate_b,a),y_first=False)
    # Native subtract-and-compare clamping, then asinf in Z/Y/X order.
    clamped = []
    for v in q[:3]:
        lower = -1. if f32(-1.-v)>=0 else v
        clamped.append(1. if f32(1.-lower)<0 else lower)
    angles = [0.,0.,0.,0.]
    for i in (2,1,0):
        angles[i] = pose_scalar_asin(clamped[i])
    factor = f32(-2.*scalar)
    response = [f32(v*f32(g*factor)) for v,g in zip(angles,gain)]
    squares = [f32(v*v) for v in response[:3]]
    magnitude = f32(math.sqrt(f32(f32(squares[0]+squares[1])+f32(squares[2]+0.))))
    if all(c<magnitude for c in cap[:3]):
        if magnitude==0:
            raise ValueError('Zero magnitude division outside supported domain')
        response = [f32(f32(v/magnitude)*c) for v,c in zip(response,cap)]
    response = [f32(v+a) for v,a in zip(_transform(output_frame,response),additive)]
    response[3] = f32(strength[0]*scale)
    u32 = lambda o:struct.unpack_from('<I',context,o)[0]
    category = 12 if single else 13
    count_offset = 0xa4+4*category
    count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+4*category)+5*count)&0xffffffff)
    if row+80>len(context):
        raise ValueError('Complete retained vector-drive row required')
    result = u32(0x180)
    struct.pack_into('<I',context,count_offset,(count+1)&0xffffffff)
    struct.pack_into('<I',context,0x180,(result+1)&0xffffffff)
    struct.pack_into('<I',context,row+4,result)
    struct.pack_into('<4f',context,row+0x10,*response)
    return row
