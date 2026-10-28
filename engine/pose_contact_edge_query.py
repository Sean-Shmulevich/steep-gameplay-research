"""Edge separation query; LINK_SOLVER.md, Contact edge-distance query."""
import math
from reference.central_impulse import f32


def query_contact_edges(first_frame,first_shape,second_frame,second_shape,result):
    """Replace seeded output using supplied vertices, planes and four-index edges.

    Edges contain vertex0, vertex1, plane0, plane1 indices. Frames have XYZ rows.
    Finite arithmetic and nonzero second-edge lengths required. The second basis
    is transposed, not generally inverted; no frame normalization is substituted.
    """
    def dot(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[0]+p[1])+f32(p[2]+0.))
    def sub(a,b):return [f32(x-y) for x,y in zip(a,b)]
    def cross(a,b):return [f32(f32(a[1]*b[2])-f32(a[2]*b[1])),f32(f32(a[2]*b[0])-f32(a[0]*b[2])),f32(f32(a[0]*b[1])-f32(a[1]*b[0]))]
    f,g=[[list(map(f32,row)) for row in frame] for frame in (first_frame,second_frame)]
    h=[[g[j][i] for j in range(3)] for i in range(3)]
    it=[dot([-x for x in g[3]],g[j]) for j in range(3)]
    basis=[[f32(f32(f32(h[0][j]*v[0])+f32(h[1][j]*v[1]))+f32(h[2][j]*v[2])) for j in range(3)] for v in f[:3]]
    translation=[f32(f32(f32(f32(h[0][j]*f[3][0])+it[j])+f32(h[1][j]*f[3][1]))+f32(h[2][j]*f[3][2])) for j in range(3)]
    def normal(v):
        x,y,z=map(f32,v[:3])
        return [f32(f32(f32(basis[1][j]*y)+f32(basis[0][j]*x))+f32(basis[2][j]*z)) for j in range(3)]
    def point(v):
        x,y,z=map(f32,v)
        return [f32(f32(f32(f32(basis[0][j]*x)+translation[j])+f32(basis[1][j]*y))+f32(basis[2][j]*z)) for j in range(3)]
    best=f32(-3.4028234663852886e38);result.update(distance=best,first=0xffffffff,second=0xffffffff)
    eps=f32(1e-6)
    for i,(v0,v1,p0,p1) in enumerate(first_shape['edges']):
        a,b=normal(first_shape['planes'][p0]),normal(first_shape['planes'][p1])
        first=point(first_shape['vertices'][v0]);end=point(first_shape['vertices'][v1])
        for j,(w0,w1,q0,q1) in enumerate(second_shape['edges']):
            c,d=[list(map(f32,second_shape['planes'][k][:3])) for k in (q0,q1)]
            second,other=[list(map(f32,second_shape['vertices'][k])) for k in (w0,w1)]
            edge=sub(second,other);length=f32(math.sqrt(dot(edge,edge)))
            if not length>0:raise ValueError('Nonzero second-edge length required')
            inv=f32(1./length);unit=[f32(x*inv) for x in edge]
            na,nb=[-x for x in a],[-x for x in b]
            n=cross(nb,na)
            bd,ad=dot(nb,unit),dot(na,unit);nc,nd=dot(n,c),dot(n,d)
            if not (f32(bd*nc)>eps and f32(nd*nc)<-eps and f32(ad*bd)<-eps):continue
            axis=cross(sub(first,end),edge);size=f32(math.sqrt(dot(axis,axis)))
            if size<f32(.001):continue
            axis=[f32(x/size) for x in axis]
            if dot([f32(x+y) for x,y in zip(a,b)],axis)<0:axis=[-x for x in axis]
            separation=f32(dot(axis,second)-dot(axis,first))
            if best<separation<0:
                best=separation;result.update(distance=best,first=i,second=j)
