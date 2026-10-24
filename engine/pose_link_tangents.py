"""Recovered point-motion tangent selection for metadata-clear/single links.

Evidence: LINK_SOLVER.md, Link point-motion tangent basis.
"""
import math
from reference.central_impulse import f32


def link_tangent_basis(basis, point, center, motion1a0, motion1ac, normal):
    """Return two directions from explicit first-body fields and a payload row.

    The motion field roles follow the recovered arithmetic; units are unresolved.
    Normal is not normalized. Finite, nondegenerate inputs are required. Each
    basis row is multiplied by the corresponding local coordinate.
    """
    def vector(v):
        if len(v)!=3:raise ValueError('Three components required')
        r=tuple(f32(x) for x in v)
        if not all(math.isfinite(x) for x in r):raise ValueError('Finite components required')
        return r
    if len(basis)!=3:raise ValueError('Three basis rows required')
    rows=[vector(v) for v in basis]
    p,c,v,w,n=map(vector,(point,center,motion1a0,motion1ac,normal))
    local=[f32(p[i]-c[i]) for i in range(3)]
    r=[f32(f32(rows[2][j]*local[2])+f32(f32(local[0]*rows[0][j])+f32(rows[1][j]*local[1]))) for j in range(3)]
    def cross(a,b):
        return [f32(f32(a[(i+1)%3]*b[(i+2)%3])-f32(a[(i+2)%3]*b[(i+1)%3])) for i in range(3)]
    spin=cross(w,r)
    opposite=[-f32(spin[i]+v[i]) for i in range(3)]
    def dot(a,b):
        products=[f32(a[i]*b[i]) for i in range(3)]
        return f32(f32(products[0]+products[1])+f32(products[2]+0.0))
    projection=dot(opposite,n)
    tangent=[f32(opposite[i]-f32(projection*n[i])) for i in range(3)]
    fallback=f32(dot(tangent,tangent)-f32(1e-6))<0
    if fallback:
        x,y,z=n;ax,ay,az=map(abs,n)
        if f32(min(ax,ay)-az)<0:
            tangent=[z,0.0,-x] if f32(ay-ax)<0 else [0.0,z,-y]
        else:
            tangent=[y,-x,0.0]
    length=f32(math.sqrt(dot(tangent,tangent)))
    if length==0 or not math.isfinite(length):raise ValueError('Finite nonzero tangent length required')
    inverse=f32(1.0/length)
    first=[f32(x*inverse) for x in tangent]
    lane3=0.0 if fallback else f32(-0.0-f32(projection*0.0))
    return dict(first=first,second=cross(n,first),fallback=fallback,
                first_lane3=f32(lane3*inverse),opposite_motion_projection=projection)
