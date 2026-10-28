"""Single-plane clipping; LINK_SOLVER.md, Single-plane polygon clipping."""
import struct
from reference.central_impulse import f32


def clip_polygon_plane(output, source, count, plane):
    """Write XYZ/tag records and return count; source and output must be distinct.

    Finite inputs, 1..128 input records and room for twice that count required.
    These are authored guards; native capacity argument is not enforced.
    """
    if not 1 <= count <= 128 or len(source) < count*16:
        raise ValueError('One to128 complete source records required')
    if source is output or len(output) < count*32:
        raise ValueError('Distinct output with worst-case capacity required')
    records = [struct.unpack_from('<3fI', source, i*16) for i in range(count)]
    nx, ny, nz, scalar = map(f32, plane)
    distances = []
    for x, y, z, tag in records:
        d = f32(f32(f32(scalar-f32(nx*x))-f32(ny*y))-f32(nz*z))
        if f32(abs(d)-f32(1e-5)) < 0:
            d = 0.
        distances.append(d)
    previous = count-1
    written = 0
    for i, current in enumerate(records):
        a, b = distances[previous], distances[i]
        if (a < 0) != (b < 0):
            inv = f32(1./f32(a-b))
            point = [f32(f32(f32(f32(current[j]-records[previous][j])*a)*inv)
                         + records[previous][j]) for j in range(3)]
            tag = records[previous][3] if a < 0 else current[3]
            struct.pack_into('<3fI', output, written*16, *point, tag)
            written += 1
        if b >= 0:
            output[written*16:(written+1)*16] = source[i*16:(i+1)*16]
            written += 1
        previous = i
    return written
