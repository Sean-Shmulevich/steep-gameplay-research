"""Recovered skeleton post-update tail; cadence is not a pose completion fence."""
import struct
import math


def f32(value):
    try:
        return struct.unpack('<f', struct.pack('<f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def advance_skeleton_cadence(counter, interval, flags, dirty, accumulated, dt):
    """Native uint8 state and float32 accumulation, before counter increment.

    dt is supplied from the owner's selected world time group. Units inherit that
    source; this function does not establish a fixed animation rate.
    """
    if any(type(v) is not int or not 0 <= v <= 255 for v in (counter, interval, flags, dirty)):
        raise ValueError('uint8 cadence state required')
    accumulate = interval != 0 and counter % interval != 0 and not (flags & 1)
    value = f32(f32(accumulated) + f32(dt)) if accumulate else 0.0
    return dict(counter=(counter + 1) & 255, flags=flags & 254,
                dirty=dirty & 239, accumulated=value, accumulated_this_call=accumulate)
