"""Face contact emission; LINK_SOLVER.md, Connected face-contact emission."""
import struct
from reference.central_impulse import f32
from .pose_contact_face_polygon import append_face_polygon
from .pose_contact_side_planes import append_side_planes
from .pose_contact_polygon_clip import clip_polygon_planes
from .pose_contact_point_filter import select_contact_points


def emit_face_contacts(output, capacity, reference_frame, reference_shape,
                       incident_frame, incident_shape, reference_face,
                       reduce_to_four=False, flipped=False):
    """Emit 48-byte records from explicit shape vertices/planes/face_indices.

    Finite nondegenerate geometry and helper capacity domains are required.
    Capacity limits writes only; geometry still runs for zero capacity.
    """
    if capacity < 0 or len(output) < capacity*48:
        raise ValueError('Nonnegative capacity with complete output storage required')
    f, g = [[list(map(f32, row)) for row in frame]
            for frame in (reference_frame, incident_frame)]
    def dot(a, b):
        p = [f32(x*y) for x, y in zip(a, b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    x, y, z, scalar = map(f32, reference_shape['planes'][reference_face][:4])
    normal = [f32(f32(f32(f[1][j]*y)+f32(f[0][j]*x))+f32(f[2][j]*z))
              for j in range(3)]
    plane = normal+[f32(dot(f[3], normal)+scalar)]
    local = [dot(row, normal) for row in g[:3]]
    if not incident_shape['planes']:
        raise ValueError('At least one incident plane required')
    incident_face = 0
    best = dot(list(map(f32, incident_shape['planes'][0][:3])), local)
    for i, p in enumerate(incident_shape['planes'][1:], 1):
        value = dot(list(map(f32, p[:3])), local)
        if value < best:
            best, incident_face = value, i
    polygon = bytearray(4096)
    sides = bytearray(0x804)
    append_face_polygon(polygon, g, incident_shape['vertices'],
                        incident_shape['face_indices'][incident_face],
                        reference_face, incident_face, flipped)
    append_side_planes(sides, f, reference_shape['vertices'],
                       reference_shape['face_indices'][reference_face], [x, y, z])
    count = struct.unpack_from('<I', polygon, 0x800)[0]
    side_count = struct.unpack_from('<I', sides, 0x800)[0]
    count = clip_polygon_planes(polygon, count,
                                [struct.unpack_from('<4f', sides, i*16)
                                 for i in range(side_count)])
    distances = bytearray(512)
    count = select_contact_points(distances, polygon, count, plane, reduce_to_four)
    written = min(capacity, count)
    direction = [-v for v in normal] if flipped else normal
    for i in range(written):
        q = struct.unpack_from('<3f', polygon, i*16)
        separation = struct.unpack_from('<f', distances, i*4)[0]
        p = [f32(q[j]-f32(normal[j]*separation)) for j in range(3)]
        first, second = (q, p) if flipped else (p, q)
        struct.pack_into('<4f3fI3fI', output, i*48, *direction, separation,
                         *first, 0, *second, 0xffff0000)
    return written
