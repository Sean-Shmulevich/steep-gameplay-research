"""Kind3 composite builder; LINK_SOLVER.md, Kind3 constraint composition.

Hinge is an authored descriptive name, not a recovered class identity.
"""
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform
from .pose_constraint_point import _xyz, _cross_columns
from .pose_constraint_angle import select_pose_angle_interval, pose_constraint_drive_sample
from .pose_constraint_limit import build_pose_angular_limit_row
from .pose_constraint_drive import build_pose_angular_drive_row
from .snow_pose_angle import pose_row_angle


def _cross(a, b):
    return [f32(f32(a[j]*b[k])-f32(b[j]*a[k])) for j,k in ((1,2),(2,0),(0,1))]+[0.]


def build_pose_hinge_constraint(context, constraint, *, bodies, metadata, atan2,
                                 notify=None):
    """Append two-stage, two limit and optional drive rows in native order.

    atan2 is explicit. A reached notification requires notify(body_token, 2).
    Finite retained storage and normal callback returns define the supported
    domain. Callback-driven mutation and native exceptional math are not modeled.
    """
    first, second = struct.unpack_from('<2Q', constraint, 8)
    body = [bodies[first], bodies[second]]
    meta = metadata[struct.unpack_from('<Q', body[1], 0x30)[0]]
    single = not bool(struct.unpack_from('<H', meta, 0x50)[0]&0x8000)
    indices = [struct.unpack_from('<H', b, 0x1c)[0] for b in body]
    config = bytes(constraint[0x70:0x100])
    if len(config) != 0x90:
        raise ValueError('Complete retained kind3 configuration required')
    frames = [[_xyz(b,o) for o in (0x40,0x50,0x60)] for b in body]
    anchors = [_read(config,o) for o in (0,16)]
    world, arms = [], []
    for endpoint,(b,frame,anchor) in enumerate(zip(body,frames,anchors)):
        position = _xyz(b,0x70)
        world.append([f32(f32(frame[2][j]*anchor[2])+
                         f32(f32(f32(frame[0][j]*anchor[0])+position[j])+
                             f32(frame[1][j]*anchor[1]))) for j in range(4)])
        if endpoint == 0 or not single:
            local = [f32(a-c) for a,c in zip(anchor,_xyz(b,0x128))]
            arms.append(_transform(frame,local))
    u, v = [_transform(frame,_read(config,o)) for frame,o in zip(frames,(0x20,0x30))]
    p, q = [_transform(frame,_read(config,o)) for frame,o in zip(frames,(0x40,0x50))]
    cross = _cross(u,p)
    columns = [[0.,p[j],cross[j],0.] for j in range(3)]
    u32 = lambda off: struct.unpack_from('<I',context,off)[0]
    flags = u32(0x38)
    factor = f32(struct.unpack_from('<f',context,0xc)[0]*
                 (f32(.4) if flags&0x18000000 == 0x08000000 else 0.))
    linear_response = [f32(f32(a-b)*factor) for a,b in zip(*world)]
    angular_error = [f32(x*factor) for x in _cross(v,u)]
    angular_response = _transform(columns,angular_error)
    category,stride = (22,256) if single else (23,352)
    count_offset = 0xa4+4*category
    count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
    if row+stride > len(context):
        raise ValueError('Complete retained kind3 row storage required')
    struct.pack_into('<I',context,count_offset,(count+1)&0xffffffff)
    index = u32(0x180)
    struct.pack_into('<I',context,0x180,(index+1)&0xffffffff)
    struct.pack_into('<HHI',context,row,*indices,index)
    struct.pack_into('<4f',context,row+0x10,*linear_response)
    for i,column in enumerate(_cross_columns([-x for x in arms[0]])):
        struct.pack_into('<4f',context,row+0x20+i*16,*column)
    for i,column in enumerate(columns):
        struct.pack_into('<4f',context,row+0x80+i*16,*column)
    struct.pack_into('<4f',context,row+0xe0,*angular_response)
    context[row+0xf0:row+0x100] = bytes(16)
    if not single:
        for i,column in enumerate(_cross_columns(arms[1])):
            struct.pack_into('<4f',context,row+0x100+i*16,*column)
        # Transpose rows zero,-p,-cross; the first column components stay +0.
        for j in range(3):
            struct.pack_into('<4f',context,row+0x130+j*16,0.,-p[j],-cross[j],0.)
    swap = bool(constraint[0x59])
    angle = pose_row_angle(v,p,q,atan2)['angle']
    lower,upper = struct.unpack_from('<2f',config,0x60)
    selected_lower,selected_upper = (-upper,-lower) if swap else (lower,upper)
    angle = select_pose_angle_interval([angle]*4,[selected_lower]*4,[selected_upper]*4)
    term,mix = struct.unpack_from('<2f',config,0x78)
    for sign,bound in ((-1.,selected_upper),(1.,-selected_lower)):
        offset = build_pose_angular_limit_row(context,single=single,axis=v,coordinate=angle,
            sign=[sign]*4,offset=[bound]*4,response_term=[term]*4,response_mix=[mix]*4)
        struct.pack_into('<HH',context,offset,*indices)
    mode = struct.unpack_from('<I',config,0x68)[0]
    if mode:
        sample = pose_constraint_drive_sample(constraint)
        if swap: sample = -sample
        target,cap = struct.unpack_from('<2f',config,0x70)
        offset = build_pose_angular_drive_row(context,single=single,mode=mode,axis=v,
            sample=[sample]*4,reference=angle,rate_bound=[target]*4,impulse_bound=[cap]*4)
        struct.pack_into('<HH',context,offset,*indices)
        if not config[0x80] and struct.unpack_from('<Q',body[0],0x10)[0]:
            first_meta = metadata[struct.unpack_from('<Q',body[0],0x30)[0]]
            if struct.unpack_from('<Q',first_meta,0x20)[0]:
                if notify is None: raise ValueError('Reached body notification requires explicit service')
                notify(first,2)
    return 1
