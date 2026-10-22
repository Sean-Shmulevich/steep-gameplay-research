"""Work-buffer quaternion blend; not the graph's polynomial blend helper.

Evidence: CENTRAL_IMPULSE.md, Work rotation interpolation branches.
RSQRT, acos and sin are explicit numerical services. Inputs must be finite.
"""
import math
from reference.snow import f32


def blend_work_rotation(saved, current, alpha, reciprocal_sqrt, acos, sin):
    a,b=tuple(map(f32,saved)),tuple(map(f32,current));t=f32(alpha)
    if len(a)!=4 or len(b)!=4 or not all(math.isfinite(x) for x in a+b+(t,)):
        raise ValueError('finite four-lane rotations and alpha required')
    products=tuple(f32(x*y) for x,y in zip(a,b))
    dot=f32(f32(products[0]+products[2])+f32(products[1]+products[3]))
    if abs(f32(abs(dot)-1.)) <= f32(2**-23):
        return dict(rotation=a,branch='keep_saved',dot=dot)
    branch='normalized_linear'
    left,right=f32(1.-t),t
    if dot < f32(.9893559813499451):
        branch='spherical'
        if not -1. < dot < 1.:
            return dict(rotation=b,branch='spherical_out_of_range_current',dot=dot)
        angle=f32(acos(abs(dot)))
        left=f32(sin(f32(f32(1.-t)*angle)))
        right=f32(sin(f32(t*angle)))
        if dot < 0:right=-right
        if abs(angle) <= f32(1e-5):
            return dict(rotation=b,branch='spherical_tiny_angle_current',dot=dot)
        inverse=f32(1./f32(sin(angle)))
        right=f32(right*inverse);left=f32(left*inverse)
    q=tuple(f32(f32(left*x)+f32(right*y)) for x,y in zip(a,b))
    sq=tuple(f32(x*x) for x in q)
    n=f32(f32(sq[0]+sq[2])+f32(sq[1]+sq[3]))
    if n<=0 or not math.isfinite(n):
        raise ValueError('positive finite norm required by inspection adapter')
    seed=f32(reciprocal_sqrt(n))
    factor=f32(f32(.5*seed)*f32(3.-f32(f32(seed*n)*seed)))
    return dict(rotation=tuple(f32(x*factor) for x in q),branch=branch,dot=dot)
