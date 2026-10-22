"""TU7 version-94 replay spatial block, not a complete replay record.

Evidence: LIVE_REPLAY_LEADS.md, Spatial block. Channel names are ordinal;
coordinate frame, units and body/bone identity are unresolved. Bounds/finite
checks are authored guards. The reciprocal-square-root seed is explicit because
its native instruction approximation is not a portable mathematical constant.
"""
import math
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def decode_spatial(payload, *, version, rsqrt_seed):
    """Decode 51 bytes; rsqrt_seed accepts the float32 squared quaternion norm.

    Callers may supply lambda s: 1/math.sqrt(s) as an authored approximation.
    This does not reproduce the native RSQRTPS seed. Trailing bytes are allowed.
    """
    if type(version) is not int or version != 94:
        raise ValueError('Only inspected record version 94 is supported')
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 51:
        raise ValueError('Spatial block requires 51 bytes')
    if not callable(rsqrt_seed):
        raise ValueError('Explicit reciprocal-square-root seed required')
    anchor = list(struct.unpack_from('<3f', payload))
    extra = list(struct.unpack_from('<3f', payload, 35))
    if not all(math.isfinite(x) for x in anchor + extra):
        raise ValueError('Nonfinite spatial coordinates')
    scale = f32(1 / 127)
    def quantized(offset, count):
        return [f32(v * scale) for v in struct.unpack_from('<' + 'b'*count, payload, offset)]
    points = [[f32(a + d) for a, d in zip(anchor, quantized(12+3*i, 3))]
              for i in range(5)]
    rotations = []
    for index in range(2):
        xyz = quantized(29+3*index, 3)
        squares = [f32(x*x) for x in xyz]
        length2 = f32(f32(f32(squares[0]+0.0)+squares[1])+squares[2])
        if length2 > 1:
            length = f32(math.sqrt(length2))
            rotations.append([f32(x/length) for x in xyz] + [0.0])
        else:
            sign = -1.0 if payload[27+index] else 1.0
            rotations.append(xyz + [f32(f32(math.sqrt(f32(1-length2)))*sign)])
    candidate = quantized(47, 4)
    squares = [f32(x*x) for x in candidate]
    length2 = f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
    if length2 == 0:
        raise ValueError('Zero quaternion has no finite normalization')
    seed = f32(rsqrt_seed(length2))
    if not math.isfinite(seed) or seed <= 0:
        raise ValueError('Seed must be finite and positive')
    factor = f32(f32(3-f32(f32(seed*length2)*seed))*f32(0.5*seed))
    return {'anchor': anchor, 'relative_points': points,
            'rotations': rotations, 'extra_vector': extra,
            'extra_rotation': [f32(x*factor) for x in candidate],
            'consumed': 51}
