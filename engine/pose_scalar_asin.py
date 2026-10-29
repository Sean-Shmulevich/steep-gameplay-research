"""Finite asinf arithmetic; LINK_SOLVER.md, Quaternion angular-drive response."""
import math
import struct
from reference.central_impulse import f32


def pose_scalar_asin(value):
    """Float32 arcsine on [-1,1]; CRT floating-point status effects excluded."""
    x = f32(value)
    if not math.isfinite(x) or abs(x)>1:
        raise ValueError('Finite arcsine input in [-1,1] required')
    a = abs(x)
    if a < 2**-14:
        return x
    if a == 1:
        return math.copysign(f32(math.pi/2),x)
    large = a >= .5
    t = f32(f32(1.-a)*.5) if large else f32(a*a)
    s = f32(math.sqrt(t)) if large else a
    p = f32(f32(-0.013381929136812687)-f32(t*f32(0.003961374517530203)))
    p = f32(f32(p*t)-f32(0.05652986839413643))
    p = f32(f32(p*t)+f32(0.18416160345077515))
    p = f32(p*t)
    q = f32(f32(1.1049696207046509)-f32(t*f32(0.8364112973213196)))
    r = f32(p/q)
    if large:
        bits = struct.unpack('<I',struct.pack('<f',s))[0]&0xffff0000
        hi = struct.unpack('<f',struct.pack('<I',bits))[0]
        correction = f32(f32(t-f32(hi*hi))/f32(hi+s))
        twice_s, twice_hi = f32(s*2.), f32(hi*2.)
        residual = f32(f32(twice_s*r)-f32(f32(7.549789415861596e-08)-f32(correction+correction)))
        quarter = f32(0.7853981256484985)
        residual = f32(residual-f32(quarter-twice_hi))
        result = f32(quarter-residual)
    else:
        result = f32(f32(r*a)+a)
    return -result if x<0 else result
