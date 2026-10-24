"""Recovered local velocity-correction decisions with supplied upstream inputs.

Evidence: CENTRAL_IMPULSE.md, Post-submission velocity setter and speed floor.
Damping curves, frame transforms, activation and native setter remain external.
"""
from math import sqrt
from reference.central_impulse import f32
from .snow_post_pending import four


def speed(vector):
    squares=[f32(x*x) for x in vector[:3]]
    return f32(sqrt(f32(squares[0]+f32(squares[1]+squares[2]))))


def preserve_speed_floor(original, candidate, floor, bypass):
    """Finite XYZ velocities; W zeroed as in the surrounding native producers.

    Local branch RVA 0x13f81e0..0x13f8225. No global minimum-speed policy:
    original speeds below the floor are preserved rather than accelerated.
    """
    if type(bypass) is not bool:
        raise ValueError('Explicit bypass boolean required')
    original=four(original);candidate=four(candidate)
    original[3]=candidate[3]=0.0
    floor=f32(floor);old_speed=speed(original);new_speed=speed(candidate)
    if bypass or floor <= new_speed:
        return dict(velocity=candidate,speed=new_speed,action='candidate')
    if old_speed > floor:
        return dict(velocity=[f32(f32(floor*x)/old_speed) for x in original],
                    speed=floor,action='original_direction_at_floor')
    return dict(velocity=original,speed=old_speed,action='original')


def directional_velocity_decay(velocity, rates, elapsed, to_frame, from_frame, sample_decay):
    """Local transform/axis-decay/transform path before contact correction.

    Source RVA 0x13f7faf..0x13f80d7. Three native columns per frame are supplied;
    their producer/orthogonality is not assumed. sample_decay supplies the runtime
    lookup, whose initialized contents are not established by this composition.
    """
    if len(rates)!=3 or len(to_frame)!=3 or len(from_frame)!=3:
        raise ValueError('Expected three rates and three columns per frame')
    velocity=four(velocity);velocity[3]=0.0
    def transform(v,columns):
        columns=[four(c) for c in columns]
        result=[f32(f32(f32(v[2]*columns[2][j])+f32(v[1]*columns[1][j]))+
                    f32(v[0]*columns[0][j])) for j in range(4)]
        result[3]=0.0
        return result
    local=transform(velocity,to_frame);dt=f32(elapsed)
    # The native order samples Z, Y, X; preserve it for an observable provider.
    damped=local[:];arguments=[None]*3;gains=[None]*3
    for axis in (2,1,0):
        arguments[axis]=-f32(dt*f32(rates[axis]))
        gains[axis]=f32(sample_decay(arguments[axis]))
        damped[axis]=f32(gains[axis]*local[axis])
    return dict(velocity=transform(damped,from_frame),frame_velocity=local,
                decay_arguments=arguments,decay_gains=gains)


def contact_return_candidate(velocity, direction, duration, strength, disabled, lower, upper):
    """RVA 0x13f80dc..0x13f81c0: directional correction then XYZ clamps.

    The 0.5 window is recovered. Direction/strength/disable flag and runtime
    clamp values remain supplied. No normal normalization or bound repair.
    """
    if type(disabled) is not bool or len(lower)!=3 or len(upper)!=3:
        raise ValueError('Explicit flag and three bounds per side required')
    v=four(velocity);n=four(direction);duration=f32(duration)
    applied=False
    if not disabled and duration < f32(.5):
        products=[f32(a*b) for a,b in zip(v,n)]
        dot=f32(f32(products[1]+products[3])+f32(products[0]+products[2]))
        correction=f32(f32(.5-duration)*dot)
        correction=f32(correction+correction)
        if correction < 0:
            correction=f32(correction*f32(strength))
            v=[f32(x-f32(correction*y)) for x,y in zip(v,n)]
            applied=True
    adjusted=v[:]
    for axis in range(3):
        lo,hi=f32(lower[axis]),f32(upper[axis])
        if lo > v[axis]:v[axis]=lo
        elif v[axis] > hi:v[axis]=hi
    v[3]=0.0
    return dict(velocity=v,adjusted_velocity=adjusted,correction_applied=applied)


def correct_linear_velocity(original, rates, elapsed, to_frame, from_frame, sample_decay,
                            direction, duration, strength, disabled, lower, upper, floor, bypass):
    """Connected local arithmetic ending before the native linear setter.

    Upstream activation, curves/configuration and subsequent impulses are external.
    The stages deliberately preserve order: the floor may override correction
    and clamps using the original velocity, not the intermediate direction.
    """
    decay=directional_velocity_decay(original,rates,elapsed,to_frame,from_frame,sample_decay)
    contact=contact_return_candidate(decay['velocity'],direction,duration,strength,disabled,lower,upper)
    selected=preserve_speed_floor(original,contact['velocity'],floor,bypass)
    return dict(decay=decay,contact=contact,selected=selected)
