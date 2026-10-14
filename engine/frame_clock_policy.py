"""Recovered interval-policy block; see docs/reconstruction/FRAME_CLOCK_POLICY.md."""
from .world_clock import _f32


def select_interval(*, elapsed_seconds, mode, rate=60.0, table=(1 / 30,),
                    table_index=0, stable_count=0, history=None, history_index=0):
    """Pure adapter for the driver's policy block, excluding timer I/O and waits.

    history has 16 slots; the native sum reads only the first 15. Slot 15
    aliases the low word of a neighboring native field; see the evidence note.
    Finite inputs, valid indexes and non-overlapping Python state are our guards.
    """
    value = _f32(elapsed_seconds)
    if type(mode) is not int or not 0 <= mode <= 0xffffffff:
        raise ValueError('mode must be uint32')
    if type(stable_count) is not int or not 0 <= stable_count <= 0x7fffffff:
        raise ValueError('stable_count must be nonnegative int32')
    entries = [_f32(v) for v in table]
    if not entries or type(table_index) is not int or not 0 <= table_index < len(entries):
        raise ValueError('table index is invalid')
    samples = [_f32(v) for v in ([0.0] * 16 if history is None else history)]
    if len(samples) != 16 or type(history_index) is not int or not 0 <= history_index <= 15:
        raise ValueError('history requires 16 slots and index 0 through 15')
    alias_write = None
    if mode == 0:
        hz = _f32(rate)
        if hz <= 0: raise ValueError('rate must be positive')
        value = _f32(1.0 / hz)
    elif mode == 1:
        old = table_index
        if value > entries[old]:
            table_index = max(old - 1, 0)
            if table_index != old: stable_count = 0
        elif stable_count > 10:
            table_index = min(old + 1, len(entries) - 1)
        else:
            stable_count += 1
        value = entries[table_index]
    elif mode == 2:
        if entries[0] < value: value = entries[0]
    elif mode == 3:
        samples[history_index] = value
        if history_index == 15: alias_write = value
        value = 0.0
        for sample in samples[:15]: value = _f32(value + sample)
        value = _f32(value / 15.0)
        history_index = history_index + 1 if history_index < 15 else 0
    value = max(value, _f32(.0001))
    return dict(interval_seconds=value, input_ms=_f32(value * 1000.0),
                table_index=table_index, stable_count=stable_count,
                history=samples, history_index=history_index,
                neighboring_low_word_float_write=alias_write)
