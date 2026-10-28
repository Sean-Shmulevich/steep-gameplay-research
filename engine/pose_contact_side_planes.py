"""Reference side planes; LINK_SOLVER.md, Reference side-plane construction."""
import math
import struct
from reference.central_impulse import f32


def append_side_planes(storage, frame, vertices, indices, face_normal):
    """Append normal/scalar planes; finite nondegenerate edges are required.

    Storage has 128 sixteen-byte slots and count at 0x800. Capacity and empty
    index guards are authored. No post-transform normalization is substituted.
    """
    if len(storage) < 0x804:
        raise ValueError('Retained plane storage required')
    count = struct.unpack_from('<I', storage, 0x800)[0]
    if not indices or count + len(indices) > 128:
        raise ValueError('Nonempty indices within plane capacity required')
    def dot(a, b):
        p = [f32(x*y) for x, y in zip(a, b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    f = [list(map(f32, row)) for row in frame]
    n = list(map(f32, face_normal[:3]))
    previous = list(map(f32, vertices[indices[-1]]))
    for index in indices:
        current = list(map(f32, vertices[index]))
        e = [f32(a-b) for a, b in zip(current, previous)]
        raw = [f32(f32(e[1]*n[2])-f32(e[2]*n[1])),
               f32(f32(e[2]*n[0])-f32(e[0]*n[2])),
               f32(f32(e[0]*n[1])-f32(e[1]*n[0]))]
        length = f32(math.sqrt(dot(raw, raw)))
        if not length > 0 or not math.isfinite(length):
            raise ValueError('Finite nonzero edge cross face normal required')
        inv = f32(1./length)
        normal = [f32(x*inv) for x in raw]
        distance = dot(normal, previous)
        world = [f32(f32(f32(f[1][j]*normal[1])+f32(f[0][j]*normal[0]))
                     +f32(f[2][j]*normal[2])) for j in range(3)]
        scalar = f32(dot(world, f[3])+distance)
        struct.pack_into('<4f', storage, count*16, *world, scalar)
        count += 1
        struct.pack_into('<I', storage, 0x800, count)
        previous = current
