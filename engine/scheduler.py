"""Owned stepping policies, not control of the original game's scheduler.

Subdivision follows publication-review scheduler research (original source:
runtime/testbench/run5/subdivision/findings.md). Smoothing is deliberately absent;
caller-supplied frequency selects the unsmoothed policy. Fixed mode is our design.
All retained state is JSON-compatible and checkpointable.
"""
import math
import struct


def _f32(x):
    try:
        value = struct.unpack('<f', struct.pack('<f', x))[0]
    except OverflowError as exc:
        raise ValueError('value exceeds float32 range') from exc
    if not math.isfinite(value):
        raise ValueError('value exceeds finite float32 range')
    return value


def _finite(x, name, positive=False):
    x = float(x)
    if not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise ValueError(name + ' must be finite and ' + ('positive' if positive else 'nonnegative'))
    return x


def schedule(state, frame_dt, config=None):
    """Consume elapsed wall time into steps; retain unconsumed time in state.

    Config: mode='fixed'|'subdivision', fixed_dt=1/120, max_steps=1024,
    frequency=120, policy=0. Fixed mode caps work and retains backlog. Subdivision
    rejects excessive counts rather than silently changing recovered arithmetic.
    Change modes only after reset; the units of retained time are seconds.
    """
    config = config or {}
    dt = _finite(frame_dt, 'frame_dt')
    retained = _finite(state.get('retained', 0), 'retained')
    mode = config.get('mode', 'fixed')
    if mode not in ('fixed', 'subdivision'):
        raise ValueError('unknown scheduler mode')
    if state.get('mode', mode) != mode:
        raise ValueError('reset scheduler state before changing mode')
    limit = config.get('max_steps', 1024)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError('max_steps must be a positive integer')
    total = _finite(retained + dt, 'accumulated time')
    if mode == 'fixed':
        elapsed = _finite(config.get('fixed_dt', 1 / 120), 'fixed_dt', True)
        # A small relative tolerance prevents a binary roundoff-only missed tick.
        count = limit if total >= limit * elapsed else min(limit, math.floor(total / elapsed + 1e-12))
        consumed = count * elapsed
        remainder = max(0.0, total - consumed)
        steps = [{'elapsed_dt': elapsed, 'derivative_dt': elapsed} for _ in range(count)]
        evidence = 'designed_fixed_step'
    else:
        if config.get('smoothing_enabled', False):
            raise ValueError('smoothing ring/table policy is not implemented')
        policy = config.get('policy', 0)
        if not isinstance(policy, int) or not 0 <= policy <= 255:
            raise ValueError('policy must be a byte')
        frequency = _f32(_finite(config.get('frequency', 120), 'frequency', True))
        if frequency == 0:
            raise ValueError('frequency underflows float32')
        if policy == 1:
            frequency = _f32(90)
        acc = _f32(_f32(retained) + _f32(dt))
        if acc < _f32(9.999999747378752e-6):
            count, consumed, remainder, steps = 0, 0.0, 0.0, []
        else:
            if acc < _f32(1 / frequency):
                count, consumed = 1, acc
            else:
                q = _f32(frequency * acc)
                count = math.floor(q)
                fraction = _f32(q - count)
                if fraction >= _f32(0.8 if policy else 0.5):
                    count += 1
                    consumed = acc
                elif policy and fraction >= _f32(0.15):
                    consumed = min(acc, _f32(_f32(_f32(count) * _f32(1.1)) / frequency))
                else:
                    consumed = acc
            if count > limit:
                raise ValueError('subdivision count exceeds max_steps')
            elapsed = _f32(consumed / _f32(count))
            remainder = _f32(acc - consumed)
            steps = [{'elapsed_dt': elapsed, 'derivative_dt': consumed} for _ in range(count)]
        evidence = 'recovered_subdivision_without_smoothing'
    state.update(mode=mode, retained=remainder, last_count=count,
                 last_consumed=consumed, evidence=evidence)
    return steps
