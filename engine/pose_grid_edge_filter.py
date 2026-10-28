"""Grid edge rejection; LINK_SOLVER.md, Grid edge rejection predicate."""
import math
import struct
from reference.central_impulse import f32
from engine.pose_grid_cell import write_grid_edge_neighbors


def reject_grid_edge(resource,samples,first_id,second_id,first_vertex,
                     second_vertex,direction,threshold):
    """Evaluate the recovered predicate on finite, nondegenerate XYZ inputs.

    Threshold has four lanes: all four participate in the near-zero gate;
    only XYZ thresholds participate in rejection. Recognized index differences
    are required because the native unsupported path reads prior scratch data.
    """
    width=struct.unpack_from('<H',resource,0x68)[0]
    allowed=(1,width,width-1 if resource[0x58] else width+1)
    if abs(first_id-second_id) not in allowed:
        raise ValueError('Recognized edge difference required')
    a,b,d=[list(map(f32,v)) for v in (first_vertex,second_vertex,direction)]
    t=list(map(f32,threshold))
    if any(len(v)!=3 for v in (a,b,d)) or len(t)!=4:
        raise ValueError('XYZ vertices/direction and four threshold lanes required')
    if not all(math.isfinite(x) for v in (a,b,d,t) for x in v):
        raise ValueError('Finite inputs required')
    out=bytearray(24)
    write_grid_edge_neighbors(resource,samples,first_id,second_id,out)
    n0=struct.unpack_from('<3f',out);n1=struct.unpack_from('<3f',out,12)
    def sub(x,y):return [f32(i-j) for i,j in zip(x,y)]
    def dot(x,y):
        p=[f32(i*j) for i,j in zip(x,y)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    def normalize(x):
        length=f32(math.sqrt(dot(x,x)))
        if not length>0:raise ValueError('Nondegenerate edge/normalization required')
        inv=f32(1./length)
        return [f32(v*inv) for v in x]
    def cross(x,y):
        return [f32(f32(x[1]*y[2])-f32(x[2]*y[1])),
                f32(f32(x[2]*y[0])-f32(x[0]*y[2])),
                f32(f32(x[0]*y[1])-f32(x[1]*y[0]))]
    edge=normalize(sub(a,b))
    u,v=sub(n0,b),sub(n1,a)
    def maybe_normalize(x):
        return x if all(abs(q)<=limit for q,limit in zip(x+[0.],t)) else normalize(x)
    u,v=maybe_normalize(u),maybe_normalize(v)
    first=dot(cross(cross(edge,u),edge),d)
    if all(first>limit for limit in t[:3]):return True
    second=dot(cross(edge,cross(v,edge)),d)
    return all(second>limit for limit in t[:3])
