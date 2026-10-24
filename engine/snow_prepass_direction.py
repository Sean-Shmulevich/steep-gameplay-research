"""Recovered slope-angle rotation and low-depth direction correction.

Evidence: CENTRAL_IMPULSE.md, Slope-driven auxiliary direction.
Resolved vectors, gain and numerical services remain explicit inputs.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_axis_rotation import rotate_basis_axis


def slope_projection_direction(normal, rotation_axis, selected_direction,
                               gain, depth, slope_angle, sine, cosine,
                               reciprocal_sqrt_seed):
    """Construct the auxiliary projection direction, not the completed basis.

    Finite nonsingular domain; near-up bypass does not evaluate supplied math.
    Low-depth correction uses four-lane dots and four-lane normalization.
    """
    normal=four(normal)
    if not all(math.isfinite(x) for x in normal):
        raise ValueError('Finite normal required')
    if normal[2] >= f32(.999):
        return {'direction':[0.,0.,1.,0.],'branch':'up'}
    product=f32(f32(slope_angle(normal[2]))*f32(gain))
    direction=rotate_basis_axis([0.,0.,1.,0.],rotation_axis,-product,
                                f32(1e-5),sine,cosine)
    depth=f32(depth)
    if not math.isfinite(depth):raise ValueError('Finite depth required')
    if depth > f32(.03):
        return {'direction':direction,'branch':'rotated'}
    selected=four(selected_direction)
    def dot4(a,b):
        p=[f32(x*y) for x,y in zip(a,b)]
        return f32(f32(p[1]+p[3])+f32(p[0]+p[2]))
    d=dot4(selected,normal)
    tangent=[f32(x-f32(d*n)) for x,n in zip(selected,normal)]
    d=dot4(tangent,direction)
    corrected=[f32(x-f32(d*t)) for x,t in zip(direction,tangent)]
    n=dot4(corrected,corrected)
    if not math.isfinite(n) or n<=0:raise ValueError('Finite positive four-lane norm required')
    seed=f32(reciprocal_sqrt_seed(n))
    scale=f32(f32(3.-f32(f32(seed*n)*seed))*f32(seed*.5))
    result=[f32(x*scale) for x in corrected]
    if not all(math.isfinite(x) for x in result):raise ValueError('Finite direction required')
    return {'direction':result,'branch':'corrected'}
