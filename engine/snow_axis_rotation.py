"""Recovered finite axis-rotation helper with explicit trigonometric services.

Evidence: CENTRAL_IMPULSE.md, Shared basis axis rotation. Services receive the
float32 half angle in radians. Supplying platform math is an approximation,
not a claim of native trigonometric return-bit equivalence.
"""
import math
from reference.central_impulse import f32
from .snow_post_pending import four
from .snow_basis_override import _cross


def rotate_basis_axis(vector, axis, angle, axis_threshold, sine, cosine):
    """Return four lanes; finite nonzero axis only, threshold comparison inclusive.

    Native evaluates both trig calls even when the threshold selects identity.
    This API rejects zero/nonfinite lengths instead of emulating FP exceptions.
    """
    v, a = four(vector), four(axis)
    angle, threshold = f32(angle), f32(axis_threshold)
    if not all(math.isfinite(x) for x in (*v, *a, angle, threshold)):
        raise ValueError('Finite rotation inputs required')
    squares = [f32(x*x) for x in a[:3]]
    length = f32(math.sqrt(f32(squares[0]+f32(squares[1]+squares[2]))))
    if not math.isfinite(length) or length <= 0:
        raise ValueError('Finite positive axis length required')
    half = f32(angle*.5)
    s = f32(sine(half))
    scale = f32(s/length)
    q = [f32(scale*x) for x in a[:3]] + [f32(cosine(half))]
    if not all(math.isfinite(x) for x in q):
        raise ValueError('Finite trigonometric results required')
    if length <= threshold:
        q = [0.,0.,0.,1.]
    products = [f32(v[i]*q[i]) for i in range(3)]
    dot = f32(products[0]+f32(products[1]+products[2]))
    cross = _cross(q, v)
    wterm = f32(f32(q[3]*q[3])-.5)
    return [f32(f32(f32(f32(dot*q[i])+f32(cross[i]*q[3]))+
                       f32(wterm*v[i])) * (2. if i < 3 else 0.))
            for i in range(4)]
