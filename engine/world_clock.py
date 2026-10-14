"""Recovered local clock arithmetic; see docs/reconstruction/WORLD_CLOCK.md.

This adapter does not schedule a world, accumulate absolute time or update children.
"""
import math
import struct


def _f32(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('clock scalars must be finite numbers')
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValueError('clock scalar exceeds float32') from exc
    if not math.isfinite(result):
        raise ValueError('clock scalar must be finite')
    return result


def clock_interval(*, input_ms, previous_interval, hold_count=0, pending_holds=0,
                   scale_enabled=False, secondary_enabled=False,
                   scale=1.0, secondary_scale=1.0):
    """Return the local producer's interval, reciprocal, ticks and hold state.

    Millisecond/second names are inferred from the 1000 divisor and 30000 Hz
    tick conversion. Scale/hold names describe observed operations, not symbols.
    Finite arithmetic and signed conversion bounds are adapter restrictions.
    """
    for count in (hold_count, pending_holds):
        if type(count) is not int or not -(1 << 31) <= count < (1 << 31):
            raise ValueError('hold counters must be signed int32')
    if type(scale_enabled) is not bool or type(secondary_enabled) is not bool:
        raise ValueError('scale gates must be bool')
    value, previous = _f32(input_ms), _f32(previous_interval)
    primary, secondary = _f32(scale), _f32(secondary_scale)
    holds = ((hold_count + pending_holds + (1 << 31)) % (1 << 32)) - (1 << 31)
    if holds > 0:
        value = 0.0
    elif scale_enabled:
        value = _f32(value * primary)
        if secondary_enabled:
            value = _f32(value * secondary)
            value = max(value, _f32(0.005))
    elif secondary_enabled:
        value = _f32(value * secondary)
    interval = _f32(value / 1000.0)
    tick_float = _f32(_f32(value * 30.0) + _f32(0.1))
    if not -(1 << 63) <= tick_float < (1 << 63):
        raise ValueError('tick conversion exceeds signed int64')
    ticks = math.trunc(tick_float) & 0xffffffff
    reciprocal = 0.0 if abs(interval) <= _f32(0.00001) else _f32(1.0 / interval)
    return dict(interval=interval, previous_interval=previous, reciprocal=reciprocal,
                ticks=ticks, hold_count=holds, previous_hold_count=hold_count,
                pending_holds=0)
