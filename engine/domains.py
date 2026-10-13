"""Air and environment kernels for the independent engine.

Evidence: docs/systems/air/CLIENT_GUIDE.txt (local response and force laws),
docs/systems/world/environment-runtime/pseudocode.md (clock, weather and overlay ordering).
Presets, input-to-heading mapping, seconds-to-delta mapping and integration are
explicit synthetic policies. No original assets or authored presets are loaded.
Z is up and yaw zero points +X; original air +Y-forward basis is adapted here.
"""
import math


def _clamp(x, lo, hi):
    return min(hi, max(lo, x))


def _finite(x, name):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(name + ' must be finite')
    return x


def _dt(dt):
    dt = _finite(dt, 'dt')
    if dt < 0:
        raise ValueError('dt must be nonnegative')
    return dt


def _response(previous_target, integral, previous_window, target, window, dt):
    """Recovered duration-weighted trapezoidal response, not exponential drag."""
    w = max(dt, window)
    total = integral / previous_window * (w - dt) + (target + previous_target) * dt * .5
    return total, w, total / w


def _para_forces(velocity, up, lift_gain, drag_gain, gravity):
    x, y, z = velocity
    h2 = x*x + y*y
    downward2 = h2 + min(z, 0)**2
    upward2 = max(z, 0)**2
    lift = [lift_gain * downward2 * u - (upward2 if i == 2 else 0) for i, u in enumerate(up)]
    h = math.sqrt(h2)
    # Preserve the unusual near-zero branch in the documented routine.
    drag = [-drag_gain*h2*x/h, -drag_gain*h2*y/h, 0.] if max(abs(x), abs(y)) > 9.999999747378752e-6 else [x, y, 0.]
    return lift, drag, [0., 0., -gravity]


def step_air(body, controls, dt, config):
    """Mutate body; config sport selects wingsuit/paraglider.

    Config keys: wind (already processed additive velocity), gravity, turn_rate,
    horizontal_speed, sink_speed, response_seconds, dive_horizontal_speed,
    dive_sink_speed, lift_gain, drag_gain, surface_pitch, max_bank.
    Defaults are synthetic. Wind is added to the published velocity, not multiplied
    by dt or accumulated back into the persistent base velocity. Collision is external.
    """
    dt = _dt(dt)
    sport = config.get('sport', 'wingsuit')
    if sport not in ('wingsuit', 'paraglider'):
        raise ValueError('unsupported air sport')
    pos = [_finite(v, 'position') for v in body['position']]
    velocity = [_finite(v, 'velocity') for v in body['velocity']]
    wind = [_finite(v, 'wind') for v in config.get('wind', (0., 0., 0.))]
    if len(pos) != 3 or len(velocity) != 3 or len(wind) != 3:
        raise ValueError('vectors must have three components')
    if dt == 0:
        return {'sport': sport, 'advanced': False, 'evidence': 'synthetic integration; recovered local formulas'}
    steer = _clamp(_finite(controls.get('steer', 0), 'steer'), -1, 1)
    existing = body.get('air', {})
    old = existing if existing.get('sport') == sport else {}
    heading = old.get('heading', math.atan2(velocity[1], velocity[0]))
    yaw_rate = steer * _finite(config.get('turn_rate', .7), 'turn_rate')
    heading = (heading + yaw_rate*dt + math.pi) % (2*math.pi) - math.pi
    base = list(old.get('base_velocity', velocity))
    state = {'sport': sport, 'heading': heading}
    forces = None
    if sport == 'wingsuit':
        tuck = bool(controls.get('tuck', False))
        horizontal = _finite(config.get('dive_horizontal_speed' if tuck else 'horizontal_speed', 40. if tuck else 28.), 'horizontal_speed')
        sink = _finite(config.get('dive_sink_speed' if tuck else 'sink_speed', 22. if tuck else 12.), 'sink_speed')
        if controls.get('brake', False):
            horizontal *= .7  # Synthetic input policy, not a recovered selector.
        target = [horizontal*math.cos(heading), horizontal*math.sin(heading), -sink]
        window = _finite(config.get('response_seconds', .6), 'response_seconds')
        if window <= 0:
            raise ValueError('response_seconds must be positive')
        prev_window = old.get('window', window)
        prev_target = old.get('target', base)
        integral = old.get('integral', [v*prev_window for v in base])
        results = [_response(prev_target[i], integral[i], prev_window, target[i], window, dt) for i in range(3)]
        base = [r[2] for r in results]
        state.update(target=target, integral=[r[0] for r in results], window=results[0][1])
    else:
        brake = 1. if controls.get('brake', False) else 0.
        if brake > .1:
            base = [base[0]*(1-.04*brake), base[1]*(1-.04*brake), base[2]*(1-.03*brake)]
        pitch = _finite(config.get('surface_pitch', -.12), 'surface_pitch')
        bank = -steer * _finite(config.get('max_bank', .35), 'max_bank')
        # Rz Rx Ry surface law, rotated from original +Y-forward into +X-forward.
        fwd = -math.sin(pitch)*math.cos(bank)
        left = -math.sin(bank)
        up = [fwd*math.cos(heading)-left*math.sin(heading), fwd*math.sin(heading)+left*math.cos(heading), math.cos(pitch)*math.cos(bank)]
        forces = _para_forces(base, up, _finite(config.get('lift_gain', .055), 'lift_gain'), _finite(config.get('drag_gain', .008), 'drag_gain'), _finite(config.get('gravity', 9.81), 'gravity'))
        base = [base[i]+dt*sum(f[i] for f in forces) for i in range(3)]
    command = [base[i]+wind[i] for i in range(3)]
    new_pos = [pos[i]+command[i]*dt for i in range(3)]
    if not all(math.isfinite(x) for x in command+new_pos):
        raise ValueError('air integration overflow; reduce step or coefficients')
    state['base_velocity'] = base
    body.update(position=new_pos, velocity=command, air=state, grounded=False,
                orientation=[0., 0., math.sin(heading/2), math.cos(heading/2)], angular_velocity=[0., 0., yaw_rate])
    return {'sport': sport, 'advanced': True, 'base_velocity': base, 'processed_air_velocity': wind,
            'forces': forces, 'heading': heading, 'evidence': 'recovered local math with synthetic presets, heading control and integration',
            'missing': ['zone selection', 'original preset selection', 'collision solve', 'original full body attitude']}


def step_environment(state, dt, config):
    """Advance flat JSON state using documented clock/transition branches.

    time_of_day is in authored 0..24 coordinates. cycle_duration and delta units
    are not recovered: delta_per_second defaults to 1 as a synthetic adapter.
    Holds: hold_flag, hold_count, external_hold, global_hold. Stop fields:
    stop_enabled/stop_target. Weather fields: remaining, duration, start,
    destination, weather_scalar. Track sampling is deliberately external.
    """
    dt = _dt(dt)
    delta = dt * _finite(config.get('delta_per_second', 1.), 'delta_per_second')
    cycle = _finite(config.get('cycle_duration', 10.), 'cycle_duration')
    tod = _finite(state.get('time_of_day', 12.), 'time_of_day')
    count = int(state.get('hold_count', 0))
    target = _finite(state.get('stop_target', 24.), 'stop_target')
    external = bool(config.get('external_hold', False))
    crossing = int(state.get('crossing_count', 0))
    cyclic = int(state.get('cyclic_counter', 0))
    if cycle > 0:
        if not state.get('hold_flag', False) and count <= 0 and not external and not config.get('global_hold', False):
            tod += (delta / 60.) * 24. / cycle
        if tod >= 24.:
            tod = _clamp(tod-24., 0., 24.)
            crossing += 1
            cyclic = (cyclic+1) % 7
            if target >= 24.:
                target -= 24.
    if count <= 0 and state.get('stop_enabled', False) and tod >= target:
        tod = target
        count += 1
    weather = _finite(state.get('weather_scalar', 0.), 'weather_scalar')
    remaining = _finite(state.get('remaining', 0.), 'remaining')
    if not external and config.get('modifier_available', False) and config.get('modifier_gate_allows_update', True):
        remaining = max(remaining-delta*_finite(config.get('weather_rate', 1.), 'weather_rate'), 0.)
        destination = _finite(state.get('destination', weather), 'destination')
        if remaining > 0:
            duration = _finite(state.get('duration', 0.), 'duration')
            if duration <= 0:
                raise ValueError('positive weather remaining requires positive duration')
            weather = destination+(remaining/duration)*(_finite(state.get('start', weather), 'start')-destination)
        else:
            weather = destination
        weather = _clamp(weather, 0., 1.)
    # Supplied samples only. Concrete original track interpolation is unresolved.
    properties = dict(config.get('property_samples', {}))
    for overlay in config.get('overlays', []):
        if overlay.get('mode') == 2 or not overlay.get('enabled', True):
            continue
        weight = _finite(overlay.get('weight', 0.), 'overlay weight')
        for key, sample in overlay.get('samples', {}).items():
            current = properties.get(key, 0.)
            properties[key] = current+weight*(sample-current)
    state.update(time_of_day=tod, hold_count=count, stop_target=target, crossing_count=crossing,
                 cyclic_counter=cyclic, remaining=remaining, weather_scalar=weather, properties=properties)
    return {'time_of_day_argument': tod, 'weather_argument': weather*100.,
            'wind_argument': _finite(state.get('wind_scalar', 0.), 'wind_scalar')*100.,
            'properties': properties, 'evidence': 'recovered local clock and ordered overlay formulas; synthetic delta adapter',
            'missing': ['duration resource selection', 'weather selection helpers', 'property track evaluator'],
            'affects_snow_grip': False}
