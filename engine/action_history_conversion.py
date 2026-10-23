"""Finite mathematical mode-3 history conversion, not an active-mode selector.

Evidence: INPUT_TO_ACTION_ROUTE.md, Four-lane mode-3 conversion.
Normalization includes the fourth lane, but the final SIMD mask clears W. Scalar normalization/trigonometry are explicit numerical substitutes.
"""
import math
from .action_sample import f32


def _lanes(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('four finite lanes required')
    return [f32(v) for v in value]


def convert_history_mode3(vector, *, primary, secondary):
    """Resolve supplied basis vectors and return converted four-lane value.

    Caller asserts mode 3 and resolves its basis object. An exactly zero input
    returns before inspecting basis values. Degenerate projected basis and
    overflow/underflow in normalization are unsupported, not silently repaired.
    """
    value = _lanes(vector)
    policy = 'Derived scalar normalization and trig; decoded four-lane expression; not native bit parity'
    if all(v == 0 for v in value):
        return dict(output=value, secondary_used=None, yaw=None, numerical_policy=policy)
    axis = _lanes(primary)
    fallback = abs(f32(abs(axis[2])-1.0)) <= f32(1e-5)
    if fallback:
        axis = _lanes(secondary)
    planar_length = math.hypot(axis[0], axis[1])
    if planar_length == 0:
        raise ValueError('degenerate projected basis is outside supported domain')
    xx, yy, zz, ww = [f32(v*v) for v in value]
    length = f32(math.sqrt(f32(f32(xx+zz)+f32(yy+ww))))
    if length == 0:
        raise ValueError('input normalization underflow is outside supported domain')
    x, y, z, w = [f32(v/length) for v in value]
    yaw = math.atan2(-axis[0]/planar_length, axis[1]/planar_length)
    sine, cosine = math.sin(yaw), math.cos(yaw)
    output = [f32(cosine*x-sine*y), f32(sine*x+cosine*y), z,
              0.0]
    return dict(output=output, secondary_used=fallback, yaw=yaw, numerical_policy=policy)
