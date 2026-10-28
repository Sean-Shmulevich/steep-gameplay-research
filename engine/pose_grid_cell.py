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


def grid_triangle_vertices(resource, samples, triangle_id):
    """Return three XYZ0 rows for the consumer's triangle identity.

    Evidence: LINK_SOLVER.md, Grid triangle vertex consumer boundary.
    The fourth lane is positive zero under the supplied initialized XYZ mask.
    This guarded composition is validated against the separate native method;
    it is not a claim that the native method calls the cell helper.
    """
    if not 0 <= triangle_id <= 0xffffffff:
        raise ValueError('uint32 triangle identity required')
    divisor = struct.unpack_from('<H', resource, 0x9c)[0]
    if not divisor:
        raise ValueError('Nonzero cell-row divisor required')
    row,column = divmod(triangle_id >> 1,divisor)
    vertices,indices = grid_cell_geometry(resource,samples,column,row)
    start = (triangle_id&1)*3
    return [vertices[i]+[0.] for i in indices[start:start+3]]


def grid_vertex_neighbors(resource, samples, sample_id):
    """Return ordered neighboring XYZ vertices for the contact filter.

    Evidence: LINK_SOLVER.md, Grid vertex neighborhood and contact-filter lead.
    Positive dimensions and an in-range vertex are authored API requirements.
    The native helper's first context argument is unused.
    """
    width,height = struct.unpack_from('<2H',resource,0x68)
    if not width or not height or not 0 <= sample_id < width*height:
        raise ValueError('Valid vertex in a nonempty grid required')
    if len(samples) < width*height:
        raise ValueError('Complete sample storage required')
    row,column = divmod(sample_id,width)
    offsets = ([(0,1),(1,0),(1,-1),(0,-1),(-1,0),(-1,1)]
               if resource[0x58] else
               [(0,1),(1,1),(1,0),(0,-1),(-1,-1),(-1,0)])
    sx,sy = struct.unpack_from('<2f',resource,0x70)
    ox,oy = struct.unpack_from('<2f',resource,0x7c)
    result=[]
    for dx,dy in offsets:
        x,y=column+dx,row+dy
        if 0 <= x < width and 0 <= y < height:
            result.append([f32(f32(f32(x)*sx)+ox),
                           f32(f32(f32(y)*sy)+oy),f32(samples[y*width+x])])
    return result


def write_grid_edge_neighbors(resource, samples, first_id, second_id, output):
    """Write two ordered XYZ edge-neighbor positions to retained 24-byte output.

    Evidence: LINK_SOLVER.md, Grid edge neighborhood.
    A missing neighbor falls back to the smaller endpoint's position. Unsupported
    index differences preserve prior output, followed by the usual order swap.
    Valid endpoints and complete nonempty storage are authored API requirements.
    """
    width,height = struct.unpack_from('<2H',resource,0x68)
    if not width or not height or len(samples) < width*height or len(output) < 24:
        raise ValueError('Complete grid and retained output required')
    if not all(0 <= i < width*height for i in (first_id,second_id)):
        raise ValueError('Valid endpoint identities required')
    small,large = sorted((first_id,second_id))
    row,column = divmod(small,width)
    difference=large-small
    offsets=None
    if resource[0x58]:
        if difference==1:offsets=[(1,-1),(0,1)]
        elif difference==width:offsets=[(1,0),(-1,1)]
        elif difference==width-1:offsets=[(0,1),(-1,0)]
    else:
        if difference==1:offsets=[(0,-1),(1,1)]
        elif difference==width:offsets=[(1,1),(-1,0)]
        elif difference==width+1:offsets=[(1,0),(0,1)]
    if offsets is not None:
        sx,sy=struct.unpack_from('<2f',resource,0x70)
        ox,oy=struct.unpack_from('<2f',resource,0x7c)
        for slot,(dx,dy) in enumerate(offsets):
            x,y=column+dx,row+dy
            if not (0 <= x < width and 0 <= y < height):x,y=column,row
            struct.pack_into('<3f',output,slot*12,
                             f32(f32(f32(x)*sx)+ox),
                             f32(f32(f32(y)*sy)+oy),f32(samples[y*width+x]))
    if first_id > second_id:
        output[:24]=output[12:24]+output[:12]
