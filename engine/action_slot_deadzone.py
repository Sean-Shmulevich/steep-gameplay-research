"""Recovered finite four-lane radial shaping after initial-slot packet mapping.

Evidence: INPUT_UPDATE_ORDER.md, Analog radial deadzone and magnitude limit.
Original RSQRT seed is caller-injectable; default reciprocal sqrt is a substitute.
"""
import math
import struct
from engine.action_cache_exchange import CACHE_SPAN

# Constructor default, not a claim about active gameplay configuration.
DEFAULT_DEADZONE_BITS = bytes.fromhex("9a99993e")


def set_cache_deadzone_bits(snapshot, bits):
    """Detached raw setter. Preserve all float32 encodings; no value clamping.

    Unlike the finite shaping kernel, the native setter accepts any four bytes.
    Does not propagate to record caches or modify a live game.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) != CACHE_SPAN:
        raise ValueError("exact 0x818-byte snapshot required")
    if not isinstance(bits, bytes) or len(bits) != 4:
        raise ValueError("four float32 encoding bytes required")
    result = bytearray(snapshot)
    result[0x210:0x214] = bits
    return bytes(result)


def _f(value):
    try:result=struct.unpack('<f',struct.pack('<f',value))[0]
    except (OverflowError,struct.error) as exc:raise ValueError('float32 overflow') from exc
    if not math.isfinite(result):raise ValueError('finite float32 required')
    return result


def shape_slot_vector(vector, deadzone, *, rsqrt_estimate=None):
    """Apply native branch/float32 order to four finite dimensionless lanes.

    Deadzone is explicit, not inferred or clamped. Native normalization uses
    RSQRT followed by a Newton refinement. Supply its seed for bit comparisons;
    default uses rounded 1/sqrt and does not promise original SIMD bit identity.
    Nonfinite inputs/intermediates and floating-point traps are outside scope.
    """
    if len(vector)!=4:raise ValueError('four lanes required')
    v=tuple(_f(x) for x in vector);d=_f(deadzone)
    squares=tuple(_f(x*x) for x in v)
    q=_f(_f(squares[0]+squares[2])+_f(squares[1]+squares[3]))
    if _f(d*d)>q:return (0.0,)*4
    if q>1.0:
        seed=_f(rsqrt_estimate(q) if rsqrt_estimate is not None else 1/math.sqrt(q))
        factor=_f(_f(3.0-_f(_f(seed*q)*seed))*_f(0.5*seed))
        return tuple(_f(factor*x) for x in v)
    if d>0.0 and 1.0>d:
        length=_f(math.sqrt(q))
        if length==0.0:
            raise ValueError('underflow produced zero divisor outside finite model')
        scale=_f(_f(_f(length-d)/_f(1.0-d))/length)
        return tuple(_f(scale*x) for x in v)
    return v


def shape_slot_cache(snapshot, *, rsqrt_estimate=None):
    """Shape both cached vectors using float32 deadzone at +0x210."""
    if not isinstance(snapshot,bytes) or len(snapshot)!=CACHE_SPAN:
        raise ValueError('exact 0x818-byte snapshot required')
    result=bytearray(snapshot);deadzone=struct.unpack_from('<f',snapshot,0x210)[0]
    for offset in (0x1f0,0x200):
        vector=struct.unpack_from('<4f',snapshot,offset)
        struct.pack_into('<4f',result,offset,*shape_slot_vector(vector,deadzone,rsqrt_estimate=rsqrt_estimate))
    return bytes(result)
