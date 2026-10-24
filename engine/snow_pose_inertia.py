"""Recovered producer of the three spring mass-like frame coefficients.

Evidence: CENTRAL_IMPULSE.md, Composite pose inertia-like producer.
Base-field physical provenance remains external; no tensor rotation is inferred.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four


def composite_pose_coefficients(primary_base, secondary_base, primary_position,
                                secondary_position, total_mass, secondary_mass,
                                paired):
    """Return published coefficients; paired path uses Y/Z/X distance sums.

    Base arrays have three components in native storage order. Nonpaired path
    copies primary_base without requiring secondary inputs or mass services.
    """
    if type(paired) is not bool:raise ValueError('Explicit paired-path decision required')
    if len(primary_base)!=3:raise ValueError('Three base components required')
    a=list(map(f32,primary_base))
    if not paired:return a
    if len(secondary_base)!=3:raise ValueError('Three secondary base components required')
    b=list(map(f32,secondary_base));p=four(primary_position);q=four(secondary_position)
    total,secondary=f32(total_mass),f32(secondary_mass)
    if not all(math.isfinite(x) for x in a+b+p+q+[total,secondary]) or total<=0:
        raise ValueError('Finite inputs and positive total mass required')
    primary=f32(total-secondary)
    center=[f32(f32(f32(secondary*y)+f32(primary*x))/total) for x,y in zip(p,q)]
    da=[f32(c-x) for c,x in zip(center,p)]
    db=[f32(c-y) for c,y in zip(center,q)]
    def terms(d):
        x,y,z=[f32(v*v) for v in d[:3]]
        return [f32(z+x),f32(y+x),f32(y+z)]
    ta,tb=terms(da),terms(db)
    return [f32(f32(f32(x+y)+f32(v*secondary))+f32(u*primary))
            for x,y,u,v in zip(a,b,ta,tb)]
