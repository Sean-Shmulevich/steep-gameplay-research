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


def build_pose_translation_limit_pair(context, *, single, body_indices, axis,
                                      point_a, point_b, arm_a, arm_b=None,
                                      first_bound, second_bound):
    """Append two category8/9 rows in native order, completing endpoint indices.

    First error adds first_bound; the negated-axis row subtracts second_bound.
    Bounds are not sorted or converted to semantic lower/upper limits here.
    Returns row offsets as an authored inspection convenience.
    """
    axis,point_a,point_b,arm_a,first_bound,second_bound=map(
        _vector,(axis,point_a,point_b,arm_a,first_bound,second_bound))
    if not single:arm_b=_vector(arm_b)
    if len(body_indices)!=2 or any(type(v) is not int or not 0<=v<=0xffffffff for v in body_indices):
        raise ValueError('Two unsigned32 body indices required')
    u32=lambda off:struct.unpack_from('<I',context,off)[0]
    scalar=_vector([struct.unpack_from('<f',context,0xc)[0]]*4)[0]
    phase=f32(.4) if u32(0x38)&0x18000000==0x08000000 else 0.
    category,stride=(8,112) if single else (9,128)
    count_offset=0xa4+4*category
    rows=[]
    delta=[f32(b-a) for a,b in zip(point_a,point_b)]
    for ordinal,direction in enumerate((axis,[-v for v in axis])):
        count=u32(count_offset)
        row=u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
        if row+stride>len(context):raise ValueError('Complete retained translation-limit row required')
        products=[f32(a*d) for a,d in zip(direction,delta)]
        distance=f32(f32(products[0]+products[1])+f32(products[2]+0.))
        error=[f32(distance+b) for b in first_bound] if ordinal==0 else [f32(distance-b) for b in second_bound]
        gain=f32(phase*(-scalar)) if all(v>0 for v in error[:3]) else -scalar
        response=[f32(v*gain) for v in error]
        result=u32(0x180)
        struct.pack_into('<I',context,count_offset,(count+1)&0xffffffff)
        struct.pack_into('<I',context,0x180,(result+1)&0xffffffff)
        struct.pack_into('<HHI',context,row,*(v&0xffff for v in body_indices),result)
        for off,vec in ((0x10,response),(0x20,direction),(0x30,_cross(arm_a,direction)),(0x60,[0.]*4)):
            struct.pack_into('<4f',context,row+off,*vec)
        struct.pack_into('<Q',context,row+0x50,0)
        if not single:struct.pack_into('<4f',context,row+0x70,*_cross(direction,arm_b))
        rows.append(row)
    return tuple(rows)
