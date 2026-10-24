"""Snow-state ID-84 vector branch; CENTRAL_IMPULSE.md, Snow-state vector output.

Finite XYZ inputs with implicit fourth lane zero. Caller supplies the native
RSQRT estimate for exact instruction-order comparisons. No live state selection.
"""
import math
import struct


def f32(value):
    value = struct.unpack('<f',struct.pack('<f',value))[0]
    if not math.isfinite(value):
        raise ValueError('finite float32 required')
    return value


def snow_vector(direction, normal, gain, reciprocal_sqrt_seed):
    """Return XYZ output; seed is called with float32 squared cross length.

    No assumed unit normal, native allocator, state dispatcher or handle lookup.
    Finite-input validation and exceptions are authored restrictions.
    """
    if len(direction)!=3 or len(normal)!=3:
        raise ValueError('XYZ vectors required')
    u = list(map(f32,direction));n = list(map(f32,normal));gain=f32(gain)
    def cross(a,b):
        return [f32(f32(a[j]*b[k])-f32(a[k]*b[j])) for j,k in [(1,2),(2,0),(0,1)]]
    c = cross(n,u)
    if all(abs(v)<=f32(1e-5) for v in c):
        return [f32(gain*v) for v in u]
    squared=[f32(v*v) for v in c]
    length2=f32(f32(squared[1]+0.0)+f32(squared[0]+squared[2]))
    seed=f32(reciprocal_sqrt_seed(length2))
    refined=f32(f32(3.0-f32(f32(seed*length2)*seed))*f32(0.5*seed))
    unit=[f32(refined*v) for v in c]
    return [f32(gain*v) for v in cross(unit,n)]
