"""Vector exponential lane arithmetic for the cooker domain [-10, 0].

See CENTRAL_IMPULSE.md, 'Decay exponential lanes'. Tables are independently
computed from powers of two, not copied payloads. CPU path is caller-selected.
"""
import struct
from reference.central_impulse import f32


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def from_bits(value):
    return struct.unpack('<f', struct.pack('<I', value & 0xffffffff))[0]


MANTISSAS = tuple(bits(f32(2 ** (j / 64))) & 0x7fffff for j in range(64))


def exp_lane(value, *, path):
    x = f32(value)
    if not -10 <= x <= 0:
        raise ValueError('Only the decay domain [-10, 0] is reconstructed')
    scaled = f32(x * f32(92.33248138427734))
    if path == 'sse2':
        biased = f32(scaled - f32(-12582912))
        n = f32(f32(-12582912) + biased)
        integer = bits(biased)
    elif path == 'sse41':
        integer = round(scaled)
        n = f32(integer)
    else:
        raise ValueError('Explicit sse2 or sse41 path required')
    remainder = f32(x - f32(n * f32(0.01082611083984375)))
    remainder = f32(remainder - f32(n * f32(4.313856607041089e-06)))
    square = f32(remainder * remainder)
    polynomial = f32(f32(f32(remainder + remainder) + f32(2)) + square)
    exponent_bits = ((((integer + 0x1f80) & 0xffffffff) >> 6) << 23) & 0xffffffff
    scale = from_bits(exponent_bits | MANTISSAS[integer & 63])
    return f32(polynomial * scale)
