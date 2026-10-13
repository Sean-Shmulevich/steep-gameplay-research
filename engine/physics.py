"""Independent snow/walking vertical slice; Z up, metres and seconds.

Recovered local kernels: reference.snow contact_forces, cooker, preset_weight,
and rider_spring. Point contact geometry, constraints, steering/edge policies,
material scaling, jump energy, landing classifier, integration and ALL default
settings below are synthetic design choices. They are not original game rules.
The absorption spring is visual state only; it never injects body momentum.
"""
import copy
import math
from reference import snow

DEFAULTS = dict(gravity=9.81, push_acceleration=1.2, brake_deceleration=8.0,
                edge_response=5.0, turn_rate=1.5, jump_speed=2.0,
                jump_charge_gain=2.5, charge_seconds=0.7, air_torque=5.0,
                air_drag=0.03, walking_speed=2.5, walking_response=8.0,
                crash_impact=10.0, sketchy_impact=5.0,
                spring_mass=1.0, spring_stiffness=90.0, spring_damping=18.0)
add, sub, mul, dot, cross, norm = snow.add, snow.sub, snow.mul, snow.dot, snow.cross, snow.norm


def _finite(value):
    if isinstance(value, dict):
        for v in value.values():
            _finite(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _finite(v)
    elif isinstance(value, (int, float)) and not math.isfinite(value):
        raise ValueError('nonfinite physics input or result')


def _vec(value, n):
    if not isinstance(value, (list, tuple)) or len(value) != n:
        raise ValueError('invalid vector size')
    result = tuple(float(v) for v in value)
    _finite(result)
    return result


def _unit(v):
    length = norm(v)
    if length < 1e-12:
        raise ValueError('zero normal or quaternion')
    return mul(v, 1 / length)


def _qmul(a, b):
    av, bv = a[:3], b[:3]
    xyz = add(add(mul(bv, a[3]), mul(av, b[3])), cross(av, bv))
    return (*xyz, a[3] * b[3] - dot(av, bv))


def _rotate(q, v):
    return add(v, mul(cross(q[:3], add(cross(q[:3], v), mul(v, q[3]))), 2))


def _orientation(heading, normal):
    # Swing world-up to support normal, then apply heading in support plane.
    axis = cross((0., 0., 1.), normal)
    swing = _unit((*axis, 1 + normal[2]))
    yaw = (0., 0., math.sin(heading / 2), math.cos(heading / 2))
    return _unit(_qmul(swing, yaw))


def _sample(world, position):
    row = world.sample(position[0], position[1])
    _finite(row)
    n = _unit(_vec(row['normal'], 3))
    if n[2] <= 0.05:
        raise ValueError('height-field support normal must point upwards')
    material = row['material']
    for key in ('density', 'thickness', 'normal_frequency', 'tangent_frequency', 'grip'):
        if float(material.get(key, 0)) < 0:
            raise ValueError('negative material value: ' + key)
    return float(row['height']), n, material, _vec(row.get('velocity', [0, 0, 0]), 3)


def step(body, controls, world, dt, config):
    """Advance <= 0.05s. Mutates body only after successful validation.

    Jump charges while held on support and fires on release. Air steer/flip add
    angular velocity, while release preserves angular momentum (no hidden cap).
    Walking tuck supplies forward intent; walking is a separate velocity servo,
    never the board's fluid-contact controller. Parent owns time and event log.
    """
    _finite((body, controls, config, dt))
    if not 0 < dt <= 0.05:
        raise ValueError('dt must be in (0, 0.05]; subdivide larger intervals')
    sport = config.get('sport', 'snowboard')
    if sport not in ('snowboard', 'ski', 'walking'):
        raise ValueError('unsupported ground sport')
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in config.items() if k in DEFAULTS})
    cfg.update(config.get('physics', {}))
    if any(not isinstance(v, (int, float)) or v < 0 for v in cfg.values()):
        raise ValueError('physics tuning must be nonnegative numbers')
    if cfg['charge_seconds'] <= 0 or cfg['spring_mass'] <= 0:
        raise ValueError('charge_seconds and spring_mass must be positive')
    b = copy.deepcopy(body)
    p, v = _vec(b['position'], 3), _vec(b['velocity'], 3)
    q = _unit(_vec(b['orientation'], 4))
    omega = _vec(b['angular_velocity'], 3)
    mass = float(b['mass'])
    if mass <= 0:
        raise ValueError('mass must be positive')
    state = b.setdefault('_snow_physics', {})
    heading = state.get('heading', math.atan2(_rotate(q, (1, 0, 0))[1], _rotate(q, (1, 0, 0))[0]))
    state.setdefault('charge', 0.)
    state.setdefault('jump_held', False)
    state.setdefault('steer', 0.)
    state.setdefault('absorption', 0.)
    state.setdefault('absorption_velocity', 0.)
    raw = float(controls.get('steer', 0))
    flip = float(controls.get('flip', 0))
    lean = float(controls.get('lean', 0))
    if max(abs(raw), abs(flip), abs(lean)) > 1:
        raise ValueError('control axis outside [-1,1]')
    state['steer'] = snow.cooker(state['steer'], raw, dt,
        dict(baseDampFactorToZero=0., proportionalDampFactorToZero=12.,
             baseDampFactorToOne=0., proportionalDampFactorToOne=9.))
    steer = state['steer']
    height, n, material, support_velocity = _sample(world, p)
    rel = sub(v, support_velocity)
    supported = bool(b.get('grounded')) and p[2] <= height + 0.03 and dot(rel, n) <= 0.25
    was_grounded = supported
    events = []
    contact_impulse = (0., 0., 0.)
    jump = bool(controls.get('jump'))
    if supported and jump:
        state['charge'] = min(cfg['charge_seconds'], state['charge'] + dt)
    launch = supported and state['jump_held'] and not jump
    if launch:
        charge = state['charge'] / cfg['charge_seconds']
        speed = cfg['jump_speed'] + cfg['jump_charge_gain'] * charge
        rel = add(sub(rel, mul(n, dot(rel, n))), mul(n, speed))
        v = add(rel, support_velocity)
        supported = False
        state['charge'] = 0.
        events.append(dict(type='jump', charge=charge, speed=speed, policy='synthetic'))
    elif not supported:
        state['charge'] = 0.
    state['jump_held'] = jump
    gravity = (0., 0., -cfg['gravity'])
    speed_blend = snow.preset_weight(norm(rel))
    if supported:
        gravity = sub(gravity, mul(n, dot(gravity, n)))
        heading += steer * cfg['turn_rate'] * dt * (1 - 0.45 * speed_blend)
        q = _orientation(heading, n)
        forward = _rotate(q, (1., 0., 0.))
        lateral = cross(n, forward)
        rel = sub(rel, mul(n, dot(rel, n)))
        if sport == 'walking':
            desired = cfg['walking_speed'] if controls.get('tuck') and not controls.get('brake') else 0.
            target = mul(forward, desired)
            rel = add(rel, mul(sub(target, rel), 1 - math.exp(-cfg['walking_response'] * dt)))
            # Walking servo includes support gravity compensation, a separate policy.
            gravity = (0., 0., 0.)
        else:
            density_scale = max(0.25, min(2., float(material.get('density', 300)) / 300))
            frequency = float(material.get('tangent_frequency', 0.1)) * math.sqrt(density_scale)
            forces = snow.contact_forces(n, rel, dt, mass,
                float(material.get('normal_frequency', 2)), frequency,
                hull_mode=False, depth_fraction=1.)
            contact_impulse = forces['impulse']
            candidate = add(rel, mul(contact_impulse, 1 / mass))
            # Synthetic stability guard: damping cannot reverse the whole velocity.
            rel = candidate if dot(candidate, rel) >= 0 else (0., 0., 0.)
            grip = float(material.get('grip', 1)) * (1 + 0.6 * abs(lean))
            # Ski difference is an explicit authored substitute, not recovered tuning.
            edge = cfg['edge_response'] * grip * (1.15 if sport == 'ski' else 1.)
            rel = sub(rel, mul(lateral, dot(rel, lateral) * (1 - math.exp(-edge * dt))))
            if controls.get('tuck'):
                rel = add(rel, mul(forward, cfg['push_acceleration'] * dt))
            if controls.get('brake'):
                length = norm(rel)
                rel = mul(rel, max(0., 1 - cfg['brake_deceleration'] * dt / length)) if length else rel
        v = add(add(rel, support_velocity), mul(gravity, dt))
        omega = (0., 0., 0.)
    else:
        v = mul(add(v, mul(gravity, dt)), math.exp(-cfg['air_drag'] * dt))
        # World yaw and rider-relative flip torques do not alter translation.
        flip_axis = _rotate(q, (0., 1., 0.))
        omega = add(omega, mul(add((0., 0., raw), mul(flip_axis, flip)), cfg['air_torque'] * dt))
        angle = norm(omega) * dt
        if angle:
            delta = (*mul(omega, math.sin(angle / 2) / norm(omega)), math.cos(angle / 2))
            q = _unit(_qmul(delta, q))
        heading = math.atan2(_rotate(q, (1, 0, 0))[1], _rotate(q, (1, 0, 0))[0])
    p = add(p, mul(v, dt))
    floor, n2, _, ground_velocity = _sample(world, p)
    # Numerical contact tolerance is a designed height-field policy, not a recovered threshold.
    skin = .003 if supported else 1e-7
    separating_limit = .1 if supported else 1e-7
    grounded = p[2] <= floor + skin and dot(sub(v, ground_velocity), n2) <= separating_limit
    if grounded:
        relative = sub(v, ground_velocity)
        impact = max(0., -dot(relative, n2))
        if not was_grounded and not launch:
            alignment = dot(_rotate(q, (0, 0, 1)), n2)
            quality = 'crash' if impact > cfg['crash_impact'] or alignment < 0.25 else 'sketchy' if impact > cfg['sketchy_impact'] or alignment < 0.8 else 'clean'
            events.append(dict(type='landing', quality=quality, impact_speed=impact,
                               alignment=alignment, policy='synthetic'))
            state['absorption_velocity'] += min(impact, 10.) * 0.2
        p = (p[0], p[1], floor)
        v = add(sub(relative, mul(n2, min(0., dot(relative, n2)))), ground_velocity)
    a, av, _ = snow.rider_spring(state['absorption'], state['absorption_velocity'], 0., 0.,
        cfg['spring_mass'], cfg['spring_stiffness'], cfg['spring_damping'], 0., dt)
    state.update(heading=heading, absorption=a, absorption_velocity=av)
    b.update(position=list(p), velocity=list(v), orientation=list(q),
             angular_velocity=list(omega), grounded=grounded)
    _finite(b)
    body.clear()
    body.update(b)
    return dict(sport=sport, events=events, speed=norm(v), grounded=grounded,
        control_blend=speed_blend, steering=steer, contact_impulse=list(contact_impulse),
        absorption=a, material=material.get('name', 'unnamed'),
        evidence=dict(kernels='recovered local reference math',
                      controller='synthetic independent implementation',
                      landing='synthetic thresholds; no original classifier claim'))
