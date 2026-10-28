"""Contact point filtering; LINK_SOLVER.md, Contact plane and proximity filtering."""
import struct
from reference.central_impulse import f32


def filter_plane_points(distances, points, count, plane):
    """Compact points on/below the plane and write matching float32 distances."""
    if not 0 <= count <= 128 or len(points) < count*16 or len(distances) < count*4:
        raise ValueError('Complete buffers and count within128 required')
    nx, ny, nz, scalar = map(f32, plane)
    written = 0
    for i in range(count):
        x, y, z = struct.unpack_from('<3f', points, i*16)
        d = f32(f32(f32(f32(nx*x)+(-scalar))+f32(ny*y))+f32(nz*z))
        bits = struct.unpack('<i', struct.pack('<f', d))[0]
        if bits <= 0:
            points[written*16:(written+1)*16] = points[i*16:(i+1)*16]
            struct.pack_into('<f', distances, written*4, d)
            written += 1
    return written


def remove_near_points(distances, points, count, radius):
    """Remove later nearby points by swapping from the end, with their distances."""
    if count < 0 or len(points) < count*16 or len(distances) < count*4:
        raise ValueError('Complete point and distance buffers required')
    radius = f32(radius)
    squared = f32(radius*radius)
    i = 0
    while i < count-1:
        anchor = struct.unpack_from('<3f', points, i*16)
        j = i+1
        while j < count:
            current = struct.unpack_from('<3f', points, j*16)
            delta = [f32(a-b) for a, b in zip(anchor, current)]
            residual = squared
            for d in delta:
                residual = f32(residual-f32(d*d))
            if residual > 0:
                count -= 1
                points[j*16:(j+1)*16] = points[count*16:(count+1)*16]
                distances[j*4:(j+1)*4] = distances[count*4:(count+1)*4]
            else:
                j += 1
        i += 1
    return count


def select_contact_points(distances, points, count, plane, reduce_to_four=False):
    """Filter, deduplicate, then optionally gather four geometric extrema.

    Selection reuses the recovered fixed-angle selector. Nonzero finite plane
    normal required when reduction runs; other stages keep their own contracts.
    """
    from .pose_link_selection import select_pose_link_rows
    count = filter_plane_points(distances, points, count, plane)
    count = remove_near_points(distances, points, count, 1e-4)
    if reduce_to_four and count > 4:
        indices = select_pose_link_rows(
            [struct.unpack_from('<3f', points, i*16) for i in range(count)],
            plane[:3])['indices']
        selected_points = b''.join(bytes(points[i*16:(i+1)*16]) for i in indices)
        selected_distances = b''.join(bytes(distances[i*4:(i+1)*4]) for i in indices)
        points[:64] = selected_points
        distances[:16] = selected_distances
        return 4
    return count
