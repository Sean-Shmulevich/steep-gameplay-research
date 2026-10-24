"""Recovered prepass direction rejection and finite fallback normalization.

Evidence: CENTRAL_IMPULSE.md, Initial prepass direction projection.
The supplied projection direction is not normalized by this fragment.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_basis_override import _normalize


def project_prepass_direction(selected_direction, projection_direction,
                              fallback_axis, reciprocal_sqrt_seed):
    """Return normalized first axis and unchanged auxiliary direction.

    Caller supplies the previously selected vectors. Degenerate final XYZ norms
    raise by authored policy; native instructions have no second fallback here.
    """
    selected, direction = four(selected_direction), four(projection_direction)
    if not all(math.isfinite(x) for x in selected+direction):
        raise ValueError('Finite projection inputs required')
    def reject(vector):
        products=[f32(vector[i]*direction[i]) for i in range(3)]
        dot=f32(products[0]+f32(products[1]+products[2]))
        return [f32(vector[i]-f32(dot*direction[i])) for i in range(4)]
    projected=reject(selected)
    used_fallback=all(abs(x)<=f32(1e-5) for x in projected)
    if used_fallback:
        fallback=four(fallback_axis)
        if not all(math.isfinite(x) for x in fallback):
            raise ValueError('Finite fallback axis required')
        sign=0. if fallback[2]==0 else (1. if fallback[2]>0 else -1.)
        projected=reject([f32(sign*x) for x in fallback])
    return {'axis0':_normalize(projected,reciprocal_sqrt_seed),
            'auxiliary_direction':direction,'used_fallback':used_fallback}
