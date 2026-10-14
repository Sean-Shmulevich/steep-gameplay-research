"""Recovered animation replacement lookup over caller-owned synthetic objects.

Evidence: docs/reconstruction/research/animation.md, Ordered provider replacement
and Wrapper availability delegates to a context callback. These are our object
shapes, not decoded native layouts. No loading, pointer lifetime, readiness,
thread safety, clip selection, or integration with the synthetic pose player is
implied. Availability remains a caller-supplied predicate.
"""
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Handle:
    key: int


@dataclass
class Row:
    key: int
    scalar_bits: int
    flag: int
    available: bool
    handle: Handle


@dataclass
class Provider:
    rows: list[Row]


@dataclass
class Wrapper:
    pointer: Provider | None
    control_word: int = 0


@dataclass
class Outputs:
    scalar_bits: int = 0
    flag: int = 0


def select_replacement(primary: Provider | None, wrappers: list[Wrapper | None],
                       original: Handle, outputs: Outputs,
                       accepts: Callable[[Any], bool]) -> Handle:
    """Preserve identity, ordered lookup, and output writes on failed matches.

    Caller contract: keys/words/bytes have their native unsigned widths, rows
    are valid objects, and availability reflects only a non-null row pointer.
    Scalars remain raw bits to avoid inventing units or changing float payloads.
    Native relative-array decoding and concurrent mutation are outside this model.
    """
    def find(provider):
        for row in provider.rows:
            if row.key == original.key:
                outputs.scalar_bits = row.scalar_bits
                outputs.flag = row.flag
                if row.available:
                    return row.handle
        return None

    if primary is not None:
        selected = find(primary)
        if selected is not None:
            return selected
    for wrapper in wrappers:
        if wrapper is None:
            continue
        if not (wrapper.control_word & 0x80000000):
            if not accepts(wrapper.pointer):
                continue
        # Deliberately reread after the callback, matching the native helper.
        provider = wrapper.pointer
        if provider is not None:
            selected = find(provider)
            if selected is not None:
                return selected
    return original


def tagged_endpoint(records, requested_tag, limit):
    """First matching byte tag, decoded as float32(uint16 / 120), then capped.

    Evidence: animation research, Tagged endpoint conversion. ``records`` are
    synthetic (tag, encoded_endpoint) pairs replacing unresolved native accessor
    callbacks. Returns (found, value); a miss writes zero. Preserve MINSS source
    preference for equal/unordered operands, including NaN in the supplied limit.
    Values are in the resource's unproven playback units.
    """
    import struct
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    if type(requested_tag) is not int or not 0 <= requested_tag <= 255:
        raise ValueError('expected byte tag')
    for tag, encoded in records:
        if type(tag) is not int or not 0 <= tag <= 255:
            raise ValueError('expected byte record tag')
        if tag != requested_tag:
            continue
        if type(encoded) is not int or not 0 <= encoded <= 65535:
            raise ValueError('expected uint16 endpoint')
        value = f32(encoded / 120.0)
        bound = f32(limit)
        return True, bound if bound < value else value
    return False, 0.0


def resolve_playback_range(resource_length, requested_start, requested_end,
                           custom_range, equal_range_backoff=0.0):
    """Finite-input range kernel; does not update an evaluator or its caches.

    Evidence: animation research, Effective range and tick quantization. Backoff
    is supplied by an unresolved owner-context producer, not assumed frame dt.
    No units or valid clip-duration limits are invented here.
    """
    import math
    import struct
    def f32(value):
        result = struct.unpack('<f', struct.pack('<f', value))[0]
        if not math.isfinite(result):
            raise ValueError('range adapter requires finite float32 values')
        return result
    length = f32(resource_length)
    start = f32(requested_start) if custom_range else 0.0
    end = f32(requested_end) if custom_range else length
    epsilon = f32(1e-5)
    if abs(f32(start - end)) <= epsilon:
        start = max(f32(start - f32(equal_range_backoff)), 0.0)
    elif abs(end) <= epsilon:
        end = length
    if start >= end:
        start, end = 0.0, length
    def ticks(value):
        rounded = f32(f32(value * 120.0) + 0.5)
        # CVTTSS2SI r64 returns the integer-indefinite value on overflow.
        integer = math.trunc(rounded) if -(1 << 63) <= rounded < (1 << 63) else -(1 << 63)
        return integer & 0xffff
    return {'start': start, 'end': end,
            'start_tick': ticks(start), 'end_tick': ticks(end)}


def timestamp_cursor(encoded_times, absolute_position, previous=None):
    """Recovered reset or forward-only cache walk over synthetic uint16 times.

    Evidence: animation research, Timestamp cursor boundaries. ``previous=None``
    selects reset; otherwise -1 denotes the before-first sentinel. Native reset
    and advance read distinct count fields, so the caller must supply the correct
    sequence for the selected operation. No event delivery is implemented.
    """
    import math
    import struct
    def f32(value):
        return struct.unpack('<f', struct.pack('<f', value))[0]
    position = f32(absolute_position)
    if not math.isfinite(position):
        raise ValueError('cursor adapter requires a finite position')
    times = []
    for encoded in encoded_times:
        if type(encoded) is not int or not 0 <= encoded <= 65535:
            raise ValueError('expected uint16 timestamp')
        times.append(f32(encoded / 120.0))
    if previous is None:
        for index, time in enumerate(times):
            if time >= position:
                return index - 1
        # The native exhaustion result is count, including zero for empty input.
        return len(times)
    if type(previous) is not int or previous < -1 or previous > 0xffffffff:
        raise ValueError('expected cursor index or -1')
    index = 0 if previous in (-1, 0xffffffff) else (previous + 1) & 0xffffffff
    result = previous
    while index < len(times) and times[index] <= position:
        result = index
        index += 1
    return result
