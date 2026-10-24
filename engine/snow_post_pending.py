"""Finite-input post-pending submission loops; no locks or body mutation.

Evidence: CENTRAL_IMPULSE.md, Post-pending point-impulse loops.
Resolved scalars and record data are supplied; their producers remain external.
"""
from reference.central_impulse import f32


def four(value):
    if len(value) != 4:
        raise ValueError('four lanes required')
    return [f32(x) for x in value]


def directional_submissions(records, combined_scale):
    """Already-entered first loop, after the positive outer gate and curve work."""
    scale = f32(combined_scale)
    return [dict(index=i, impulse=[f32(scale*x) for x in four(r['direction'])],
                 point=four(r['point']), force=True)
            for i, r in enumerate(records) if r['enabled']]


def summed_submissions(records, gate_one, gate_other, runtime_scale):
    """Type exactly 1 selects gate_one; every other byte selects gate_other.

    Selected gate controls eligibility only. It does not scale the impulse.
    """
    gates = [f32(gate_other), f32(gate_one)]
    scale = f32(runtime_scale)
    result = []
    for i, record in enumerate(records):
        kind = record['kind']
        if type(kind) is not int or not 0 <= kind <= 255:
            raise ValueError('byte kind required')
        if not record['enabled'] or gates[kind == 1] <= 0:
            continue
        a, b = four(record['a']), four(record['b'])
        result.append(dict(index=i, impulse=[f32(f32(x+y)*scale) for x,y in zip(a,b)],
                           point=four(record['point']), force=True))
    return result


def attenuate_point_gates(gate_one, gate_other, input_scalar, denominator,
                          lower_one, lower_other, upper):
    """Already-entered local gate update; caller supplies outer branch decision.

    Source block at RVA 0x1409362. Upper is incoming XMM11, not assumed one.
    No clamping; zero denominator is outside this finite portable contract.
    """
    one, other, value, denom, low_one, low_other, high = map(f32,
        (gate_one, gate_other, input_scalar, denominator, lower_one, lower_other, upper))
    if denom == 0:
        raise ValueError('nonzero denominator required')
    weight = f32(f32(denom-value)/denom)
    blend_one = f32(f32(f32(high-low_one)*weight)+low_one)
    blend_other = f32(f32(f32(high-low_other)*weight)+low_other)
    return (f32(f32(blend_one*blend_one)*one), f32(blend_other*other))
