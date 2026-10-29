"""Kind5 angular geometry; LINK_SOLVER.md, Composed angular-limit geometry."""
import math
from reference.central_impulse import f32
from .pose_constraint_limit import _vector
from .pose_ellipse import pose_ellipse_project,pose_ellipse_normal,EPSILON
from .pose_scalar_trig import scalar_sin_cos
from .pose_scalar_asin import pose_scalar_asin
from .pose_link_rotation import quaternion_basis


def pose_angular_limit_geometry(radius, angle, extent_x, extent_y, axis, rotation_axis):
    """Return four-lane correction axis and broadcast error, without row writes.

    Inputs retain SIMD lane gates. General path uses X scalar lanes. Existing
    dispatch-zero scalar trig is used; finite supported-domain inputs required.
    """
    radius,angle,ex,ey,axis,rotation_axis = map(
        _vector,(radius,angle,extent_x,extent_y,axis,rotation_axis))
    if all(abs(f32(x-y))<=EPSILON for x,y in zip(ex,ey)):
        return axis,[f32(x-r) for x,r in zip(ex,radius)]
    if all(r<EPSILON for r in radius[:3]):
        return axis,[0.]*4
    r=radius[0]
    if r==0:
        raise ValueError('Nonzero scalar radius required on general path')
    sine,cosine=scalar_sin_cos(angle[0])
    x,y=f32(cosine*r),f32(sine*r)
    a,b=ex[0],ey[0]
    if abs(a)>EPSILON and abs(b)>EPSILON:
        px,py=pose_ellipse_project(x,y,a,b)
        nx,ny=pose_ellipse_normal(a,b,px,py)
    else:
        def clamp(v,bound):
            low=-bound if f32(-bound-v)>=0 else v
            return bound if f32(bound-low)<0 else low
        px,py=clamp(x,a),clamp(y,b)
        nx,ny=f32(x-px),f32(y-py)
        squared=f32(f32(ny*ny)+f32(nx*nx))
        if abs(squared)<=EPSILON:
            return axis,[0.]*4
        reciprocal=f32(1./f32(math.sqrt(squared)))
        nx,ny=f32(nx*reciprocal),f32(ny*reciprocal)
    reciprocal=f32(1./r)
    turn=f32(f32(f32(reciprocal*y)*nx)-f32(f32(reciprocal*x)*ny))
    low=-1. if f32(-1.-turn)>=0 else turn
    turn=1. if f32(1.-low)<0 else low
    correction=pose_scalar_asin(turn)
    sine,cosine=scalar_sin_cos(f32(correction*.5))
    basis=quaternion_basis([f32(v*sine) for v in rotation_axis[:3]]+[cosine])
    rotated=[f32(f32(f32(basis[0][j]*axis[0])+f32(basis[1][j]*axis[1]))+
                 f32(basis[2][j]*axis[2])) for j in range(3)]+[0.]
    error=f32(f32(f32(py-y)*ny)+f32(f32(px-x)*nx))
    return rotated,[error]*4
