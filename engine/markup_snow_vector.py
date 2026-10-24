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


def branch3_gain_bits(state, read_payload_field):
    """Decode RVA 0x519640's state-to-field choice, returning raw float bits.

    The caller resolves the active global payload. Unrecognized states return
    positive zero without reading a payload field. State numbers are unnamed.
    """
    if type(state) is not int or not 0 <= state <= 0xffffffff:
        raise ValueError('uint32 state required')
    offset = {0:0x60,2:0x5c,5:0x5c,9:0x1a8}.get(state)
    if offset is None:
        return 0
    bits = read_payload_field(offset)
    if type(bits) is not int or not 0 <= bits <= 0xffffffff:
        raise ValueError('uint32 float bits required')
    return bits


def branch3_vector(current, normal, entity_direction, gain, *, direct_direction,
                   reverse_fallback, reciprocal_sqrt_seed):
    """RVA 0x516cb0 for finite XYZ inputs, implicit zero fourth lanes.

    Preserves the missing cross-degeneracy guard: a parallel high-magnitude
    vector may produce NaNs. Seed provider must model RSQRT(0) if that occurs.
    Booleans are resolved low-byte predicates supplied by the caller.
    """
    if any(len(v)!=3 for v in (current,normal,entity_direction)):
        raise ValueError('XYZ vectors required')
    if type(direct_direction) is not bool or type(reverse_fallback) is not bool:
        raise ValueError('resolved boolean gates required')
    v,n,d = [list(map(f32,x)) for x in (current,normal,entity_direction)]
    gain=f32(gain)
    def rounded(x):
        try:return struct.unpack('<f',struct.pack('<f',x))[0]
        except OverflowError:return math.copysign(math.inf,x)
    def cross(a,b):
        return [rounded(rounded(a[j]*b[k])-rounded(a[k]*b[j])) for j,k in [(1,2),(2,0),(0,1)]]
    def length2(a):
        squares=[rounded(x*x) for x in a]
        return rounded(rounded(squares[1]+0.0)+rounded(squares[0]+squares[2]))
    if direct_direction:
        direction=d
    elif rounded(math.sqrt(length2(v))) <= f32(0.01):
        direction=[-x for x in d] if reverse_fallback else d
    else:
        c=cross(n,v);squared=length2(c)
        seed=rounded(reciprocal_sqrt_seed(squared))
        reciprocal=rounded(rounded(3.0-rounded(rounded(seed*squared)*seed))*rounded(0.5*seed))
        direction=cross([rounded(reciprocal*x) for x in c],n)
    return [rounded(gain*x) for x in direction]
