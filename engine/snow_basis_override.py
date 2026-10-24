"""Explicit-vector branch of the live-identified basis callback.

Evidence: CENTRAL_IMPULSE.md, Explicit-vector basis override. This branch is not
the complete callback. Caller establishes branch reachability and supplies the
post-prepass vectors plus approximate reciprocal-square-root seeds.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four


def normalize_override_triplet(vectors, reciprocal_sqrt_seed):
    """Normalize XYZ lengths and scale all lanes; output source order [1,2,0].

    Inputs follow receiver slots 220/230/240. No Gram-Schmidt, cross products or
    W repair. Zero/nonfinite norms are rejected by authored API policy, not a
    recovered native fallback. Native evaluation order is 0,1,2.
    """
    if len(vectors) != 3:
        raise ValueError('Three supplied vectors required')
    normalized=[]
    for vector in vectors:
        v=four(vector)
        squares=[f32(x*x) for x in v[:3]]
        n=f32(squares[0]+f32(squares[1]+squares[2]))
        if not math.isfinite(n) or n <= 0:
            raise ValueError('Finite positive XYZ norm required')
        seed=f32(reciprocal_sqrt_seed(n))
        if not math.isfinite(seed):
            raise ValueError('Finite reciprocal sqrt seed required')
        refinement=f32(f32(3.0-f32(f32(seed*n)*seed))*f32(.5*seed))
        normalized.append([f32(refinement*x) for x in v])
    return [normalized[1],normalized[2],normalized[0]]
