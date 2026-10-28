"""Resource transform and bounds refresh.

Evidence: docs/reconstruction/LINK_SOLVER.md, Body resource bounds refresh.
Resource-specific bounds are required services, not assumed box geometry.
"""
import math
import struct
from reference.central_impulse import f32


def compose_pose_resource_transform(parent, local):
    """Return four XYZ rows; fourth lanes are unspecified native scratch bytes."""
    p = [struct.unpack_from('<3f', parent, i*16) for i in range(4)]
    q = [struct.unpack_from('<3f', local, i*16) for i in range(4)]
    if not all(math.isfinite(v) for rows in (p,q) for row in rows for v in row):
        raise ValueError('Finite transforms required')
    rows = [[f32(f32(f32(q[i][0]*p[0][j])+f32(q[i][1]*p[1][j]))+
                 f32(q[i][2]*p[2][j])) for j in range(3)] for i in range(4)]
    rows[3] = [f32(rows[3][j]+p[3][j]) for j in range(3)]
    return rows


def refresh_pose_body_bounds(body, *, entry_arrays, transforms, metadata, resource_bounds):
    """Refresh metadata in retained storage with explicit identity maps.

    Entry arrays contain native-layout 72-byte records. Transforms and metadata
    map opaque identities to raw storage. resource_bounds(identity, four_xyz_rows)
    returns six finite float32 values, minima followed by maxima. Callbacks may
    replace arrays, later records, body transform or metadata identity; count is
    captured once. Concurrent mutation is not supported. An all-null nonempty
    span is rejected as an authored guard, not assigned invented native behavior.
    """
    count = struct.unpack_from('<H', body, 0xc0)[0]
    def entry(i):
        pointer = struct.unpack_from('<Q', body, 0xb8)[0]
        return struct.unpack_from('<QQ', entry_arrays[pointer], i*72+16)
    bounds = None
    for i in range(count):
        resource, transform = entry(i)
        if not resource:
            continue
        frame = compose_pose_resource_transform(body[0x40:0x80], transforms[transform])
        resource, _ = entry(i)
        new = list(map(f32, resource_bounds(resource, frame)))
        if len(new) != 6 or not all(math.isfinite(v) for v in new):
            raise ValueError('Six finite resource bounds required')
        if bounds is None:
            bounds = new
            continue
        for j in range(3):
            if f32(new[j]-bounds[j]) < 0:
                bounds[j] = new[j]
        for j in (3,4,5):
            if f32(new[j]-bounds[j]) >= 0:
                bounds[j] = new[j]
    if bounds is None:
        if count:
            raise ValueError('Nonempty resource span must contain a resource')
        bounds = list(struct.unpack_from('<3f', body, 0x70))*2
    target = struct.unpack_from('<Q', body, 0x30)[0]
    struct.pack_into('<6f', metadata[target], 4, *bounds)
