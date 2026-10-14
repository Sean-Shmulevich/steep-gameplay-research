"""Recovered local animation deferral gate and float32 interval accumulation.

This plans the inspected branch only. It does not invoke graph callbacks, select
an actor, implement the physics scheduler, or assert a render-frame cadence.
"""
import math
import struct


def _uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(f'expected uint{bits}')
    return value


def _f32(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('expected finite float32 interval')
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError as exc:
        raise ValueError('interval overflows float32') from exc
    if not math.isfinite(result):
        raise ValueError('interval overflows float32')
    return result


def plan_animation_update(*, pending_count_word, graph_state_word, mode_flags,
                          counter, threshold, accumulated, interval):
    """Return local branch effects without evaluating or clearing pending entries.

    Flags bit0 must be set and bit2 clear to enter the counter gate. Other bits
    are ignored by that gate. The counter increment wraps at 256 before the
    unsigned comparison. Negative finite intervals are preserved, not clamped.
    """
    pending = _uint(pending_count_word, 32) & 0x1fffffff
    _uint(graph_state_word, 32)
    _uint(mode_flags, 8)
    _uint(counter, 8)
    _uint(threshold, 8)
    interval, accumulated = _f32(interval), _f32(accumulated)
    gated_counter = counter
    deferred = False
    if pending and graph_state_word == 0 and mode_flags & 5 == 1:
        gated_counter = (counter + 1) & 255
        deferred = gated_counter < threshold
    combined = _f32(interval + accumulated)
    return {
        'deferred': deferred,
        'counter': gated_counter if deferred else 0,
        'accumulated': combined if deferred else 0.0,
        'branch_interval': interval if deferred else combined,
        'reset_parameter_groups': not deferred,
    }
