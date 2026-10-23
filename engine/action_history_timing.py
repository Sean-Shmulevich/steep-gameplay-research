"""History-sector action timing; detached state with explicit clock reads.

Evidence: INPUT_TO_ACTION_ROUTE.md, History action timing gates.
Configuration durations are multiplied by 1000 before uint64 comparison.
No wall-clock or scheduler cadence is inferred from that scale alone.
"""
from .action_sample import f32

_MASK = (1 << 64) - 1


def _u64(value):
    if type(value) is not int or not 0 <= value <= _MASK:
        raise ValueError('uint64 clock or timestamp required')
    return value


def advance_history_timing(*, current, previous, mode, start_time, repeat_time,
                           hold_delay, repeat_delay, read_clock):
    """Evaluate rising/held/falling modes 0/1/2 and return next detached state.

    Finite nonnegative configuration only. Each needed clock read is separate,
    matching native order. Unknown uint32 modes publish false but cache current.
    Durations whose scaled float32 value reaches 2**64 are unsupported.
    """
    if type(current) is not bool or type(previous) is not bool:
        raise ValueError('current and previous must be booleans')
    if type(mode) is not int or not 0 <= mode <= 0xffffffff:
        raise ValueError('mode must be uint32')
    start_time, repeat_time = _u64(start_time), _u64(repeat_time)
    delays = [f32(hold_delay), f32(repeat_delay)]
    if any(x < 0 or f32(x*1000) >= 2**64 for x in delays):
        raise ValueError('finite nonnegative durations below uint64 tick range required')
    reads = []
    def clock():
        value = _u64(read_clock())
        reads.append(value)
        return value
    active = False
    if mode == 0:
        active = current and not previous
    elif mode == 2:
        active = previous and not current
    elif mode == 1:
        delay, repeat = delays
        if delay <= f32(1e-5):
            active = current
        elif current:
            now = clock()
            if previous != current:
                start_time = now
            else:
                active = ((now-start_time) & _MASK) >= int(f32(delay*1000))
        if active and repeat > f32(1e-5):
            now = clock()
            if ((now-repeat_time) & _MASK) >= int(f32(repeat*1000)):
                repeat_time = now
            else:
                active = False
    return dict(active=active, previous=current, start_time=start_time,
                repeat_time=repeat_time, clock_reads=reads)
