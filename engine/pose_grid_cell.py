"""Grid cell geometry; LINK_SOLVER.md, Grid cell vertices and triangle identities."""
import struct
from reference.central_impulse import f32


def grid_cell_geometry(resource, samples, column, row):
    """Return four local XYZ vertices and six local triangle indices.

    Samples are supplied float32 grid values, not decoded asset bytes. Coordinate
    and storage checks are authored guards against native out-of-range reads.
    """
    stride = struct.unpack_from('<H', resource, 0x68)[0]
    if not (0 <= column < stride-1 and 0 <= row < 0xffffffff):
        raise ValueError('A complete nonnegative grid cell is required')
    if (row+1)*stride+column+1 >= len(samples):
        raise ValueError('Missing cell samples')
    sx,sy = struct.unpack_from('<2f',resource,0x70)
    ox,oy = struct.unpack_from('<2f',resource,0x7c)
    vertices = [[f32(f32(f32(x)*sx)+ox),f32(f32(f32(y)*sy)+oy),
                 f32(samples[y*stride+x])]
                for x,y in ((column,row),(column+1,row),
                            (column+1,row+1),(column,row+1))]
    indices = [0,1,3,1,2,3] if resource[0x58] else [0,1,2,2,3,0]
    return vertices, indices


def grid_triangle_sample_indices(resource, triangle_id):
    """Resolve a uint32 triangle identity to three uint32 sample indices.

    The cell-row divisor at0x9c is distinct from sample-row stride at0x68.
    This routine has no height/sample bounds; callers must validate storage.
    Native uint32 wrapping is retained. Zero divisor is an authored rejection.
    """
    if not 0 <= triangle_id <= 0xffffffff:
        raise ValueError('uint32 triangle identity required')
    width = struct.unpack_from('<H', resource, 0x9c)[0]
    stride = struct.unpack_from('<H', resource, 0x68)[0]
    if not width:
        raise ValueError('Nonzero cell-row divisor required')
    row,column = divmod(triangle_id >> 1,width)
    a = row*stride+column
    cell = [a,a+1,a+stride+1,a+stride]
    topology = ([0,1,3,1,2,3] if resource[0x58] else [0,1,2,2,3,0])
    start = (triangle_id&1)*3
    return [cell[i]&0xffffffff for i in topology[start:start+3]]
