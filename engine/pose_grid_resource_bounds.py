"""Kind-7 resource bounds; LINK_SOLVER.md, Kind-7 grid resource bounds.

This is a constructor-selected method, not a generic AABB transformation.
"""
import math
import struct
from reference.central_impulse import f32


def grid_resource_bounds(resource, frame):
    """Return minimum XYZ followed by maximum XYZ for four supplied XYZ rows.

    Resource is retained raw storage. Its extent producers and grid loading remain
    separate dependencies. Finite float32 arithmetic only; no live pointers used.
    """
    lo = struct.unpack_from('<3f', resource, 0x7c)
    hi = struct.unpack_from('<3f', resource, 0x88)
    height_pair = struct.unpack_from('<2f', resource, 0x94)
    if len(frame) != 4 or any(len(row) != 3 for row in frame):
        raise ValueError('Four XYZ transform rows required')
    frame = [list(map(f32,row)) for row in frame]
    if not all(math.isfinite(v) for v in (*lo,*hi,*height_pair,
                                         *(v for row in frame for v in row))):
        raise ValueError('Finite bounds and transform required')
    half = [f32(f32(hi[i]-lo[i])*.5) for i in range(3)]
    height_center = f32(f32(height_pair[1]+height_pair[0])*.5)
    radius = [f32(f32(f32(abs(frame[0][j])*half[0])+
                          f32(abs(frame[1][j])*half[1]))+
                     f32(abs(frame[2][j])*half[2])) for j in range(3)]
    center = [f32(f32(f32(f32(frame[0][j]+frame[1][j])*0.)+
                          f32(height_center*frame[2][j]))+frame[3][j])
              for j in range(3)]
    return ([f32(center[j]-radius[j]) for j in range(3)]+
            [f32(radius[j]+center[j]) for j in range(3)])
