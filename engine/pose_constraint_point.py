"""Kind1 row production; LINK_SOLVER.md, Point constraint producer."""
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read
from .pose_paired_angular_solver import _transform


def _xyz(buffer, offset):
    return list(struct.unpack_from('<3f', buffer, offset)) + [0.]


def _cross_columns(v):
    x, y, z = v[:3]
    return [[0., z, -y, 0.], [-z, 0., x, 0.], [y, -x, 0., 0.]]


def build_pose_point_constraint(context, constraint, *, bodies, metadata):
    """Append category10 or11 from two retained body frames and local anchors.

    The second body is required even for category10: its frame supplies the other
    world anchor. Metadata bit15 at50 selects the paired numerical row. Counts
    here are append counts, not solver traversal counts. No result initialization.
    """
    first, second = struct.unpack_from('<2Q', constraint, 8)
    body = [bodies[first], bodies[second]]
    paired = bool(struct.unpack_from('<H', metadata[struct.unpack_from('<Q', body[1], 0x30)[0]], 0x50)[0] & 0x8000)
    category = 11 if paired else 10
    stride = 176 if paired else 128
    u32 = lambda off: struct.unpack_from('<I', context, off)[0]
    count_offset = 0xa4+category*4
    count = u32(count_offset)
    row = u32(0x16c)+16*((u32(0x40+category*4)+count*(stride//16)) & 0xffffffff)
    if row+stride > len(context):
        raise ValueError('Complete retained point row storage required')
    frames = [[_xyz(b, off) for off in (0x40,0x50,0x60)] for b in body]
    anchors = [_read(constraint, off) for off in (0x70,0x80)]
    world = []
    arms = []
    for endpoint, (b, frame, anchor) in enumerate(zip(body, frames, anchors)):
        position = _xyz(b, 0x70)
        world.append([f32(f32(frame[2][j]*anchor[2]) +
                         f32(f32(f32(frame[0][j]*anchor[0])+position[j]) +
                             f32(frame[1][j]*anchor[1]))) for j in range(4)])
        if endpoint == 0 or paired:
            local_arm = [f32(a-o) for a, o in zip(anchor, _xyz(b, 0x128))]
            arms.append(_transform(frame, local_arm))
    factor = f32(struct.unpack_from('<f', context, 0xc)[0] *
                 (f32(.4) if u32(0x38)&0x18000000 == 0x08000000 else 0.))
    response = [f32(f32(a-b)*factor) for a, b in zip(*world)]
    response[3] = struct.unpack('<f', bytes.fromhex('ffff7f7f'))[0]
    struct.pack_into('<I', context, count_offset, (count+1)&0xffffffff)
    index = u32(0x180)
    struct.pack_into('<I', context, 0x180, (index+1)&0xffffffff)
    struct.pack_into('<HHI', context, row,
                     struct.unpack_from('<H', body[0], 0x1c)[0],
                     struct.unpack_from('<H', body[1], 0x1c)[0], index)
    struct.pack_into('<4f', context, row+0x10, *response)
    for i, column in enumerate(_cross_columns([-x for x in arms[0]])):
        struct.pack_into('<4f', context, row+0x20+i*16, *column)
    if paired:
        for i, column in enumerate(_cross_columns(arms[1])):
            struct.pack_into('<4f', context, row+0x80+i*16, *column)
    return 1
