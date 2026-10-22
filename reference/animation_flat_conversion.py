"""Recovered kind-zero pose conversion ordering; group kinds remain unsupported.

Evidence: CENTRAL_IMPULSE.md, Flat result pose accumulation.
Provider evaluation, temporary storage and pose blend are supplied dependencies.
"""
import math
import struct


def _f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        return math.copysign(float('inf'), value)


def _divide(a, b):
    if b == 0:
        if a == 0 or math.isnan(a):
            return float('nan')
        return math.copysign(float('inf'), math.copysign(1, a) * math.copysign(1, b))
    return _f32(a / b)


def convert_flat_results(records, parent_weight, context, output, *, publish_token,
                         evaluate, prepare_temporary, blend, cleanup):
    """Return authored success/weight diagnostics for a complete kind-zero list.

    evaluate(provider, destination, context); blend(output, temporary, factor).
    cleanup(temporary) runs on normal completion, including empty input. A None
    temporary denotes the native initially empty descriptor. Exception unwinding
    is not modeled. Reject group kinds rather than silently flattening them.
    """
    records = [bytes(r) for r in records]
    if len(records) > 65535 or any(len(r) != 24 for r in records):
        raise ValueError('bounded 24-byte records required')
    for r in records:
        if r[22] != 0 or struct.unpack_from('<H', r, 20)[0] != 1:
            raise ValueError('only flat kind-zero unit-span records supported')
    parent_weight = _f32(parent_weight)
    total = 0.0; temporary = None
    for i, record in enumerate(records):
        token, provider, weight = struct.unpack_from('<QQf', record)
        weighted = _f32(parent_weight * weight)
        publish_token(context, token)
        if i == 0:
            evaluate(provider, output, context)
        else:
            temporary = prepare_temporary(temporary, context)
            evaluate(provider, temporary, context)
            blend(output, temporary, _divide(weighted, _f32(weighted + total)))
        total = _f32(total + weighted)
    # MINSS(1, total) selects total on unordered or equal comparison.
    reported = 1.0 if 1.0 < total else total
    cleanup(temporary)
    return {'success': bool(records), 'total_weight': total, 'reported_weight': reported}
