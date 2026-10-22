"""Recovered ordered polynomial roots with explicit runtime-math dependency.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Ordered curve roots.
Finite coefficients and finite intermediates only. Each supplied math function
must implement the desired float32 runtime behavior; no CRT equivalence implied.
"""
from .action_axis_ramp import f32


def ordered_curve_roots(c0, c1, c2, c3, *, sqrt, acos, cos, power):
    """Return roots in native output order, not sorted order.

    Coefficients ascend in power. Degenerate cubic falls through to quadratic
    then linear. Math callbacks receive float32 arguments and return scalars.
    Non-finite intermediate behavior is outside this contract.
    """
    d, c, b, a = map(f32, (c0, c1, c2, c3))
    if a == 0:
        if b == 0:
            return () if c == 0 else (-f32(d / c),)
        half = f32(c / f32(b + b))
        disc = f32(f32(half * half) - f32(d / b))
        # These comparisons use double constants, not rounded float32 bounds.
        if disc < -0.0001:
            return ()
        if disc < 0.0001:
            return (-half,)
        root = f32(sqrt(disc))
        return (f32(root - half), f32(-root - half))

    b = f32(b / a)
    c = f32(c / a)
    d27 = f32(f32(d / a) * 27)
    q = f32(f32(f32(b * b) - f32(c * 3)) / 9)
    r = f32(f32(f32(f32(f32(b + b) * b) * b) - f32(f32(b * 9) * c)) + d27)
    r = f32(r / 54)
    q3 = f32(f32(q * q) * q)
    disc = f32(f32(r * r) - q3)
    if disc <= 0:
        denominator = f32(sqrt(q3))
        if denominator == 0:
            raise ValueError('zero divisor in cubic trigonometric path is outside finite-intermediate contract')
        ratio = f32(r / denominator)
        angle = f32(acos(max(-1., min(1., ratio))))
        scale = f32(f32(sqrt(q)) * -2)
        shift = f32(b / 3)
        angles = (f32(angle / 3), f32(f32(angle + f32(6.2831854820251465)) / 3),
                  f32(f32(angle + f32(12.566370964050293)) / 3))
        return tuple(f32(f32(f32(cos(t)) * scale) - shift) for t in angles)
    root = f32(sqrt(disc))
    u = f32(power(f32(abs(r) + root), f32(1 / 3)))
    value = f32(f32(q / u) + u)
    sign = 1. if r < 0 else -1.
    return (f32(f32(value * sign) - f32(b / 3)),)
