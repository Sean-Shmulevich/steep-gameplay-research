"""Grid candidate enumeration; LINK_SOLVER.md, Grid triangle candidate enumeration."""
import math
import struct
from reference.central_impulse import f32


def write_grid_triangle_candidates(resource,query,output,capacity):
    """Write uint32 triangle IDs into retained storage; return written count.

    Finite int32-convertible coordinates, positive spacings, nonzero cell
    dimensions and positive capacity are authored domain requirements.
    """
    if not 0 < capacity <= min(len(output)//4,0x7fffffff):
        raise ValueError('Positive retained capacity required')
    lo=struct.unpack_from('<3f',resource,0x7c);hi=struct.unpack_from('<3f',resource,0x88)
    sx,sy=struct.unpack_from('<2f',resource,0x70)
    width,height=struct.unpack_from('<2H',resource,0x9c)
    q=list(map(f32,query))
    if len(q)!=6 or not width or not height or not sx>0 or not sy>0:
        raise ValueError('Six bounds, positive spacing and cell dimensions required')
    if not all(math.isfinite(x) for x in (*lo,*hi,*q,sx,sy)):
        raise ValueError('Finite bounds required')
    low=[lo[j] if f32(lo[j]-q[j])>=0 else q[j] for j in range(3)]
    high=[q[j+3] if f32(hi[j]-q[j+3])>=0 else hi[j] for j in range(3)]
    if low[2]>high[2]:return 0
    def index(value,origin,spacing):
        x=f32(f32(value-origin)*f32(1./spacing))
        if not math.isfinite(x) or not -2147483648<=x<2147483648:
            raise ValueError('int32-convertible cell coordinate required')
        return math.trunc(x)
    x0=max(index(low[0],lo[0],sx),0);x1=min(index(high[0],lo[0],sx),width-1)
    y0=max(index(low[1],lo[1],sy),0);y1=min(index(high[1],lo[1],sy),height-1)
    count=0
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            for half in (0,1):
                struct.pack_into('<I',output,count*4,(2*(y*width+x)+half)&0xffffffff)
                count+=1
                if count>=capacity:return count
    return count
