"""Grid height interpolation; LINK_SOLVER.md, Grid height query."""
import math
import struct
from reference.central_impulse import f32


def query_grid_height(resource, samples, x, y, triangle_id=0xffffffff):
    """Return height and ID, preserving supplied ID outside the grid.

    Finite coordinates, positive dimensions/spans/spacings and complete samples
    required. Samples are caller supplied, not decoded assets.
    """
    width,height=struct.unpack_from('<2H',resource,0x68)
    sx,sy=struct.unpack_from('<2f',resource,0x70)
    ox,oy=struct.unpack_from('<2f',resource,0x7c)
    hx,hy=struct.unpack_from('<2f',resource,0x88)
    x,y=f32(x),f32(y)
    if width<2 or height<2 or not (sx>0 and sy>0 and hx>ox and hy>oy):
        raise ValueError('Positive complete grid required')
    if not math.isfinite(x) or not math.isfinite(y):raise ValueError('Finite XY required')
    col=math.floor(f32(f32(f32(f32(x-ox)-f32(2**-23))*f32(width-1))/f32(hx-ox)))
    row=math.floor(f32(f32(f32(f32(y-oy)-f32(2**-23))*f32(height-1))/f32(hy-oy)))
    if not (0<=col<=width-2 and 0<=row<=height-2):
        return f32(-3.4028234663852886e38),triangle_id
    if len(samples)<width*height:raise ValueError('Complete sample grid required')
    x0=f32(f32(f32(col)*sx)+ox);x1=f32(f32(f32(col+1)*sx)+ox)
    y0=f32(f32(f32(row)*sy)+oy);y1=f32(f32(f32(row+1)*sy)+oy)
    a,b,c,d=[f32(samples[j*width+i]) for i,j in ((col,row),(col+1,row),(col+1,row+1),(col,row+1))]
    dx,dy=f32(x-x0),f32(y-y0)
    tx,ty=f32(dx/sx),f32(dy/sy)
    base=2*(row*struct.unpack_from('<H',resource,0x9c)[0]+col)
    def term(delta,distance,span):return f32(f32(delta*distance)/span)
    if not resource[0x58]:
        if tx>ty:
            first=term(f32(b-a),dx,f32(x1-x0))
            second=term(f32(c-b),f32(y-y0),f32(y1-y0))
            value=f32(f32(first+a)+second);base+=1
        else:
            first=term(f32(c-d),f32(x-x0),f32(x1-x0))
            second=term(f32(d-a),dy,f32(y1-y0))
            value=f32(f32(first+a)+second)
    elif f32(1.-tx)>ty:
        first=term(f32(b-a),dx,f32(x1-x0))
        second=term(f32(d-a),dy,f32(y1-y0))
        value=f32(f32(first+a)+second)
    else:
        first=term(f32(d-c),f32(x-x1),f32(x0-x1))
        second=term(f32(b-c),f32(y-y1),f32(y0-y1))
        value=f32(f32(first+c)+second);base+=1
    return value,base
