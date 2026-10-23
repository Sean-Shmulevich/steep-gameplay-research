"""Finite mathematical reconstruction of input-history direction remapping.

Evidence: INPUT_TO_ACTION_ROUTE.md, History feature direction remapping.
Scalar normalization/trig are derived substitutes, not bit-exact native SIMD.
Conversion and curve are explicit dependencies; no gameplay consumer is inferred.
"""
import math
import struct
from .action_sample import f32, publish_vector


def update_history_features(snapshot, raw_vector, *, convert, curve):
    """Return shifted feature histories and a receipt of the supplied operations.

    convert(vector4) is called three times, preserving the zero-route repeated
    conversion. curve(abs_angle/pi) returns an angle directly, not a normalized
    fraction to rescale by pi. Stable detached snapshots and finite lanes only.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) < 0x2e0:
        raise ValueError('history snapshot must cover offset 0x2df')
    if not isinstance(raw_vector, bytes) or len(raw_vector) != 16:
        raise ValueError('four raw float32 lanes required')
    threshold = f32(struct.unpack_from('<f', snapshot, 0x50)[0])
    vector = [f32(x) for x in struct.unpack('<4f', raw_vector)]
    normalized = publish_vector(vector)['direction']
    calls = []
    def converted(value):
        result = convert(list(value))
        if not isinstance(result, (list, tuple)) or len(result) != 4:
            raise ValueError('conversion must return four finite lanes')
        result = [f32(x) for x in result]
        calls.append(dict(input=list(value), output=list(result)))
        return result
    first = converted(normalized)
    selected = [0., 1., 0., 0.] if normalized[1] > threshold else list(normalized)
    second = converted(selected)
    angle = argument = response = None
    if any(abs(x) > f32(1e-5) for x in selected):
        unit = publish_vector(selected)['direction']
        dot = unit[1]
        if dot >= 1:
            angle = 0.
        elif dot <= -1:
            angle = f32(math.pi)
        else:
            angle = f32(math.acos(dot))
            if unit[0] < 0:
                angle = -angle
        argument = f32(abs(angle) / f32(math.pi))
        response = f32(curve(argument))
        sign = 1 if angle > 0 else -1 if angle < 0 else 0
        theta = f32(sign * response)
        # Finite mathematical equivalent of the native Z-axis quaternion route.
        candidate = [f32(math.sin(theta)), f32(math.cos(theta)), 0., 0.]
    else:
        candidate = second
    third = converted(candidate)
    result = bytearray(snapshot)
    for offset, value in ((0x100, first), (0x1a0, second), (0x240, third)):
        result[offset+16:offset+160] = snapshot[offset:offset+144]
        result[offset:offset+16] = struct.pack('<4f', *value)
    return dict(snapshot=bytes(result), conversions=calls, signed_angle=angle,
                curve_input=argument, curve_output=response,
                numerical_policy='Derived scalar reciprocal seed and trigonometry; recovered flow and history layout; not native bit parity')
