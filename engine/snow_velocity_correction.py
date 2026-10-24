"""Recovered local velocity-correction decisions with supplied upstream inputs.

Evidence: CENTRAL_IMPULSE.md, Post-submission velocity setter and speed floor.
Frame/rate producers, activation and native setter remain external. The decay
table has an explicit initializer-backed sampler below. Component bounds may
be supplied from body_velocity_limits.initialized_velocity_limits, but that
does not establish the current live globals.
"""
from math import sqrt
from reference.central_impulse import f32
from .snow_post_pending import four


def select_velocity_decay_drive(product_a, product_b, retention_byte,
                                override_value, drive_value, runtime_scale,
                                override_inhibit_byte):
    """Finite upstream selection at RVA 0x13f7cf1..0x13f7df6.

    Argument names describe local arithmetic, not recovered gameplay actions.
    Activation (runtime immersion > float32(.01)) is external. Byte fields are
    raw uint8 values, not assumed Boolean. See CENTRAL_IMPULSE.md, Upstream
    velocity decay drive selection, for field provenance and override ordering.
    """
    for value in (retention_byte,override_inhibit_byte):
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError('Raw uint8 fields required')
    product_a,product_b,override_value,drive_value,runtime_scale=map(
        f32,(product_a,product_b,override_value,drive_value,runtime_scale))
    positive=override_value > 0
    if f32(product_a*product_b) < 0 and retention_byte == 0 and not positive:
        drive_value=0.0
    selected=f32(drive_value*drive_value)
    scaled=f32(selected*f32(.3))
    larger=override_value if override_value > scaled else scaled
    additive=f32(f32(f32(.7)*runtime_scale)*larger)
    inline=positive and override_inhibit_byte == 0
    if inline:
        additive=selected=override_value
    return dict(additive_rate=additive,selected_drive=selected,
                speed_floor_bypassed=positive,inline_configuration_selected=inline)


def assemble_velocity_decay_rates(base_rate, xy_curve_value, z_curve_value,
                                  additive_rate, xy_gain, suppression_vector):
    """Finite local rate assembly at RVA 0x13f7e93..0x13f7f40.

    Curve results and already-selected base rate are supplied. XY share a rate;
    Z has a separate curve and no xy_gain multiplication. The supplied four-lane
    vector is tested componentwise, including W. Its semantic producer remains
    unresolved; the returned flag also disables the later contact correction.
    Evidence: CENTRAL_IMPULSE.md, Per-axis velocity decay rate assembly.
    """
    base_rate,xy_curve_value,z_curve_value,additive_rate,xy_gain = map(
        f32,(base_rate,xy_curve_value,z_curve_value,additive_rate,xy_gain))
    vector=four(suppression_vector)
    def clamp_unit(value):
        return 0.0 if value < 0 else (1.0 if value > 1 else value)
    xy=clamp_unit(f32(xy_curve_value+additive_rate))
    z=clamp_unit(f32(z_curve_value+additive_rate))
    # SSE MAX selects its second operand on equality; retain signed-zero choice.
    xy=base_rate if base_rate > xy else xy
    z=base_rate if base_rate > z else z
    xy=f32(xy*xy_gain)
    disabled=any(abs(x) > f32(.00001) for x in vector)
    rates=[xy,xy,z,0.0]
    if disabled:
        rates=[f32(x*f32(.01)) for x in rates]
    return dict(rates=rates,contact_correction_disabled=disabled)


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


def build_velocity_decay_sampler(*, vector_path, scalar_path):
    """Build the independently reconstructed native table once for reuse.

    Initializer join: CENTRAL_IMPULSE.md, Native decay initializer joined to
    velocity correction. CPU paths must be explicit; this does not inspect live
    CPU dispatch or mutable native globals. No native table payload is loaded.
    """
    from reference.decay_exp import cooker_table
    from reference.runtime_curve import evaluate
    table=cooker_table(vector_path=vector_path,scalar_path=scalar_path)
    return lambda argument:evaluate(argument,**table)
