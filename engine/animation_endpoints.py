"""Recovered endpoint arithmetic over caller-supplied samples.

Evidence: docs/reconstruction/ANIMATION_ENDPOINT_MOTION.md. Channel selection,
resource dispatch and gameplay application are deliberately outside this API.
"""
import math
import struct


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _vector(value):
    result = tuple(f32(x) for x in value)
    if len(result) != 4 or not all(math.isfinite(x) for x in result):
        raise ValueError('expected four finite float32 lanes')
    return result


def endpoint_delta(start_position, end_position, start_rotation, end_rotation,
                   *, variant=False, rsqrt_estimate=None):
    """Return four-lane displacement and normalized conjugate(start)*end.

    Variant negates displacement x and rotation y/z. Default reciprocal square
    root seed is a derived scalar substitute for native RSQRTPS. A caller may
    supply its observed seed. Finite/nonzero validation is our API safeguard.
    """
    if type(variant) is not bool:
        raise ValueError('expected boolean variant')
    p, q, a, b = map(_vector, (start_position, end_position,
                              start_rotation, end_rotation))
    displacement = [f32(y-x) for x, y in zip(p, q)]
    cx, cy, cz, cw = -a[0], -a[1], -a[2], a[3]
    # Match native product accumulation: w term, x term, y term, z term.
    terms = ((b[0]*cw, b[3]*cx, b[2]*cy, -b[1]*cz),
             (b[1]*cw, -b[2]*cx, b[3]*cy, b[0]*cz),
             (b[2]*cw, b[1]*cx, -b[0]*cy, b[3]*cz),
             (b[3]*cw, -b[0]*cx, -b[1]*cy, -b[2]*cz))
    rotation = []
    for row in terms:
        v = f32(row[0])
        for term in row[1:]:
            v = f32(v + f32(term))
        rotation.append(v)
    if variant:
        displacement[0] = -displacement[0]
        rotation[1], rotation[2] = -rotation[1], -rotation[2]
    squares = [f32(x*x) for x in rotation]
    norm = f32(f32(squares[1]+squares[3]) + f32(squares[0]+squares[2]))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError('expected nonzero finite rotation norm')
    seed = f32(1/math.sqrt(norm) if rsqrt_estimate is None else rsqrt_estimate)
    if not math.isfinite(seed) or seed <= 0:
        raise ValueError('expected positive finite reciprocal seed')
    scale = f32(f32(seed*0.5) * f32(3.0-f32(seed*f32(seed*norm))))
    return {'displacement': displacement,
            'rotation': [f32(x*scale) for x in rotation],
            'seed_policy': 'derived_scalar' if rsqrt_estimate is None else 'caller_supplied'}
