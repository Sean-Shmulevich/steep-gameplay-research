"""Recovered central-impulse wrapper and arithmetic, for finite float32 inputs.

See docs/reconstruction/CENTRAL_IMPULSE.md. No game calls or addresses.
Post-dispatch is reported, not modeled as a guaranteed wake or island update.
"""
import math
import struct


def f32(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('finite value required')
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError as exc:
        raise ValueError('float32 range exceeded') from exc
    if not math.isfinite(result):
        raise ValueError('float32 range exceeded')
    return result


def vector(value):
    if len(value) != 3:
        raise ValueError('three components required')
    return tuple(f32(x) for x in value)


def central_impulse(linear, angular, impulse, inverse_mass, *, kind=0, flags=0, force=False):
    """Return velocities plus wrapper decisions. No dt multiplication here.

    Input validation is our portable API policy; native instructions do not
    implement these checks. kind and flags represent the descriptor bytes.
    """
    linear, angular, impulse = vector(linear), vector(angular), vector(impulse)
    inverse_mass = f32(inverse_mass)
    if inverse_mass < 0 or type(kind) is not int or type(flags) is not int or not 0 <= kind <= 255 or not 0 <= flags <= 255 or type(force) is not bool:
        raise ValueError('nonnegative inverse mass, byte descriptors and boolean force required')
    entered = (kind & 15) != 2 or force
    writes = entered and not flags & 8
    after = tuple(f32(f32(inverse_mass * j) + v) for j, v in zip(impulse, linear)) if writes else linear
    return {'linear': after, 'angular': angular, 'inner_entered': entered,
            'velocity_write_enabled': writes, 'post_dispatch_requested': entered and force}


def coupled_delta_velocity_impulses(delta_velocity, inverse_masses):
    """Derived mod policy: give each dynamic body the same linear delta-v.

    J_i = delta-v / inverse_mass_i. This is not the game's configured jump-mass
    split. No solver, locking, body acquisition or live invocation is implied.
    """
    delta = vector(delta_velocity)
    masses = tuple(f32(x) for x in inverse_masses)
    if not masses or any(x <= 0 for x in masses):
        raise ValueError('positive live inverse masses required for all bodies')
    return tuple(tuple(f32(x / im) for x in delta) for im in masses)


def consume_pending_impulse(pending, bodies):
    """Recovered finite-input pending-vector consumer, with supplied body states.

    bodies is main then optional rider, each a dict of central_impulse arguments
    except impulse/force. This models the call sequence, not real locking.
    """
    if len(pending) != 4 or len(bodies) not in (1, 2):
        raise ValueError('four pending lanes and main plus optional rider required')
    pending = tuple(f32(x) for x in pending)
    threshold = f32(1e-5)
    active = not all(abs(x) <= threshold for x in pending)
    if not active:
        return {'pending': pending, 'consumed': False, 'submissions': (), 'lock_scope': False}
    submissions = tuple(central_impulse(impulse=pending[:3], force=True, **body) for body in bodies)
    return {'pending': (0., 0., 0., 0.), 'consumed': True,
            'submissions': submissions, 'lock_scope': True}


def queue_pending_impulse(pending, impulse):
    """Recovered actor leaf: four float32 additions, with no lock or mass/dt scale.

    pending=None represents a missing runtime and returns None without reading
    impulse, matching the native null-runtime early return. Alignment and object
    lifetime are responsibilities of a native adapter, not this numerical API.
    """
    if pending is None:
        return None
    if len(pending) != 4 or len(impulse) != 4:
        raise ValueError('four lanes required')
    return tuple(f32(f32(a) + f32(b)) for a, b in zip(pending, impulse))


def clear_pending_impulse(pending):
    """Recovered actor leaf: absent runtime is a no-op, otherwise clear all lanes."""
    return None if pending is None else (0., 0., 0., 0.)


def queue_producer_route_selected(state_code, variant):
    """One recovered motion-dispatch route, after its outer actor/lock gates.

    True means the handler containing a queue producer is selected, not that an
    impulse is necessarily produced. Numeric state semantics remain unassigned.
    """
    for value in (state_code, variant):
        if type(value) is not int or not -(1 << 31) <= value <= (1 << 32) - 1:
            raise ValueError('32-bit state code required')
    return state_code == 3 and (variant in (1, 2) or (variant & 0xffffffff) > 8)


def pending_consumer_prepass(enabled_byte, blocked_byte, counter, timer_a, timer_b, helper_gain):
    """Recovered local branch before pending consumption, finite inputs only.

    The configuration-validity byte must already be nonzero. The optional helper
    is reported, not executed; its side effects remain opaque. counter_after assumes
    that helper does not alter the supplied counter. Assuming normal
    return, every local branch then decrements the counter and reaches the
    pending-vector threshold check. This is not an outer actor eligibility test.
    """
    if any(type(v) is not int or not 0 <= v <= 255 for v in (enabled_byte, blocked_byte)):
        raise ValueError('byte flags required')
    if type(counter) is not int or not -(1 << 31) <= counter < (1 << 31):
        raise ValueError('signed 32-bit counter required')
    timer_a, timer_b, helper_gain = map(f32, (timer_a, timer_b, helper_gain))
    helper = (enabled_byte != 0 and blocked_byte == 0 and counter <= 0
              and timer_a <= 0 and timer_b <= 0 and helper_gain > 0)
    decremented = ((counter - 1 + (1 << 31)) & 0xffffffff) - (1 << 31)
    return {'optional_helper_requested': helper, 'counter_after': decremented,
            'reaches_pending_threshold_on_normal_return': True}


def helper_direct_impulses(scale, dt, direction, descriptor_scale, combined_mass, rider_mass,
                           mask_eligible, override_byte):
    """Recovered helper submission tail, with upstream scale/direction supplied.

    Configuration validity and both body pointers must already be established.
    This does not reconstruct how upstream force or direction is produced.
    No clamp on combined_mass - rider_mass is present in this local sequence.
    """
    scale, dt, descriptor_scale, combined_mass, rider_mass = map(
        f32, (scale, dt, descriptor_scale, combined_mass, rider_mass))
    direction = vector(direction)
    if type(mask_eligible) is not bool or type(override_byte) is not int or not 0 <= override_byte <= 255:
        raise ValueError('boolean mask result and byte override required')
    if scale >= f32(-.1) or not (mask_eligible or override_byte != 0):
        return {'submitted': False, 'submissions': ()}
    timed = f32(scale * dt)
    base = tuple(f32(f32(timed * axis) * descriptor_scale) for axis in direction)
    main_share = f32(combined_mass - rider_mass)
    return {'submitted': True, 'submissions': (
        {'body': 'rider', 'impulse': tuple(f32(rider_mass*x) for x in base), 'force': True},
        {'body': 'main', 'impulse': tuple(f32(main_share*x) for x in base), 'force': True},
    )}


def helper_force_scale(speed_scalar, curve_a, curve_b, alignment, measure, measure_limit,
                       response_strength, activity_scalar, contact_time, override_a, override_b,
                       override_gain, *, pivot=15, gain=2):
    """Recovered scalar assembly after the direction/dot-product entry gates.

    Curve outputs, alignment and semantic-free descriptor scalars are supplied.
    pivot/gain defaults are the inspected image values, not proven immutable
    settings. Finite arithmetic checks are portable API policy.
    """
    speed_scalar, curve_a, curve_b, alignment, measure, measure_limit, response_strength, activity_scalar, contact_time, override_gain, pivot, gain = map(
        f32, (speed_scalar, curve_a, curve_b, alignment, measure, measure_limit, response_strength, activity_scalar, contact_time, override_gain, pivot, gain))
    if any(type(v) is not int or not 0 <= v <= 255 for v in (override_a, override_b)):
        raise ValueError('byte overrides required')
    ceiling = f32(pivot * 2)
    if not (speed_scalar < ceiling or override_a or override_b):
        return {'eligible': False, 'scale': None, 'reason': 'speed_gate'}
    if speed_scalar < pivot:
        speed_factor = f32(speed_scalar * gain)
    elif override_a or override_b:
        speed_factor = f32(pivot * gain)
    else:
        speed_factor = f32(f32(ceiling - speed_scalar) * gain)
    if speed_factor <= 0:
        return {'eligible': False, 'scale': None, 'reason': 'nonpositive_speed_factor'}
    use_sqrt = (measure > 0 and measure_limit > measure) or activity_scalar != 0
    if use_sqrt:
        if measure_limit == 0:
            raise ValueError('nonzero measure limit required on square-root branch')
        ratio = f32(measure / measure_limit)
        root_input = f32(1 - min(1., ratio))
        response = max(1., f32(f32(math.sqrt(root_input)) * response_strength))
    elif override_a:
        response = 1.
    else:
        response = min(f32(contact_time * 6), 1.)
    multiplier = override_gain if override_a else 1.
    value = curve_a
    for factor in (alignment, curve_b, speed_factor, response, multiplier):
        value = f32(value * factor)
    return {'eligible': True, 'scale': -value, 'speed_factor': speed_factor,
            'response_factor': response, 'override_factor': multiplier,
            'response_branch': 'sqrt' if use_sqrt else 'override' if override_a else 'contact_ramp'}


def helper_force_geometry(direction_input, reference_axis, source_vector, reciprocal_sqrt):
    """Recovered finite, nondegenerate vector sequence with supplied RSQRT seed.

    reciprocal_sqrt(norm_squared) supplies the processor's approximate RSQRT
    result. Requiring it avoids claiming host math.sqrt reproduces that estimate.
    Reference axis normalization is not performed by these native instructions.
    Rejecting degenerate/nonfinite inputs is authored API policy.
    """
    direction_input, reference_axis, source_vector = map(vector, (direction_input, reference_axis, source_vector))
    def dot(a, b):
        p = [f32(x*y) for x,y in zip(a,b)]
        return f32(p[0] + f32(p[1]+p[2]))
    def cross(a,b):
        return tuple(f32(f32(a[i]*b[j])-f32(a[j]*b[i])) for i,j in ((1,2),(2,0),(0,1)))
    def normalize(a, horizontal=False):
        n = f32(f32(a[0]*a[0])+f32(a[1]*a[1])) if horizontal else dot(a,a)
        if n <= 0:
            raise ValueError('nondegenerate direction required')
        seed = f32(reciprocal_sqrt(n))
        correction = f32(3 - f32(f32(seed*n)*seed))
        coefficient = f32(correction * f32(.5*seed))
        return tuple(f32(coefficient*x) for x in a)
    unit_input = normalize(direction_input)
    projection = dot(source_vector, reference_axis)
    residual = tuple(f32(x-f32(projection*n)) for x,n in zip(source_vector,reference_axis))
    horizontal_sq = f32(f32(residual[0]*residual[0])+f32(residual[1]*residual[1]))
    if horizontal_sq > f32(.0001):
        unit_residual = normalize(residual)
        horizontal = cross(unit_residual,(0.,0.,1.))
        horizontal = normalize((horizontal[0],horizontal[1],0.), horizontal=True)
        direction = cross(horizontal,unit_residual)
        alignment = dot(unit_residual,unit_input)
        branch = 'projected_direction'
    else:
        direction, alignment, branch = (0.,0.,1.), 0., 'world_z_fallback'
    eligibility_dot = dot(reference_axis,unit_input)
    return {'direction':direction, 'alignment':alignment,
            'eligible':eligibility_dot > f32(-.6), 'eligibility_dot':eligibility_dot,
            'branch':branch, 'normalized_input':unit_input}


def helper_entry_eligible(curve_result, contact_fraction, auxiliary_scalar, override_a, override_b):
    """Recovered helper entry gate; auxiliary scalar's meaning remains unnamed."""
    curve_result, contact_fraction, auxiliary_scalar = map(f32, (curve_result,contact_fraction,auxiliary_scalar))
    if any(type(v) is not int or not 0 <= v <= 255 for v in (override_a,override_b)):
        raise ValueError('byte overrides required')
    return curve_result > f32(.1) and (contact_fraction > 0 or override_a != 0
                                     or (auxiliary_scalar < f32(.05) and override_b != 0))


def helper_velocity_history(previous_velocity, current_velocity, dt):
    """Recovered history shift and finite-difference acceleration for XYZ.

    Native code copies current cached velocity to previous, then samples the
    body. Inputs here are those two samples. Positive dt is authored API policy.
    """
    previous_velocity, current_velocity = vector(previous_velocity), vector(current_velocity)
    dt = f32(dt)
    if dt <= 0:
        raise ValueError('positive history timestep required')
    acceleration = tuple(f32(f32(new-old)/dt) for old,new in zip(previous_velocity,current_velocity))
    return {'previous':previous_velocity,'current':current_velocity,'acceleration':acceleration}


def helper_response_filter(rate, displacement, acceleration, reference_axis, dt):
    """Recovered asymmetric two-state filter and scalar publication.

    Names rate/displacement describe the integration, not an established visual
    or physical consumer. Source constants are preserved; no tuning substitute.
    """
    rate, displacement, dt = map(f32,(rate,displacement,dt))
    acceleration, reference_axis = vector(acceleration), vector(reference_axis)
    stiffness = 1000. if rate > 0 else 3000.
    restoring = -f32(stiffness*displacement)
    damping = f32(rate*-300.)
    products = [f32(a*b) for a,b in zip(reference_axis,acceleration)]
    dot = f32(products[0]+f32(products[1]+products[2]))
    drive = f32(dot*reference_axis[2])
    if drive < 10.:
        drive = 0.
    force = f32(f32(f32(damping+restoring)/80.)+drive)
    new_rate = f32(f32(force*dt)+rate)
    new_displacement = f32(f32(dt*new_rate)+displacement)
    lower, upper = f32(-.2), f32(.8)
    clipped = new_displacement > upper or new_displacement < lower
    if clipped:
        new_displacement = upper if new_displacement > upper else lower
        new_rate = 0.
    return {'rate':new_rate,'displacement':new_displacement,'drive':drive,
            'stiffness':stiffness,'clipped':clipped,
            'published':(new_rate,new_displacement)}


def advance_preconsume_countdown(value, elapsed_dt):
    """Recovered local float32 countdown update, before later branch resets.

    CENTRAL_IMPULSE.md, 'Countdown clock and adjacent impulse magnitude'.
    No zero clamp: expired values continue decreasing. Finite validation is an
    authored API policy. This does not execute the surrounding impulse branch.
    """
    return f32(f32(value) - f32(elapsed_dt))
