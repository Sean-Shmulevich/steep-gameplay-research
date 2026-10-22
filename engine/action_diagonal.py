"""Recovered finite-input diagonal correction stage for action vectors.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Live chain and diagonal correction.
Original stage operates on SIMD values; this adapter rejects nonfinite input.
"""
import math
import struct


def _f(x):
    return struct.unpack('<f',struct.pack('<f',x))[0]

EPSILON=_f(1e-5)
DIAGONAL_SCALE=_f(0.7071067690849304)


def correct_diagonal(vector):
    """Preserve Z/W. Scale XY to retain its maximum-axis magnitude.

    Near-equal magnitudes use the original constant fast path. All four lanes
    participate in the near-zero early return. Preserve float32 operation order.
    """
    if not isinstance(vector,(list,tuple)) or len(vector)!=4:
        raise ValueError('four finite float32 lanes required')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in vector):
        raise ValueError('four finite float32 lanes required')
    try:v=[_f(x) for x in vector]
    except (OverflowError,struct.error) as exc:raise ValueError('float32 overflow') from exc
    if not all(math.isfinite(x) for x in v):raise ValueError('float32 overflow')
    if all(abs(x)<=EPSILON for x in v):return v
    x,y,z,w=v
    if abs(_f(abs(x)-abs(y)))<=EPSILON:
        scale=DIAGONAL_SCALE
    else:
        large,small=(x,y) if abs(x)>abs(y) else (y,x)
        ratio=_f(_f(1.0/large)*small)
        squared=_f(1.0+_f(ratio*ratio))
        scale=_f(1.0/_f(math.sqrt(squared)))
    return [_f(x*scale),_f(y*scale),z,w]
