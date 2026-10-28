"""Edge contact emission; LINK_SOLVER.md, Edge contact record emission."""
import math
import struct
from reference.central_impulse import f32


def emit_edge_contact(output,capacity,first_frame,first_shape,second_frame,second_shape,selection):
    """Emit one 48-byte record, or return zero before geometry for zero capacity.

    Finite nondegenerate selected edges are required. No invented fallback normal
    is supplied for parallel edges. Output tail storage is retained.
    """
    if capacity==0:return 0
    if capacity<0 or len(output)<48:raise ValueError('Positive retained record capacity required')
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    def sub(a,b):return [f32(x-y) for x,y in zip(a,b)]
    def cross(a,b):return [f32(f32(a[1]*b[2])-f32(a[2]*b[1])),f32(f32(a[2]*b[0])-f32(a[0]*b[2])),f32(f32(a[0]*b[1])-f32(a[1]*b[0]))]
    f,g=[[list(map(f32,row)) for row in frame] for frame in (first_frame,second_frame)]
    def point(frame,v):
        x,y,z=map(f32,v)
        return [f32(f32(f32(f32(frame[0][j]*x)+frame[3][j])+f32(frame[1][j]*y))+f32(frame[2][j]*z)) for j in range(3)]
    def normal(v):
        x,y,z=map(f32,v[:3])
        return [f32(f32(f32(f[1][j]*y)+f32(f[0][j]*x))+f32(f[2][j]*z)) for j in range(3)]
    v0,v1,p0,p1=first_shape['edges'][selection['first']]
    w0,w1,_,_=second_shape['edges'][selection['second']]
    a0,a1=[point(f,first_shape['vertices'][i]) for i in (v0,v1)]
    b0,b1=[point(g,second_shape['vertices'][i]) for i in (w0,w1)]
    n0,n1=[normal(first_shape['planes'][i]) for i in (p0,p1)]
    u,v,w=sub(a1,a0),sub(b1,b0),sub(a0,b0)
    a,b,c,d,e=dot(u,u),dot(v,u),dot(v,v),dot(u,w),dot(v,w)
    det=f32(f32(c*a)-f32(b*b))
    if abs(det)<=f32(a*f32(1e-5)):
        sn=0.;sd=c;tn=e;td=c
    else:
        sn=f32(f32(e*b)-f32(d*c));tn=f32(f32(e*a)-f32(d*b));sd=td=det
        if sn<0:sn=0.;tn=e;td=c
        elif sn>det:sn=det;tn=f32(e+b);td=c
    if tn<0:
        t=0.;q=-d
        s=0. if q<0 else (1. if q>a else f32(q/a))
    elif tn>td:
        t=1.;q=f32(-d+b)
        s=0. if q<0 else (1. if q>a else f32(q/a))
    else:
        t=f32(tn/td);s=f32(sn/sd)
    us=[f32(x*s) for x in u];vt=[f32(x*t) for x in v]
    first=[f32(x+y) for x,y in zip(us,a0)]
    second=[f32(x+y) for x,y in zip(vt,b0)]
    delta=[f32(f32(x+y)-z) for x,y,z in zip(us,w,vt)]
    axis=cross(u,v);length=f32(math.sqrt(dot(axis,axis)))
    if not length>0:raise ValueError('Nonparallel selected edges required')
    inv=f32(1./length);axis=[f32(x*inv) for x in axis]
    if dot([f32(x+y) for x,y in zip(n1,n0)],axis)<0:axis=[-x for x in axis]
    struct.pack_into('<3ff3fI3fI',output,0,*axis,-dot(delta,delta),*first,0,*second,0xffff0000)
    return 1
