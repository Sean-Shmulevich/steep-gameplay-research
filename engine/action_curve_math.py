"""Independent scalar math for the curve solver's finite input domain.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Reconstructed curve acos.
Preserves scalar SSE float32 and float64 operation ordering. Floating-point
exception flags and CRT error handling are not part of this numerical API.
"""
import math
import struct
from .action_axis_ramp import f32


def curve_acos(value):
    """Recovered acos return value for finite float32 input in [-1, 1]."""
    x = f32(value)
    if not -1 <= x <= 1:
        raise ValueError('curve acos requires input in [-1, 1]')
    ax = abs(x)
    if ax < 2 ** -26:
        return f32(1.5707963705062866)
    if x == 1:
        return 0.
    if x == -1:
        return f32(3.1415927410125732)
    outer = ax >= .5
    z = f32(f32(1 - ax) * .5) if outer else f32(ax * ax)
    s = f32(math.sqrt(z)) if outer else 0.
    p = f32(-0.013381929136812687 - f32(z * 0.003961374517530203))
    p = f32(f32(p * z) - 0.05652986839413643)
    p = f32(f32(p * z) + 0.18416160345077515)
    p = f32(p * z)
    q = f32(1.1049696207046509 - f32(z * 0.8364112973213196))
    ratio = f32(p / q)
    if not outer:
        correction = 6.123233995736766e-17 - f32(ratio * x)
        return f32(1.5707963267948966 - (x - correction))
    if x < 0:
        correction = (f32(ratio * s) - 6.123233995736766e-17) + s
        return f32(3.141592653589793 - (correction + correction))
    bits = struct.unpack('<I', struct.pack('<f', s))[0] & 0xffff0000
    truncated = struct.unpack('<f', struct.pack('<I', bits))[0]
    correction = f32(f32(z - f32(truncated * truncated)) / f32(truncated + s))
    value = f32(f32(s + s) * ratio)
    value = f32(value + f32(correction + correction))
    return f32(value + f32(truncated * 2))


def curve_cos(value):
    """Recovered dispatch-zero cosine for finite float32 angles |x| <= 6.

    This covers all finite angles constructed by the cubic curve solver.
    General large-angle reduction and alternate CPU dispatch are excluded.
    """
    x = abs(f32(value))
    if x > 6:
        raise ValueError('curve cosine requires angle magnitude at most 6 radians')
    quadrant = 0
    short = False
    exponent = 0
    if x > 0.7853981633974483:
        quadrant = int(x * 0.6366197723675814 + .5)
        high = x - 1.5707963267341256 * quadrant
        low = 6.077100506506192e-11 * quadrant
        reduced = high - low
        def exponent_bits(v):
            return (struct.unpack('<Q', struct.pack('<d', v))[0] >> 52) & 0x7ff
        exponent = exponent_bits(reduced)
        if exponent_bits(x) - exponent > 15:
            part = 6.077100506303966e-11 * quadrant
            tail = 2.0222662487959506e-21 * quadrant
            previous = high
            high = high - part
            correction = (previous - high) - part
            low = tail - correction
            reduced = high - low
        x = reduced
        short = exponent < 0x3f2
    z = x * x
    if short:
        if exponent <= 0x3de:
            result = x if quadrant & 1 else 1.
        elif quadrant & 1:
            result = x - ((0.16666666666666666 * x) * z)
        else:
            result = 1. - z * .5
    elif quadrant & 1:
        z2 = z * z
        a = 2.7557319223985893e-06 * z
        b = 0.008333333333333333 * z
        a = (a + -0.0001984126984126984) * z2
        b = b + -0.16666666666666666
        result = x + ((a + b) * (x * z))
    else:
        z2 = z * z
        a = (-2.755731922398589e-07 * z + 2.4801587301587298e-05) * z2
        b = -0.0013888888888888887 * z + 0.041666666666666664
        result = (-.5 * z + 1.) + ((a + b) * z2)
    if (quadrant + 1) & 2:
        result = 0. - result
    return f32(result)
