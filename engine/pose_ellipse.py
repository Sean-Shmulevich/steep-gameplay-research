"""Limit geometry helpers; LINK_SOLVER.md, Elliptical limit projection."""
import math
from reference.central_impulse import f32

EPSILON = f32(1e-4)


def _inputs(*values):
    out = [f32(v) for v in values]
    if not all(math.isfinite(v) for v in out):
        raise ValueError('Finite ellipse inputs required')
    return out


def pose_ellipse_project(x, y, radius_x, radius_y):
    """Recovered boundary projection, including interior and near-axis branches.

    Positive radii and finite nondegenerate intermediate arithmetic required.
    The iteration-cap exit deliberately uses the last evaluated denominators.
    """
    x,y,a,b = _inputs(x,y,radius_x,radius_y)
    if a<=0 or b<=0:
        raise ValueError('Positive ellipse radii required')
    aa,bb,xx,yy = f32(a*a),f32(b*b),f32(x*x),f32(y*y)
    if abs(x)<=EPSILON:
        if a<b and abs(y)<f32(b-f32(f32(1./b)*aa)):
            py=f32(f32(bb*y)/f32(bb-aa))
            t=f32(py*f32(1./b))
            px=f32(f32(math.sqrt(abs(f32(1.-f32(t*t)))))*a)
            return [-px if x<0 else px,py]
        return [0.,-b if y<0 else b]
    if abs(y)<=EPSILON:
        if b<a and abs(x)<f32(a-f32(f32(1./a)*bb)):
            px=f32(f32(aa*x)/f32(aa-bb))
            t=f32(px*f32(1./a))
            py=f32(f32(math.sqrt(abs(f32(1.-f32(t*t)))))*b)
            return [px,-py if y<0 else py]
        return [-a if x<0 else a,0.]
    ia,ib = f32(1./a),f32(1./b)
    tx,ty = f32(ia*x),f32(ib*y)
    inside = f32(f32(ty*ty)+f32(tx*tx))<1.
    t = 0. if inside else f32(f32(math.sqrt(f32(yy+xx)))*(b if f32(b-a)>=0 else a))
    ax,by = f32(xx*aa),f32(yy*bb)
    for _ in range(19):
        u,v = f32(t+bb),f32(t+aa)
        uu,vv = f32(u*u),f32(v*v)
        residual = f32(f32(f32(uu*vv)-f32(uu*ax))-f32(vv*by))
        if abs(residual)<EPSILON:
            break
        derivative = f32(f32(f32(f32(f32(u*v)*f32(u+v))-f32(u*ax))-f32(v*by))*2.)
        if derivative==0:
            raise ValueError('Degenerate ellipse iteration derivative')
        t=f32(t-f32(residual/derivative))
    # u/v are not recomputed after the final bounded Newton update.
    if abs(v)>abs(u):
        px=f32(f32(aa*x)/v)
        h=f32(px*ia);remaining=f32(1.-f32(h*h))
        if -remaining>=0:remaining=0.
        py=f32(f32(math.sqrt(remaining))*b)
        return [px,-py if f32(u*y)<0 else py]
    py=f32(f32(bb*y)/u)
    h=f32(py*ib);remaining=f32(1.-f32(h*h))
    if -remaining>=0:remaining=0.
    px=f32(f32(math.sqrt(remaining))*a)
    return [-px if f32(v*x)<0 else px,py]


def pose_ellipse_normal(radius_x, radius_y, x, y):
    """Normalize (x, radius_x squared times y / radius_y squared)."""
    a,b,x,y = _inputs(radius_x,radius_y,x,y)
    if b==0:
        raise ValueError('Nonzero second radius required')
    ny=f32(f32(f32(a*a)*y)/f32(b*b))
    length=f32(math.sqrt(f32(f32(x*x)+f32(ny*ny))))
    if not length or not math.isfinite(length):
        raise ValueError('Finite nonzero ellipse normal required')
    reciprocal=f32(1./length)
    return [f32(reciprocal*x),f32(reciprocal*ny)]
