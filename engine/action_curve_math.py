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
