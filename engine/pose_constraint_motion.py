"""Kind6 row producer; LINK_SOLVER.md, Motion-aware primary constraint producer."""
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read,_dot
from .pose_constraint_point import _xyz
from .pose_constraint_hinge import _cross
from .pose_paired_angular_solver import _transform


def build_pose_motion_constraint(context, constraint, *, bodies, metadata):
    """Produce category2/3 from retained anchors, frames, normal and motion.

    Motion-aware is an authored label. No active gameplay owner is inferred.
    The single-endpoint branch treats the second frame as a fixed anchor frame.
    """
    first,second = struct.unpack_from('<2Q',constraint,8)
    b1,b2 = bodies[first],bodies[second]
    meta = metadata[struct.unpack_from('<Q',b2,0x30)[0]]
    paired = bool(struct.unpack_from('<H',meta,0x50)[0]&0x8000)
    frames = [[_xyz(b,o) for o in (0x40,0x50,0x60)] for b in (b1,b2)]
    anchors = [_read(constraint,o) for o in (0x80,0x90)]
    centers,arms,velocities = [],[],[]
    for endpoint,(b,frame,anchor) in enumerate(zip((b1,b2),frames,anchors)):
        position = _xyz(b,0x70)
        if endpoint == 0 or paired:
            local_center = _xyz(b,0x128)
            center_delta = _transform(frame,local_center)
            center = [f32(p+d) for p,d in zip(position,center_delta)]
            arm = _transform(frame,[f32(a-c) for a,c in zip(anchor,local_center)])
            spin = _cross(_xyz(b,0x1ac),arm)
            velocity = [f32(v+w) for v,w in zip(_xyz(b,0x1a0),spin)]
        else:
            center = position
            arm = _transform(frame,anchor)
            velocity = [0.]*4
        centers.append(center);arms.append(arm);velocities.append(velocity)
    first_point = [f32(a+c) for a,c in zip(arms[0],centers[0])]
    second_point = [f32(c+a) for c,a in zip(centers[1],arms[1])]
    delta = [f32(b-a) for a,b in zip(first_point,second_point)]
    normal = _read(constraint,0xa0)
    direction = [-x for x in normal]
    projected_motion = _dot(normal,[f32(b-a) for a,b in zip(*velocities)])
    motion_term = f32(projected_motion*0.) if f32(projected_motion-0.)<0 else 0.
    scalar = struct.unpack_from('<f',context,0xc)[0]
    bias = struct.unpack_from('<f',context,0x1c)[0]
    positional = f32(f32(_dot(delta,direction)+bias)*(-scalar))
    response = motion_term if f32(abs(positional)-abs(motion_term))<0 else positional
    half = [f32(.5*x) for x in delta]
    angular1 = _cross([f32(h+a) for h,a in zip(half,arms[0])],direction)
    angular2 = _cross(direction,[f32(a-h) for a,h in zip(arms[1],half)]) if paired else None
    category,stride = (3,128) if paired else (2,112)
    u32 = lambda off: struct.unpack_from('<I',context,off)[0]
    count_offset = 0xa4+4*category;count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+4*category)+count*(stride//16))&0xffffffff)
    if row+stride > len(context):raise ValueError('Complete retained motion row storage required')
    index = u32(0x180)
    struct.pack_into('<I',context,0x180,(index+1)&0xffffffff)
    struct.pack_into('<I',context,count_offset,(count+1)&0xffffffff)
    struct.pack_into('<HHI',context,row,struct.unpack_from('<H',b1,0x1c)[0],
                     struct.unpack_from('<H',b2,0x1c)[0],index)
    for off,value in ((0x10,[response]*4),(0x20,direction),(0x30,angular1),(0x60,[0.]*4)):
        struct.pack_into('<4f',context,row+off,*value)
    struct.pack_into('<Q',context,row+0x50,0)
    if paired:struct.pack_into('<4f',context,row+0x70,*angular2)
    return 1
