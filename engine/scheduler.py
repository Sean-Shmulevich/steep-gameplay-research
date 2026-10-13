"""Owned stepping policies, not control of the original game's scheduler.

Subdivision and smoothing follow docs/reconstruction/SCHEDULER_SMOOTHING_AUDIT.md
and its instruction-backed sources. Fixed mode, observer counters and plan schema
are our design. Unsmoothed frequency overrides are labeled designed deviations.
All retained state is JSON-compatible and checkpointable; scheduling plans do
not prove that a physics job executed or completed.
"""
import copy
import math
import struct

FREQUENCY_TABLE = (100., 100., 100., 90., 80., 100., 90., 105., 120., 90., 100., 110., 120.)
ACCUMULATOR_CAP = 0.06666667014360428


def _f32(x):
    try:
        value = struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError as exc:
        raise ValueError('value exceeds float32 range') from exc
    if not math.isfinite(value):
        raise ValueError('value exceeds finite float32 range')
    return value


def _finite(x, name, positive=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(name + ' must be numeric')
    x = float(x)
    if not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise ValueError(name + ' must be finite and ' + ('positive' if positive else 'nonnegative'))
    return x


def _counter(value, name, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(name + ' is out of range')
    return value


def _history(state, capacity):
    """Validate/copy a physical ring. Capacity is a caller choice, not universal."""
    original = state.get('history')
    if original is None:
        return dict(capacity=capacity, values=[0.0] * capacity, count=0, write=0, oldest=0)
    if not isinstance(original, dict) or set(original) != {'capacity', 'values', 'count', 'write', 'oldest'}:
        raise ValueError('invalid smoothing history schema')
    if original['capacity'] != capacity:
        raise ValueError('reset scheduler history before changing its capacity')
    values = original['values']
    if not isinstance(values, list) or len(values) != capacity:
        raise ValueError('invalid smoothing history buffer')
    for value in values:
        if _f32(_finite(value, 'history value')) != value:
            raise ValueError('history values must be float32')
    count = _counter(original['count'], 'history count', maximum=capacity)
    write = _counter(original['write'], 'history write', maximum=capacity - 1)
    oldest = _counter(original['oldest'], 'history oldest', maximum=capacity - 1)
    if write != (oldest + count) % capacity:
        raise ValueError('inconsistent history cursor layout')
    return copy.deepcopy(original)


def _append(history, frame_dt):
    capacity = history['capacity']
    history['values'][history['write']] = frame_dt
    history['count'] += 1
    if history['count'] > capacity:
        history['oldest'] = (history['oldest'] + history['count'] - capacity) % capacity
        history['count'] = capacity
    history['write'] = (history['write'] + 1) % capacity
    total = 0.0
    for i in range(history['count']):
        total = _f32(total + history['values'][(history['oldest'] + i) % capacity])
    mean = _f32(total / _f32(history['count']))
    index = 0 if mean <= 0 else min(int(_f32(_f32(_f32(.2) / mean) + _f32(.5))), 12)
    return mean, index


def native_initial_state():
    """Successful-allocation native timing initializer, expressed as JSON.

    Source: docs/reconstruction/SCHEDULER_LIFETIME_AUDIT.md. Initial consumed and
    elapsed intervals are float32(1/90), inverse/frequency90, but step_count0:
    these are initialization values, not evidence of executed or planned steps.
    The physical ring's initially unused slots are our zero-fill representation;
    its native allocation contents were not established and count0 ignores them.

    Call schedule(state, dt, {'mode':'subdivision','smoothing_enabled':True})
    to select the corresponding policy explicitly. This helper does not change
    the engine's deliberately fixed default. Native allocation-failure behavior
    is not emulated; our Python ring allocation must succeed.
    """
    return dict(mode='subdivision', retained=0.0, last_count=0,
                last_consumed=_f32(1 / 90), last_elapsed=_f32(1 / 90),
                inverse_consumed_dt=90.0, selected_frequency=90.0,
                smoothing_enabled=True, history=_history({}, 10),
                frame_count=0, total_substeps=0,
                evidence='recovered_timing_initializer_successful_allocation')


def schedule(state, frame_dt, config=None):
    """Consume elapsed wall time into steps; retain unconsumed time in state.

    Config: mode='fixed'|'subdivision', fixed_dt=1/120, max_steps=1024,
    frequency=120, policy=0, smoothing_enabled=False, history_capacity=10.
    Ten entries matches the recovered successful-allocation initializer; caller
    overrides are supported for explicit experiments, not claimed native defaults.
    Fixed mode caps work and retains backlog. Subdivision
    rejects excessive counts rather than silently changing recovered arithmetic.
    Change modes/capacity only after reset; retained time is in seconds.
    state.last_plan is a serializable per-frame plan, not an execution receipt.
    frame_count/total_substeps count planned work in this reconstruction.
    """
    config = {} if config is None else config
    if not isinstance(state, dict) or not isinstance(config, dict):
        raise ValueError('state and config must be objects')
    if set(config) - {'mode', 'fixed_dt', 'max_steps', 'frequency', 'policy', 'smoothing_enabled', 'history_capacity'}:
        raise ValueError('unknown scheduler configuration field')
    dt = _finite(frame_dt, 'frame_dt')
    retained = _finite(state.get('retained', 0), 'retained')
    mode = config.get('mode', 'fixed')
    if mode not in ('fixed', 'subdivision'):
        raise ValueError('unknown scheduler mode')
    if state.get('mode', mode) != mode:
        raise ValueError('reset scheduler state before changing mode')
    limit = _counter(config.get('max_steps', 1024), 'max_steps', 1, 100000)
    frame_count = _counter(state.get('frame_count', 0), 'frame_count')
    total_substeps = _counter(state.get('total_substeps', 0), 'total_substeps')
    total = _finite(retained + dt, 'accumulated time')
    history = None
    plan = dict(schema_version=1, frame=frame_count + 1, mode=mode,
                raw_frame_dt=dt, retained_before=retained,
                accumulator_before_cap=total, accumulator_after_cap=total,
                cap_discarded=0.0, epsilon_discarded=0.0,
                policy=None, frequency=None, mean_frame_dt=None, frequency_table_index=None,
                smoothing_enabled=False, frequency_source=None,
                count_limit=limit, count_limited=False)
    if mode == 'fixed':
        elapsed = _finite(config.get('fixed_dt', 1 / 120), 'fixed_dt', True)
        # A small relative tolerance prevents a binary roundoff-only missed tick.
        count = limit if total >= limit * elapsed else min(limit, math.floor(total / elapsed + 1e-12))
        consumed = count * elapsed
        remainder = max(0.0, total - consumed)
        steps = [{'elapsed_dt': elapsed, 'derivative_dt': elapsed} for _ in range(count)]
        evidence = 'designed_fixed_step'
        plan.update(branch='fixed_steps' if count else 'fixed_waiting',
                    count_limited=count == limit and remainder >= elapsed)
    else:
        enabled = config.get('smoothing_enabled', False)
        if type(enabled) is not bool:
            raise ValueError('smoothing_enabled must be boolean')
        policy = _counter(config.get('policy', 0), 'policy', maximum=255)
        capacity = _counter(config.get('history_capacity', 10), 'history_capacity', 1, 4096)
        history = _history(state, capacity)
        frequency = _f32(_finite(config.get('frequency', 120), 'frequency', True))
        if frequency == 0:
            raise ValueError('frequency underflows float32')
        raw_dt = _f32(dt)
        acc = _f32(_f32(retained) + raw_dt)
        plan.update(rounded_frame_dt=raw_dt, accumulator_before_cap=acc,
                    smoothing_enabled=enabled, policy=policy,
                    frequency_source='native_unsmoothed_120' if frequency == 120 else 'designed_frequency_override')
        if enabled:
            if 'frequency' in config:
                raise ValueError('frequency override is incompatible with recovered smoothing')
            uncapped = acc
            acc = min(acc, _f32(ACCUMULATOR_CAP))
            mean, index = _append(history, raw_dt)
            frequency = FREQUENCY_TABLE[index]
            plan.update(mean_frame_dt=mean, frequency_table_index=index,
                        cap_discarded=_f32(uncapped - acc), frequency_source='recovered_history_table')
        else:
            history.update(count=0, write=0, oldest=0)
        if policy == 1:
            frequency = _f32(90)
            plan['frequency_source'] = 'recovered_policy_one_override'
        plan.update(frequency=frequency, accumulator_after_cap=acc)
        if acc < _f32(9.999999747378752e-6):
            count, consumed, remainder, steps = 0, 0.0, 0.0, []
            plan.update(branch='below_epsilon', epsilon_discarded=acc)
        else:
            if acc < _f32(1 / frequency):
                count, consumed = 1, acc
                plan['branch'] = 'below_period_single_step'
            else:
                q = _f32(frequency * acc)
                count = math.floor(q)
                fraction = _f32(q - count)
                if fraction >= _f32(0.8 if policy else 0.5):
                    count += 1
                    consumed = acc
                    plan['branch'] = 'rounded_count_up'
                elif policy and fraction >= _f32(0.15):
                    consumed = min(acc, _f32(_f32(_f32(count) * _f32(1.1)) / frequency))
                    plan['branch'] = 'retained_policy_remainder'
                else:
                    consumed = acc
                    plan['branch'] = 'floor_count_consume_all'
                plan.update(product=q, fraction=fraction,
                            round_up_threshold=_f32(.8 if policy else .5))
            if count > limit:
                raise ValueError('subdivision count exceeds max_steps')
            elapsed = _f32(consumed / _f32(count))
            remainder = _f32(acc - consumed)
            steps = [{'elapsed_dt': elapsed, 'derivative_dt': consumed} for _ in range(count)]
        evidence = 'recovered_subdivision_with_smoothing' if enabled else 'recovered_subdivision_without_smoothing'
        if not enabled and config.get('frequency', 120) != 120 and policy != 1:
            evidence = 'recovered_subdivision_with_designed_frequency_override'
    inverse = (_f32(1 / consumed) if mode == 'subdivision' else _finite(1 / consumed, 'inverse consumed interval')) if consumed else 0.0
    plan.update(count=count, consumed=consumed, retained_after=remainder,
                inverse_consumed_dt=inverse,
                steps=copy.deepcopy(steps), evidence=evidence)
    if history is not None:
        plan['history'] = copy.deepcopy(history)
    state.update(mode=mode, retained=remainder, last_count=count,
                 last_consumed=consumed, evidence=evidence, frame_count=frame_count+1,
                 total_substeps=total_substeps+count, last_plan=plan,
                 last_elapsed=steps[0]['elapsed_dt'] if steps else 0.0,
                 inverse_consumed_dt=inverse, selected_frequency=plan['frequency'],
                 smoothing_enabled=plan['smoothing_enabled'])
    if history is not None:
        state['history'] = history
    return steps
