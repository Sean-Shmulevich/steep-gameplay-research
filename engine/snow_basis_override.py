"""Explicit-vector and direction-alignment branches of the identified callback.

Evidence: CENTRAL_IMPULSE.md, Explicit-vector and Direction-aligned basis override.
These branches are not
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
    normalized = [_normalize(vector, reciprocal_sqrt_seed) for vector in vectors]
    return [normalized[1], normalized[2], normalized[0]]


def _normalize(vector, reciprocal_sqrt_seed):
    v = four(vector)
    squares = [f32(x*x) for x in v[:3]]
    n = f32(squares[0] + f32(squares[1] + squares[2]))
    if not math.isfinite(n) or n <= 0:
        raise ValueError('Finite positive XYZ norm required')
    seed = f32(reciprocal_sqrt_seed(n))
    if not math.isfinite(seed):
        raise ValueError('Finite reciprocal sqrt seed required')
    refinement = f32(f32(3.0-f32(f32(seed*n)*seed))*f32(.5*seed))
    return [f32(refinement*x) for x in v]


def _cross(a, b):
    # Preserve the packed multiply/subtract/shuffle order, including W.
    order = [2, 0, 1, 3]
    temp = [f32(f32(a[j]*b[i])-f32(b[j]*a[i]))
            for i, j in enumerate(order)]
    return [temp[j] for j in order]


def align_override_basis(initial_basis, direction, reciprocal_sqrt_seed):
    """Rebuild axes 2 then 0 while preserving post-prepass axis 1.

    Evidence: CENTRAL_IMPULSE.md, Direction-aligned basis override.
    Caller establishes branch reachability. Axis 1 is not normalized; inputs
    and output use four lanes. Singular crosses raise by authored API policy,
    with no claim that the native instructions provide a degeneracy fallback.
    """
    if len(initial_basis) != 3:
        raise ValueError('Three basis vectors required')
    axis1 = four(initial_basis[1])
    axis2 = _normalize(_cross(four(direction), axis1), reciprocal_sqrt_seed)
    axis0 = _normalize(_cross(axis1, axis2), reciprocal_sqrt_seed)
    return [axis0, axis1, axis2]
