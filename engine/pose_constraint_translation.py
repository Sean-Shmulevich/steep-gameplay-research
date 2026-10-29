"""Kind2 translation rows; LINK_SOLVER.md, Translation spring row producers."""
import struct
from reference.central_impulse import f32
from .pose_constraint_limit import _vector
from .pose_constraint_hinge import _cross
from .snow_pose_soft_row import soft_pose_row_parameters


def build_pose_translation_row(context, *, single, axis, point_a, point_b,
                               arm_a, arm_b=None, stiffness=None, damping=None):
    """Append hard14/15 or soft16/17 row, leaving endpoint indices untouched.

    Presence of stiffness selects soft arithmetic, not an inferred threshold.
    Caller owns classification. Physical units remain unestablished.
    """
    axis,point_a,point_b,arm_a=map(_vector,(axis,point_a,point_b,arm_a))
    if not single:arm_b=_vector(arm_b)
    soft=stiffness is not None
    if soft:stiffness,damping=map(_vector,(stiffness,damping))
    scalar=struct.unpack_from('<f',context,0xc)[0]
    scalar=_vector([scalar]*4)[0]
    u32=lambda off:struct.unpack_from('<I',context,off)[0]
    category=(16 if soft else 14)+(0 if single else 1)
    stride=(96 if soft else 80)+(0 if single else 16)
    count_offset=0xa4+4*category;count=u32(count_offset)
    row=u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
    if row+stride>len(context):raise ValueError('Complete retained translation row required')
    if soft:
        parameters=soft_pose_row_parameters(stiffness,damping,scalar,u32(0x38))
        gains=[-g for g in parameters['angle_gain']]
    else:gains=[f32(-.4)]*4
    delta=[f32(b-a) for a,b in zip(point_a,point_b)]
    products=[f32(a*d) for a,d in zip(axis,delta)]
    distance=f32(f32(products[0]+products[1])+f32(products[2]+0.))
    response=[f32(distance*f32(g*scalar)) for g in gains]
    response[3]=struct.unpack('<f',bytes.fromhex('ffff7f7f'))[0]
    result=u32(0x180)
    struct.pack_into('<I',context,count_offset,(count+1)&0xffffffff)
    struct.pack_into('<I',context,0x180,(result+1)&0xffffffff)
    struct.pack_into('<I',context,row+4,result)
    for off,v in ((0x10,response),(0x20,axis),(0x30,_cross(arm_a,axis))):
        struct.pack_into('<4f',context,row+off,*v)
    if not single:struct.pack_into('<4f',context,row+0x50,*_cross(axis,arm_b))
    if soft:struct.pack_into('<4f',context,row+(0x50 if single else 0x60),*parameters['coefficient'])
    return row
