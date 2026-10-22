"""Finite float32 input cooker with an explicit external decay lookup.

Evidence: CENTRAL_IMPULSE.md, 'Input cooker arithmetic'. No implicit math.exp
substitute or embedded game lookup table. Callback must return a finite scalar.
"""
from reference.central_impulse import f32


def cook(current, target, elapsed_dt, coefficients, *, decay_lookup, epsilon=.0001):
    current,target,dt,epsilon=map(f32,(current,target,elapsed_dt,epsilon))
    direction='ToZero' if abs(target)<=abs(current) or f32(current*target)<=0 else 'ToOne'
    base=f32(coefficients['baseDampFactor'+direction])
    proportional=f32(coefficients['proportionalDampFactor'+direction])
    argument=f32(-f32(dt*proportional))
    decay=f32(decay_lookup(argument))
    error=f32(target-current)
    step=f32(f32(f32(1.-decay)*abs(error))+f32(dt*base))
    if target>current:
        candidate=f32(current+step)
        if candidate>target: candidate=target
    else:
        candidate=f32(current-step)
        if candidate<target: candidate=target
    if abs(f32(target-candidate))<epsilon:
        candidate=target
    return {'value':candidate,'direction':direction,'lookup_argument':argument,
            'lookup_result':decay,'step':step}
