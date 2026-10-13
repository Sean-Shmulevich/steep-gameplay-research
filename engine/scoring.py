"""Recovered score math with an explicitly designed event detector.

See docs/systems/scoring/CLIENT_GUIDE.txt sections 2, 3 and 8. Rotation
quantization and float32 commit truncation are recovered local rules. Mapping
world angular velocity Z to primary rotation and X/Y to secondary axes,
integrating absolute motion, scoring once per flight, and grounded-edge landing
detection are substitutes, not the original rotation/trick classifiers.
"""
import math
import struct

EVIDENCE = 'recovered_score_math_with_designed_flight_detector'


def _f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def _valid(x, name):
    x = float(x)
    if not math.isfinite(x) or x < 0 or x > 1e12:
        raise ValueError(name + ' must be finite, nonnegative and <= 1e12')
    return x


def rotation_points(primary, secondary_a=0, secondary_b=0):
    """Accumulated magnitudes in radians; ordinary finite operational domain."""
    counts = []
    for radians, divisor, threshold in ((primary, 180, .25), (secondary_a, 360, .125), (secondary_b, 360, .125)):
        degrees = _f32(_f32(_f32(_valid(radians, 'rotation')) * 180) / _f32(math.pi))
        turns = _f32(degrees / divisor)
        low = math.floor(turns)
        counts.append(math.ceil(turns) if _f32(turns - low) >= _f32(threshold) else low)
    return int(_f32(_f32(_f32(counts[0] * 5) + _f32(counts[1] * 10)) + _f32(counts[2] * 10)))


def reset(state, keep_total=False):
    total = state.get('total', 0) if keep_total else 0
    state.clear()
    state.update(total=total, pending=0, airborne=False, air_time=0.0,
                 rotations=[0.0, 0.0, 0.0], flight_id=0,
                 last_committed_flight=None, evidence=EVIDENCE)


def _init(state):
    if 'airborne' not in state:
        reset(state, keep_total=True)


def begin_air(state):
    _init(state)
    if state['airborne']:
        return []
    state.update(airborne=True, air_time=0.0, rotations=[0.0, 0.0, 0.0], pending=0,
                 flight_id=state['flight_id'] + 1)
    return [{'type': 'score_flight_started', 'flight_id': state['flight_id']}]


def update_air(state, angular_velocity, dt, config=None):
    _init(state)
    dt = _valid(dt, 'dt')
    if len(angular_velocity) != 3:
        raise ValueError('angular_velocity must contain three values')
    omega = [_valid(abs(float(x)), 'angular_velocity') for x in angular_velocity]
    if not state['airborne']:
        return []
    rotations = [old + omega[i] * dt for old, i in zip(state['rotations'], (2, 0, 1))]
    points = rotation_points(*rotations)
    state.update(rotations=rotations, pending=points, air_time=state['air_time'] + dt)
    return []


def land(state, clean=True, config=None):
    _init(state)
    config = config or {}
    minimum = _valid(config.get('min_air_time', .75), 'min_air_time')
    multiplier = _valid(config.get('multiplier', 1), 'multiplier')
    if not state['airborne']:
        return []
    accepted = bool(clean) and state['air_time'] >= minimum
    points = int(_f32(_f32(state['pending']) * _f32(multiplier))) if accepted else 0
    state['total'] += points
    state.update(airborne=False, pending=0, last_committed_flight=state['flight_id'] if accepted else None)
    return [{'type': 'score_committed' if accepted else 'score_cancelled',
             'flight_id': state['flight_id'], 'points': points, 'total': state['total'],
             'air_time': state['air_time'], 'evidence': EVIDENCE}]


def update(state, body, diagnostics, dt, config=None):
    """Call once after each physics step. No frame-rate-dependent score ticks.

    A caller may supply score_angular_velocity in diagnostics to replace the
    world-velocity approximation. landing_clean defaults true unless crashed.
    Initial airborne spawn starts a flight; this is an intentional demo policy.
    """
    _valid(dt, 'dt')
    _init(state)
    if body.get('grounded', False):
        clean = diagnostics.get('landing_clean', True) and not diagnostics.get('crashed', False)
        return land(state, clean, config)
    events = begin_air(state)
    update_air(state, diagnostics.get('score_angular_velocity', body.get('angular_velocity', [0, 0, 0])), dt, config)
    return events
